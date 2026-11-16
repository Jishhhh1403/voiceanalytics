from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from ...db.database import jdump
from ...orchestration.run_context import RunContext


def jaccard(a: set, b: set) -> float:
    if not a and not b: return 0.0
    inter = len(a & b); union = len(a | b)
    return inter/union if union else 0.0


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_h4_triangulation")
    dets = ctx.db.query("SELECT * FROM lens_detections WHERE run_id=?", (ctx.run_id,))
    # also include direct uncovered problems as DIRECT_GAP signals (optional merge input)
    problems = ctx.db.query("SELECT problem_id,title,journey_node_id,priority_score,supporting_feedback_ids_json FROM canonical_problems WHERE run_id=?", (ctx.run_id,))
    val = {r["problem_id"]: r for r in ctx.db.query("SELECT problem_id,relationship_type,alignment_score,best_ticket_id FROM validation_findings WHERE run_id=?", (ctx.run_id,))}
    by_lens = defaultdict(list)
    for d in dets:
        d["_fids"] = set(json.loads(d.get("supporting_feedback_ids_json") or "[]"))
        by_lens[d["lens"]].append(d)

    # naive triangulation: group detections across lenses sharing journey+intent or jaccard>=threshold
    used = set()
    candidates = []
    all_dets = dets[:]
    for i in range(len(all_dets)):
        if all_dets[i]["detection_id"] in used: continue
        group = [all_dets[i]]
        for j in range(i+1, len(all_dets)):
            if all_dets[j]["detection_id"] in used: continue
            a,b = all_dets[i], all_dets[j]
            share_tax = (a.get("journey_node_id") and a.get("journey_node_id")==b.get("journey_node_id") and a.get("intent") and a.get("intent")==b.get("intent"))
            jac = jaccard(a["_fids"], b["_fids"])
            if share_tax or jac >= ctx.settings.feedback_jaccard_threshold:
                # only merge across different lenses to count toward corroboration meaningfully
                if b["lens"] != a["lens"] or share_tax:
                    group.append(b)
        lenses = sorted(set(g["lens"] for g in group))
        for g in group: used.add(g["detection_id"])
        if len(lenses) >= ctx.settings.triangulation_min_lenses:
            # aggregate
            fids = set()
            for g in group: fids |= g["_fids"]
            s_graph = max([float(g.get("score") or 0) for g in group if g["lens"]=="graph"] or [0.0])
            s_spatial = max([float(g.get("score") or 0) for g in group if g["lens"]=="spatial"] or [0.0])
            s_comb = max([float(g.get("score") or 0) for g in group if g["lens"]=="combinatorial"] or [0.0])
            # backlog coverage from most relevant problem overlap (approx)
            c_backlog = 0.0
            linked_problem = None
            best_overlap = 0
            for p in problems:
                pf = set(json.loads(p["supporting_feedback_ids_json"] or "[]"))
                ov = len(pf & fids)
                if ov > best_overlap:
                    best_overlap = ov; linked_problem = p; vf = val.get(p["problem_id"]) or {}; c_backlog = float(vf.get("alignment_score") or 0)
            # if unknown coverage keep explicit; use 0 in formula but record uncertainty
            ws = 0.35*s_graph + 0.30*s_spatial + 0.20*s_comb + 0.15*(1.0 - c_backlog)
            title = (group[0].get("title") or "Triangulated whitespace candidate")[:120]
            wid = "WS-" + hashlib.sha1((ctx.run_id + "|".join(sorted(g["detection_id"] for g in group))).encode()).hexdigest()[:16]
            candidates.append({
                "whitespace_id": wid,
                "run_id": ctx.run_id,
                "discovery_source": "TRIANGULATED_WHITESPACE",
                "linked_problem_id": linked_problem["problem_id"] if linked_problem else None,
                "title": title,
                "hypothesis": f"Corroborated by {len(lenses)} lenses ({', '.join(lenses)}). Evidence suggests potential underserved friction; requires human validation (not proof).",
                "acceptance_criteria_json": jdump(["Given supporting evidence is reviewed, when product validates, then confirm whether capability gap exists.", "Given linked backlog items, when compared, then document resolution vs alignment gap.", "Given affected journey, when prioritized, then define measurable remediation outcome."]),
                "whitespace_score": round(ws,4),
                "priority_score": round(float(linked_problem.get("priority_score") or 0),4) if linked_problem else None,
                "semantic_max_sim": round(c_backlog,4),
                "graph_score": round(s_graph,4), "spatial_score": round(s_spatial,4), "combinatorial_score": round(s_comb,4),
                "lenses_triggered_json": jdump(lenses),
                "supporting_feedback_ids_json": jdump(list(fids)[:300]),
                "matched_backlog_ids_json": jdump([val.get(linked_problem["problem_id"],{}).get("best_ticket_id")] if linked_problem and val.get(linked_problem["problem_id"],{}).get("best_ticket_id") else []),
                "score_components_json": jdump({"graph":s_graph,"spatial":s_spatial,"combinatorial":s_comb,"coverage_c":c_backlog,"coverage_policy":"used max alignment of best-overlap problem; unknown treated as observed value 0.0 with uncertainty noted"}),
                "evidence_json": jdump({"detections":[g["detection_id"] for g in group], "lens_count": len(lenses)}),
            })
        # single-lens detections kept as provisional in artifacts only
    # persist triangulated
    if candidates:
        ctx.db.executemany(
            """INSERT OR REPLACE INTO whitespace_candidates
            (whitespace_id,run_id,discovery_source,linked_problem_id,title,hypothesis,acceptance_criteria_json,whitespace_score,priority_score,semantic_max_sim,
             graph_score,spatial_score,combinatorial_score,lenses_triggered_json,supporting_feedback_ids_json,matched_backlog_ids_json,score_components_json,evidence_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(
                c["whitespace_id"],c["run_id"],c["discovery_source"],c["linked_problem_id"],c["title"],c["hypothesis"],c["acceptance_criteria_json"],c["whitespace_score"],c["priority_score"],c["semantic_max_sim"],
                c["graph_score"],c["spatial_score"],c["combinatorial_score"],c["lenses_triggered_json"],c["supporting_feedback_ids_json"],c["matched_backlog_ids_json"],c["score_components_json"],c["evidence_json"]
            ) for c in candidates]
        )
    c = ctx.artifacts.write_json("triangulation/verified_whitespaces.json", candidates)
    ctx.record_artifact("module_h4_triangulation", "candidates", "triangulation/verified_whitespaces.json", c)
    ctx.module_done("module_h4_triangulation", input_count=len(dets), output_count=len(candidates), message=f"verified={len(candidates)}")
    return {"verified": len(candidates)}
