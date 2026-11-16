from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from ...db.database import jdump
from ...orchestration.run_context import RunContext


def _cosine(a, b):
    # a: (d,), b: (n,d)
    an = a / (np.linalg.norm(a) + 1e-9)
    bn = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return bn @ an


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_g_validator")
    problems = ctx.db.query("SELECT problem_id, title, problem_statement, representative_text, top_evidence_json, priority_score, supporting_feedback_ids_json FROM canonical_problems WHERE run_id=? ORDER BY priority_score DESC", (ctx.run_id,))
    backlog = ctx.db.query("SELECT backlog_id, title, description, searchable_text, status, status_normalized, issue_type, journey_node_id FROM backlog_items WHERE run_id=?", (ctx.run_id,))
    if not problems:
        ctx.module_done("module_g_validator", 0, 0, "no problems")
        return {"findings": 0}
    if not backlog:
        # all uncovered
        findings = []
        for p in problems:
            fid = "VF-" + hashlib.sha1(f"{ctx.run_id}|{p['problem_id']}|none".encode()).hexdigest()[:16]
            findings.append((fid, ctx.run_id, p["problem_id"], "UNCOVERED_GAP", 0.0, None, jdump([]), jdump({"note":"no backlog"}), 0.4, "No backlog items available for comparison", "final", jdump({})))
        ctx.db.executemany("INSERT OR REPLACE INTO validation_findings(finding_id,run_id,problem_id,relationship_type,alignment_score,best_ticket_id,top_candidates_json,judge_decision_json,confidence,reason,status,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", findings)
        ctx.update_counts(uncovered_gap_count=len(findings))
        ctx.module_done("module_g_validator", len(problems), len(findings), "no backlog -> all uncovered")
        return {"findings": len(findings), "uncovered": len(findings)}

    # build TFIDF embeddings as dense semantic proxy (local, deterministic)
    b_texts = [(b["searchable_text"] or ((b["title"] or "")+" "+(b["description"] or "")) or "backlog") for b in backlog]
    p_texts = []
    for p in problems:
        ev = json.loads(p["top_evidence_json"] or "[]")
        evtxt = " ".join([e.get("enriched_sentence") or e.get("evidence_span") or "" for e in ev[:5]])
        p_texts.append(" ".join([p.get("title") or "", p.get("problem_statement") or "", evtxt]))
    vec = TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True, stop_words="english", max_features=8000)
    try:
        B = vec.fit_transform(b_texts)
        P = vec.transform(p_texts)
    except Exception:
        B = vec.fit_transform(["x"]*len(b_texts)); P = vec.transform(["x"]*len(p_texts))
    Bn = normalize(B).toarray().astype(np.float32)
    Pn = normalize(P).toarray().astype(np.float32)

    findings = []
    matches = []
    uncovered = 0
    gray = 0
    covered = 0
    k = max(1, ctx.settings.backlog_top_k)
    for i, p in enumerate(problems):
        sims = _cosine(Pn[i], Bn)
        order = np.argsort(-sims)
        top_idx = order[:k]
        candidates = []
        for rank, j in enumerate(top_idx, 1):
            b = backlog[int(j)]
            score = float(sims[int(j)])
            candidates.append({"backlog_id": b["backlog_id"], "title": b["title"], "status": b["status"], "score": round(score,4), "rank": rank})
            matches.append((ctx.run_id, p["problem_id"], b["backlog_id"], score, rank, None, None, None, "scored", jdump({"status": b["status"]})))
        best = candidates[0] if candidates else None
        best_score = best["score"] if best else 0.0
        if best_score >= ctx.settings.covered_threshold:
            rel = "COVERED"; covered += 1
            reason = "Top semantic similarity >= covered threshold (alignment signal; not proof of shipped resolution)."
            status = "final"; judge = {"covered": True, "best_ticket_id": best["backlog_id"], "reason": reason, "mode": "threshold"}
        elif best_score >= ctx.settings.gray_zone_lower:
            rel = "PARTIAL_GRAY_ZONE"; gray += 1
            # local judge via Gemini if available else unverified
            judge = _gray_zone_judge(ctx, p, candidates[:3])
            status = "judged" if judge.get("mode") != "unverified" else "needs_review"
            reason = judge.get("reason") or "Gray-zone similarity; requires review."
            if judge.get("covered") is True:
                rel = "COVERED_BY_JUDGE"
        else:
            rel = "UNCOVERED_GAP"; uncovered += 1
            reason = "No backlog item reached similarity threshold."
            status = "final"; judge = {"covered": False, "best_ticket_id": None, "reason": reason, "mode": "threshold"}
        fid = "VF-" + hashlib.sha1(f"{ctx.run_id}|{p['problem_id']}".encode()).hexdigest()[:16]
        findings.append((fid, ctx.run_id, p["problem_id"], rel, float(best_score), best["backlog_id"] if best else None, jdump(candidates), jdump(judge), float(min(0.95, 0.4+best_score)), reason, status, jdump({"thresholds": {"covered": ctx.settings.covered_threshold, "gray": ctx.settings.gray_zone_lower}})))

    ctx.db.executemany("INSERT OR REPLACE INTO backlog_problem_matches(run_id,problem_id,backlog_id,similarity_score,rank,judge_covered,judge_reason,judge_model,judge_status,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?)", matches)
    ctx.db.executemany("INSERT OR REPLACE INTO validation_findings(finding_id,run_id,problem_id,relationship_type,alignment_score,best_ticket_id,top_candidates_json,judge_decision_json,confidence,reason,status,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", findings)
    report = {"problems": len(problems), "backlog_items": len(backlog), "covered": covered, "gray_zone": gray, "uncovered": uncovered, "uncovered_plus_judge_open": uncovered + sum(1 for f in findings if f[3] in ("PARTIAL_GRAY_ZONE",))}
    c = ctx.artifacts.write_json("direct/backlog_matches.json", report)
    ctx.record_artifact("module_g_validator", "report", "direct/backlog_matches.json", c)
    ctx.update_counts(uncovered_gap_count=uncovered)
    ctx.module_done("module_g_validator", input_count=len(problems), output_count=len(findings), message=f"covered={covered} gray={gray} uncovered={uncovered}")
    return report


def _gray_zone_judge(ctx: RunContext, problem: dict, candidates: list[dict]) -> dict:
    # strict offline/unverified default; try Gemini if configured
    base = {"covered": None, "best_ticket_id": None, "reason": "Gray-zone retained as unverified (no confident local judge).", "mode": "unverified"}
    if not (ctx.settings.allow_cloud_calls and ctx.settings.gemini_api_key):
        return base
    try:
        import urllib.request
        prompt = (
            "You are validating backlog coverage. Distinguish topical similarity from actual resolution coverage. "
            "Return ONLY JSON: {\"covered\":true|false,\"best_ticket_id\":<id or null>,\"reason\":<evidence-grounded string>}.\n"
            f"Problem: {problem.get('title')} :: {problem.get('problem_statement')}\n"
            f"Candidates: {json.dumps(candidates)}\n"
            "best_ticket_id must be one of supplied candidate backlog_ids or null."
        )
        body = json.dumps({"contents":[{"parts":[{"text": prompt}]}], "generationConfig": {"temperature": 0.1, "maxOutputTokens": 300}}).encode()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{ctx.settings.gemini_model}:generateContent?key={ctx.settings.gemini_api_key}"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=ctx.settings.llm_timeout_seconds) as resp:
            data = json.loads(resp.read().decode())
        text = data.get("candidates",[{}])[0].get("content",{}).get("parts",[{}])[0].get("text","")
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return base
        obj = json.loads(m.group(0))
        allowed = {c["backlog_id"] for c in candidates} | {None}
        if obj.get("best_ticket_id") not in allowed:
            obj["best_ticket_id"] = None
        if not isinstance(obj.get("covered"), bool):
            obj["covered"] = False
        obj["mode"] = "gemini_judge"
        return obj
    except Exception as e:
        b = dict(base); b["reason"] = f"Gray-zone unverified (judge error: {type(e).__name__})"; return b
