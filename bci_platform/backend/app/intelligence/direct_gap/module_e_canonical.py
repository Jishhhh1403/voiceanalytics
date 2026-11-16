from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import MDS
from sklearn.preprocessing import normalize

from ...db.database import jdump
from ...orchestration.run_context import RunContext


def _load_csr(path):
    npz = np.load(path)
    return sparse.csr_matrix((npz["data"], npz["indices"], npz["indptr"]), shape=tuple(npz["shape"]))


def _safe_mean(vals):
    vals = [v for v in vals if v is not None]
    return float(sum(vals)/len(vals)) if vals else None


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_e_canonical")
    try:
        X = _load_csr(ctx.artifacts.path("direct/tfidf_matrix.npz"))
        ids = ctx.artifacts.load_json("direct/insight_ids.json")
    except Exception as e:
        ctx.module_fail("module_e_canonical", f"Missing artifacts: {e}")
        raise
    id_index = {iid: i for i, iid in enumerate(ids)}
    # cluster -> members (exclude noise-only primary labels except open-set)
    memberships = ctx.db.query("SELECT cluster_id, insight_id, feedback_id FROM cluster_memberships WHERE run_id=?", (ctx.run_id,))
    by_cluster = defaultdict(list)
    for m in memberships:
        if m["cluster_id"].endswith("-N-1") or "-N-1" == m["cluster_id"].split(ctx.run_id[-8:])[-1]:
            pass
        by_cluster[m["cluster_id"]].append(m)

    # insight details
    ins_rows = ctx.db.query(
        """SELECT i.*, f.cleaned_text, f.customer_tier, f.customer_id_hash, t.signature_path
           FROM extracted_insights i JOIN feedback_records f ON f.run_id=i.run_id AND f.feedback_id=i.feedback_id
           LEFT JOIN taxonomy_nodes t ON t.node_id=i.journey_node_id
           WHERE i.run_id=?""", (ctx.run_id,)
    )
    ins = {r["insight_id"]: r for r in ins_rows}

    problems = []
    cluster_vectors = {}
    for cid, members in by_cluster.items():
        # unique insights
        uids = list(dict.fromkeys(m["insight_id"] for m in members if m["insight_id"] in id_index))
        if not uids:
            continue
        if cid.split("-")[-2] == "N":  # noise bucket
            # keep as open-set evidence only if large enough, else skip as canonical problem
            if len(uids) < ctx.settings.open_set_min_count:
                continue
        idxs = [id_index[u] for u in uids]
        subX = X[idxs]
        centroid = np.asarray(subX.mean(axis=0)).ravel()
        # centroid-nearest representative (labeled per spec note)
        # distance in TFIDF space
        diffs = subX - centroid
        dists = np.sqrt(np.asarray((diffs.multiply(diffs)).sum(axis=1)).ravel()) if sparse.issparse(diffs) else np.linalg.norm(diffs, axis=1)
        rep_pos = int(np.argmin(dists)) if len(dists) else 0
        rep_iid = uids[rep_pos]
        rep = ins.get(rep_iid, {})
        cluster_vectors[cid] = centroid
        fids = list(dict.fromkeys(ins[u]["feedback_id"] for u in uids if u in ins))
        efforts = [ins[u].get("effort_score") for u in uids if u in ins]
        sents = [ins[u].get("sentiment") for u in uids if u in ins]
        neg_share = (sum(1 for s in sents if s is not None and float(s) < -0.3) / len(sents)) if sents else 0.0
        mean_effort = _safe_mean([float(e) for e in efforts if e is not None])
        tiers = [ins[u].get("customer_tier") for u in uids if u in ins]
        known_tiers = [t for t in tiers if t]
        high_tier_share = (sum(1 for t in known_tiers if str(t).lower() in ("premium","gold","high","priority","vip")) / len(known_tiers)) if known_tiers else 0.0
        # keywords proxy (top terms by centroid weights approximated via rep symptom/signature tokens)
        toks = []
        for u in uids[:50]:
            toks += str(ins[u].get("symptom","" )).lower().split()
            toks += str(ins[u].get("signature_path","" )).lower().replace(">"," ").split()
        common = [w for w,_ in Counter([t for t in toks if len(t)>2]).most_common(8)]
        det_label = f"[{rep.get('signature_path') or 'Unmapped'}] {rep.get('symptom') or 'issue'} ({', '.join(common[:3])})"
        title = (rep.get("symptom") or "Customer issue").replace("_"," ").strip().title()
        # priority
        V = math.log1p(len(fids))
        Vn = min(1.0, V / math.log1p(max(1, len(ids))))
        En = ((mean_effort or 1.0) - 1.0) / 4.0
        Sn = neg_share
        Tn = high_tier_share
        priority = 100.0 * (0.35*Vn + 0.35*En + 0.15*Sn + 0.15*Tn)
        comp = {"V_norm": Vn, "E_norm": En, "S_norm": Sn, "T_norm": Tn, "volume": len(fids), "missing_tier_share": 1.0 - (len(known_tiers)/len(tiers) if tiers else 1.0), "definition": "log-volume, mean-effort, neg-share(sent<-0.3), high-tier share over known tiers"}
        # top evidence
        top_ev = []
        for u in uids[:10]:
            rr = ins.get(u, {})
            top_ev.append({"insight_id": u, "feedback_id": rr.get("feedback_id"), "evidence_span": rr.get("evidence_span"), "enriched_sentence": rr.get("enriched_sentence")})
        pid = "CP-" + hashlib.sha1(f"{ctx.run_id}|{cid}".encode()).hexdigest()[:16]
        problems.append({
            "problem_id": pid,
            "run_id": ctx.run_id,
            "cluster_id": cid,
            "cluster_label": cid,
            "journey_node_id": rep.get("journey_node_id"),
            "title": title[:120],
            "problem_statement": det_label[:240],
            "deterministic_label": det_label[:240],
            "llm_label": None,
            "representative_insight_id": rep_iid,
            "representative_feedback_id": rep.get("feedback_id"),
            "representative_text": (rep.get("enriched_sentence") or rep.get("cleaned_text") or "")[:500],
            "keywords_json": jdump(common),
            "member_count": len(uids),
            "feedback_count": len(fids),
            "mean_effort": mean_effort,
            "negative_share": neg_share,
            "high_tier_share": high_tier_share,
            "priority_components_json": jdump(comp),
            "priority_score": round(priority, 4),
            "mds_x": None, "mds_y": None, "mds_stress": None,
            "is_open_set": 1 if "-OS-" in cid or "-N" in cid else 0,
            "supporting_feedback_ids_json": jdump(fids),
            "top_evidence_json": jdump(top_ev),
        })

    # MDS on cluster centroids (behavioral proxy via TFIDF centroids distance for scalability here)
    coords = {}
    stress_val = None
    if len(problems) >= 2:
        pids = [p["cluster_id"] for p in problems]
        M = np.vstack([cluster_vectors[c] for c in pids])
        # cosine distance matrix
        Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
        D = 1.0 - np.clip(Mn @ Mn.T, -1.0, 1.0)
        np.fill_diagonal(D, 0.0)
        try:
            try:
                mds = MDS(n_components=2, metric=False, init="random", random_state=ctx.settings.random_seed, normalized_stress="auto")
            except TypeError:
                mds = MDS(n_components=2, dissimilarity="precomputed", random_state=ctx.settings.random_seed, normalized_stress="auto")
            Y = mds.fit_transform(D)
            stress_val = float(getattr(mds, "stress_", 0.0) or 0.0)
            for i, p in enumerate(problems):
                p["mds_x"] = float(Y[i,0]); p["mds_y"] = float(Y[i,1]); p["mds_stress"] = stress_val
                coords[p["problem_id"]] = [p["mds_x"], p["mds_y"]]
        except Exception as e:
            ctx.warn(f"MDS failed: {e}")

    # persist
    if problems:
        ctx.db.executemany(
            """INSERT OR REPLACE INTO canonical_problems
            (problem_id,run_id,cluster_id,cluster_label,journey_node_id,title,problem_statement,deterministic_label,llm_label,
             representative_insight_id,representative_feedback_id,representative_text,keywords_json,member_count,feedback_count,
             mean_effort,negative_share,high_tier_share,priority_components_json,priority_score,mds_x,mds_y,mds_stress,
             is_open_set,supporting_feedback_ids_json,top_evidence_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(
                p["problem_id"],p["run_id"],p["cluster_id"],p["cluster_label"],p["journey_node_id"],p["title"],p["problem_statement"],p["deterministic_label"],p["llm_label"],
                p["representative_insight_id"],p["representative_feedback_id"],p["representative_text"],p["keywords_json"],p["member_count"],p["feedback_count"],
                p["mean_effort"],p["negative_share"],p["high_tier_share"],p["priority_components_json"],p["priority_score"],p["mds_x"],p["mds_y"],p["mds_stress"],
                p["is_open_set"],p["supporting_feedback_ids_json"],p["top_evidence_json"]
            ) for p in problems]
        )

    c = ctx.artifacts.write_json("direct/canonical_problems.json", problems)
    ctx.artifacts.write_json("direct/mds_coordinates.json", {"stress": stress_val, "coords": coords, "note": "Cluster MDS on TFIDF centroid cosine distance (reproducible, seeded). Behavioral Gower refinement can be added when full distance artifacts computed."})
    ctx.record_artifact("module_e_canonical", "problems", "direct/canonical_problems.json", c, {"count": len(problems)})
    ctx.module_done("module_e_canonical", input_count=len(by_cluster), output_count=len(problems), message=f"canonical problems={len(problems)}", artifacts={"count": len(problems), "mds_stress": stress_val})
    return {"problems": len(problems), "mds_stress": stress_val}
