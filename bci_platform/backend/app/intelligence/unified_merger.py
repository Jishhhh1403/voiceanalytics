from __future__ import annotations

import hashlib
import json
from typing import Any

from ..db.database import jdump
from ..orchestration.run_context import RunContext


def jaccard(a: set, b: set) -> float:
    if not a and not b: return 0.0
    u = len(a|b); return (len(a&b)/u) if u else 0.0


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("unified_merger")
    problems = ctx.db.query("SELECT * FROM canonical_problems WHERE run_id=?", (ctx.run_id,))
    findings = {r["problem_id"]: r for r in ctx.db.query("SELECT * FROM validation_findings WHERE run_id=?", (ctx.run_id,))}
    ws = ctx.db.query("SELECT * FROM whitespace_candidates WHERE run_id=?", (ctx.run_id,))

    unified = []
    ws_by_problem = {w["linked_problem_id"]: w for w in ws if w.get("linked_problem_id")}
    used_ws = set()

    # Track 1 uncovered/gray as direct candidates
    for p in problems:
        vf = findings.get(p["problem_id"], {})
        rel = vf.get("relationship_type")
        align = float(vf.get("alignment_score") or 0)
        if rel in ("COVERED", "COVERED_BY_JUDGE"):
            # still may be BOTH if whitespace linked
            pass
        direct_score = 0.50 * (float(p.get("priority_score") or 0)/100.0) + 0.50 * (1.0 - align)
        linked_ws = ws_by_problem.get(p["problem_id"])
        fids = set(json.loads(p.get("supporting_feedback_ids_json") or "[]"))
        is_direct_gap = rel not in ("COVERED","COVERED_BY_JUDGE")
        if linked_ws:
            used_ws.add(linked_ws["whitespace_id"])
            wfids = set(json.loads(linked_ws.get("supporting_feedback_ids_json") or "[]"))
            # evidence-aware merge
            merged_fids = list(fids | wfids)
            lenses = json.loads(linked_ws.get("lenses_triggered_json") or "[]")
            if "DIRECT_GAP" not in lenses: lenses.append("DIRECT_GAP")
            orig = float(linked_ws.get("whitespace_score") or 0)
            adjusted = min(1.0, orig * 1.20) if is_direct_gap else orig
            source = "BOTH" if is_direct_gap else "TRIANGULATED_WHITESPACE"
            unified.append({
                "candidate_id": "UC-" + hashlib.sha1(f"{ctx.run_id}|both|{p['problem_id']}".encode()).hexdigest()[:16],
                "discovery_source": source,
                "linked_problem_id": p["problem_id"],
                "title": p.get("title") or linked_ws.get("title"),
                "hypothesis": linked_ws.get("hypothesis"),
                "acceptance_criteria_json": linked_ws.get("acceptance_criteria_json"),
                "evidence_strength_score": round(max(direct_score, orig),4),
                "coverage_uncertainty": {"alignment": align, "relationship": rel, "note": "alignment similarity != proof of resolution"},
                "business_priority": float(p.get("priority_score") or 0),
                "score_components_json": jdump({"direct_score": direct_score, "whitespace_original": orig, "whitespace_adjusted": adjusted, "priority_score": p.get("priority_score"), "alignment": align}),
                "lenses_triggered_json": jdump(lenses),
                "supporting_feedback_ids_json": jdump(merged_fids[:400]),
                "matched_backlog_ids_json": jdump([vf.get("best_ticket_id")] if vf.get("best_ticket_id") else json.loads(linked_ws.get("matched_backlog_ids_json") or "[]")),
                "semantic_max_sim": align,
            })
        elif is_direct_gap:
            unified.append({
                "candidate_id": "UC-" + hashlib.sha1(f"{ctx.run_id}|direct|{p['problem_id']}".encode()).hexdigest()[:16],
                "discovery_source": "DIRECT_CLUSTER",
                "linked_problem_id": p["problem_id"],
                "title": p.get("title"),
                "hypothesis": f"Direct uncovered/partially covered customer problem: {p.get('problem_statement')}",
                "acceptance_criteria_json": jdump(["Given the reported problem evidence, when addressed, then target symptom frequency/effort should reduce.", "Given current backlog alignment, when solution is designed, then explicitly cover unsupported evidence themes.", "Given validation, when shipped, then re-measure against the same canonical problem."]),
                "evidence_strength_score": round(direct_score,4),
                "coverage_uncertainty": {"alignment": align, "relationship": rel, "note": "alignment similarity != proof of resolution"},
                "business_priority": float(p.get("priority_score") or 0),
                "score_components_json": jdump({"direct_score": direct_score, "priority_score": p.get("priority_score"), "alignment": align}),
                "lenses_triggered_json": jdump(["DIRECT_GAP"]),
                "supporting_feedback_ids_json": jdump(list(fids)[:400]),
                "matched_backlog_ids_json": jdump([vf.get("best_ticket_id")] if vf.get("best_ticket_id") else []),
                "semantic_max_sim": align,
            })

    # remaining whitespace-only
    for w in ws:
        if w["whitespace_id"] in used_ws: continue
        unified.append({
            "candidate_id": "UC-" + hashlib.sha1(f"{ctx.run_id}|ws|{w['whitespace_id']}".encode()).hexdigest()[:16],
            "discovery_source": "TRIANGULATED_WHITESPACE",
            "linked_problem_id": w.get("linked_problem_id"),
            "title": w.get("title"),
            "hypothesis": w.get("hypothesis"),
            "acceptance_criteria_json": w.get("acceptance_criteria_json"),
            "evidence_strength_score": float(w.get("whitespace_score") or 0),
            "coverage_uncertainty": {"semantic_max_sim": w.get("semantic_max_sim"), "note": "triangulated signal; corroboration not proof"},
            "business_priority": float(w.get("priority_score") or 0),
            "score_components_json": w.get("score_components_json"),
            "lenses_triggered_json": w.get("lenses_triggered_json"),
            "supporting_feedback_ids_json": w.get("supporting_feedback_ids_json"),
            "matched_backlog_ids_json": w.get("matched_backlog_ids_json"),
            "semantic_max_sim": w.get("semantic_max_sim"),
        })

    # rank by evidence strength then business priority (kept distinct)
    unified.sort(key=lambda x: (x.get("evidence_strength_score") or 0, x.get("business_priority") or 0), reverse=True)
    c = ctx.artifacts.write_json("unified/candidates.json", unified)
    # also persist triangulated whitespace table for WS-only (and keep); unified exposed via artifact/API
    ctx.artifacts.write_json("unified/summary.json", {"count": len(unified), "by_source": {}})
    ctx.record_artifact("unified_merger", "candidates", "unified/candidates.json", c)
    ctx.update_counts(whitespace_candidate_count=len(unified))
    ctx.module_done("unified_merger", input_count=len(problems)+len(ws), output_count=len(unified), message=f"unified candidates={len(unified)}")
    return {"unified": len(unified)}
