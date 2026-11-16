from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction import DictVectorizer

from ...db.database import jdump
from ...orchestration.run_context import RunContext


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_h3_combinatorial")
    insights = ctx.db.query(
        """SELECT i.insight_id,i.feedback_id,i.journey_node_id,i.intent,i.symptom,i.emotion,i.effort_score,i.workarounds_json,i.is_open_set,
                  f.channel, t.signature_path
           FROM extracted_insights i JOIN feedback_records f ON f.run_id=i.run_id AND f.feedback_id=i.feedback_id
           LEFT JOIN taxonomy_nodes t ON t.node_id=i.journey_node_id
           WHERE i.run_id=?""", (ctx.run_id,)
    )
    findings = {r["problem_id"]: r for r in ctx.db.query("SELECT problem_id,relationship_type,alignment_score FROM validation_findings WHERE run_id=?", (ctx.run_id,))}
    # journey-intent lattice
    lattice = defaultdict(lambda: {"count":0, "efforts":[], "fids":set(), "problem_aligns":[]})
    for ins in insights:
        key = (ins.get("journey_node_id") or "OPEN_SET", ins.get("intent") or "general")
        cell = lattice[key]
        cell["count"] += 1
        try: cell["efforts"].append(float(ins.get("effort_score") or 0))
        except: pass
        cell["fids"].add(ins["feedback_id"])

    # alignments by journey (best from findings of problems in that journey)
    prob_rows = ctx.db.query("SELECT problem_id,journey_node_id FROM canonical_problems WHERE run_id=?", (ctx.run_id,))
    j_best_align = defaultdict(lambda: 0.0)
    for p in prob_rows:
        vf = findings.get(p["problem_id"])
        if vf:
            j_best_align[p.get("journey_node_id") or "OPEN_SET"] = max(j_best_align[p.get("journey_node_id") or "OPEN_SET"], float(vf.get("alignment_score") or 0))

    lattice_candidates = []
    for (journey,intent), v in lattice.items():
        if v["count"] < 10: continue
        mean_eff = (sum(v["efforts"])/len(v["efforts"])) if v["efforts"] else 0
        max_align = j_best_align.get(journey, 0.0)
        if mean_eff >= 3.8 and max_align < 0.25:
            lattice_candidates.append({"journey_node_id": journey, "intent": intent, "count": v["count"], "mean_effort": round(mean_eff,3), "max_backlog_alignment": round(max_align,3), "supporting_feedback_ids": list(v["fids"])[:200]})

    # NMF on behavioral matrix (intent,symptom,emotion,workaround,channel)
    feat_dicts = []
    idx_ids = []
    for ins in insights:
        tags = [w.get("tag") if isinstance(w,dict) else str(w) for w in json.loads(ins.get("workarounds_json") or "[]")]
        d = {
            f"intent:{ins.get('intent') or 'general'}": 1,
            f"symptom:{ins.get('symptom') or 'unknown'}": 1,
            f"emotion:{ins.get('emotion') or 'neutral'}": 1,
            f"channel:{ins.get('channel') or 'unknown'}": 1,
        }
        for t in tags: d[f"work:{t}"] = 1
        feat_dicts.append(d); idx_ids.append(ins["insight_id"])
    detections = []
    nmf_info = {"components": 0}
    if feat_dicts:
        dv = DictVectorizer(sparse=True)
        X = dv.fit_transform(feat_dicts)
        # ensure non-negative
        X = X.tocsr()
        k = min(ctx.settings.n_components_nmf, max(2, X.shape[0]-1), max(2, X.shape[1]-1))
        if k >= 2:
            try:
                nmf = NMF(n_components=k, init="nndsvda", max_iter=400, random_state=ctx.settings.random_seed)
                W = nmf.fit_transform(X)  # docs x comps
                H = nmf.components_
                fnames = dv.get_feature_names_out()
                # problem coverage lookup by feedback
                prob_fb_cov = {}
                for pr in ctx.db.query("SELECT problem_id,supporting_feedback_ids_json FROM canonical_problems WHERE run_id=?", (ctx.run_id,)):
                    cov = findings.get(pr["problem_id"], {}).get("relationship_type")
                    covered_flag = cov in ("COVERED","COVERED_BY_JUDGE")
                    for fid in json.loads(pr["supporting_feedback_ids_json"] or "[]"):
                        prob_fb_cov.setdefault(fid, False)
                        prob_fb_cov[fid] = prob_fb_cov[fid] or covered_flag
                # insight -> feedback
                ins_fb = {ins["insight_id"]: ins["feedback_id"] for ins in insights}
                ins_eff = {ins["insight_id"]: (float(ins.get("effort_score") or 0)) for ins in insights}
                nmf_info = {"components": k, "feature_count": len(fnames)}
                for c in range(k):
                    weights = W[:,c]
                    top_idx = np.argsort(-weights)[:50]
                    top_ids = [idx_ids[i] for i in top_idx if weights[i] > 0]
                    if not top_ids: continue
                    effs = [ins_eff.get(i,0) for i in top_ids]
                    mean_eff = sum(effs)/len(effs) if effs else 0
                    covered_share = 0.0
                    if top_ids:
                        covs = [1.0 if prob_fb_cov.get(ins_fb.get(i), False) else 0.0 for i in top_ids]
                        covered_share = sum(covs)/len(covs)
                    if mean_eff >= 4.0 and covered_share < 0.20:
                        top_feats = [fnames[j] for j in np.argsort(-H[c])[:10]]
                        fids = list(dict.fromkeys(ins_fb.get(i) for i in top_ids if ins_fb.get(i)))
                        did = "DET-C-" + hashlib.sha1(f"{ctx.run_id}|nmf|{c}".encode()).hexdigest()[:16]
                        meta = {"component": c, "top_features": top_feats, "mean_effort": round(mean_eff,3), "covered_share": round(covered_share,3), "members": len(top_ids)}
                        detections.append((did, ctx.run_id, "combinatorial", "nmf_component", None, None, float(min(1.0, mean_eff/5.0)), float(mean_eff), f"NMF component {c}", "Latent co-occurrence pattern (not automatically a business segment).", jdump(fids[:200]), jdump(meta), jdump({})))
            except Exception as e:
                ctx.warn(f"NMF failed: {e}")

    # lattice detections
    for cell in lattice_candidates:
        did = "DET-C-" + hashlib.sha1(f"{ctx.run_id}|lat|{cell['journey_node_id']}|{cell['intent']}".encode()).hexdigest()[:16]
        score = min(1.0, (cell["count"]/50.0)*0.5 + (cell["mean_effort"]/5.0)*0.5)
        detections.append((did, ctx.run_id, "combinatorial", "lattice_hole", cell["journey_node_id"], cell["intent"], score, float(cell["count"]), "High-effort low-coverage journey-intent", "Candidate journey×intent gap from lattice (heuristic).", jdump(cell["supporting_feedback_ids"]), jdump(cell), jdump({})))

    if detections:
        ctx.db.executemany("INSERT OR REPLACE INTO lens_detections(detection_id,run_id,lens,detector_type,journey_node_id,intent,score,raw_score,title,description,supporting_feedback_ids_json,evidence_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", detections)

    out = {"lattice_cells": len(lattice), "lattice_candidates": len(lattice_candidates), "nmf": nmf_info, "detections": len(detections), "traffic_adjusted_residual": {"status": "unavailable", "reason": "No real channel/journey traffic denominators provided (synthetic backlog context); feedback volume not used as traffic."}}
    c = ctx.artifacts.write_json("combinatorial/lattice_nmf.json", {**out, "lattice_candidates_sample": lattice_candidates[:50]})
    ctx.record_artifact("module_h3_combinatorial", "report", "combinatorial/lattice_nmf.json", c)
    ctx.module_done("module_h3_combinatorial", input_count=len(insights), output_count=len(detections), message=f"combinatorial detections={len(detections)}")
    return out
