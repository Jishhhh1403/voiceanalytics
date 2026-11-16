from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

from ...db.database import jdump
from ...orchestration.run_context import RunContext


def _load_csr(path):
    npz = np.load(path)
    return sparse.csr_matrix((npz["data"], npz["indices"], npz["indptr"]), shape=tuple(npz["shape"]))


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_d_clustering")
    try:
        X = _load_csr(ctx.artifacts.path("direct/tfidf_matrix.npz"))
        ids = ctx.artifacts.load_json("direct/insight_ids.json")
        beh = ctx.artifacts.load_json("direct/behavioral_features.json")
    except Exception as e:
        ctx.module_fail("module_d_clustering", f"Missing vector artifacts: {e}")
        raise

    n = X.shape[0]
    if n == 0:
        ctx.module_done("module_d_clustering", 0, 0, "no data")
        return {"clusters": 0}
    svd_n = min(ctx.settings.svd_components, max(2, X.shape[1] - 1), max(2, n - 1))
    if svd_n < 2:
        svd_n = 2
    svd = TruncatedSVD(n_components=svd_n, random_state=ctx.settings.random_seed)
    Xr = svd.fit_transform(X)
    Xr = normalize(Xr)

    labels = None
    method = "hdbscan"
    try:
        import hdbscan  # type: ignore
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min(ctx.settings.min_cluster_size, max(2, n)),
            min_samples=min(ctx.settings.min_samples, max(1, n)),
            metric="euclidean",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(Xr)
    except Exception as e:
        ctx.warn(f"HDBSCAN unavailable/failed ({e}); falling back to MiniBatchKMeans baseline")
        k = max(2, min(20, n // 10 or 2))
        km = MiniBatchKMeans(n_clusters=k, random_state=ctx.settings.random_seed, n_init=10)
        labels = km.fit_predict(Xr)
        method = "minibatch_kmeans_fallback"

    labels = np.array(labels)
    # mega-cluster guard
    counts = Counter(int(l) for l in labels if l != -1)
    final_labels = labels.copy()
    next_label = (max([l for l in counts] or [0]) + 1)
    split_info = []
    for lab, c in list(counts.items()):
        if c / max(1, n) > ctx.settings.mega_cluster_fraction and c >= 16:
            idx = np.where(labels == lab)[0]
            subk = min(8, max(2, len(idx)//10))
            if subk >= 2 and len(idx) >= subk:
                km2 = MiniBatchKMeans(n_clusters=subk, random_state=ctx.settings.random_seed, n_init=10)
                sub = km2.fit_predict(Xr[idx])
                for j, s in enumerate(sub):
                    final_labels[idx[j]] = next_label + int(s)
                split_info.append({"parent": int(lab), "size": int(c), "children": [int(next_label + i) for i in range(subk)]})
                next_label += subk

    # build cluster memberships
    beh_by_id = {b["insight_id"]: b for b in beh}
    cluster_rows = []
    for i, iid in enumerate(ids):
        lab = int(final_labels[i])
        cluster_id = f"CL-{ctx.run_id[-8:]}-N{lab}" if lab == -1 else f"CL-{ctx.run_id[-8:]}-{lab:04d}"
        b = beh_by_id.get(iid, {})
        cluster_rows.append((ctx.run_id, cluster_id, iid, b.get("feedback_id"), 1 if lab == -1 else 0, None))

    # open-set micro groups: is_open_set or noise with high effort; group by intent+symptom
    open_groups = defaultdict(list)
    for i, iid in enumerate(ids):
        b = beh_by_id.get(iid, {})
        lab = int(final_labels[i])
        effort = b.get("effort_raw") or 0
        if b.get("is_open_set") or (lab == -1 and effort >= ctx.settings.open_set_effort_threshold):
            key = (str(b.get("intent") or "general"), str(b.get("symptom") or "unknown").lower().strip())
            open_groups[key].append(iid)
    open_kept = {k: v for k, v in open_groups.items() if len(v) >= ctx.settings.open_set_min_count}
    # assign open-set cluster ids (additive labels for those groups) without deleting existing
    for gi, (key, members) in enumerate(open_kept.items(), 1):
        ocid = f"CL-{ctx.run_id[-8:]}-OS-{gi:04d}"
        for iid in members:
            b = beh_by_id.get(iid, {})
            cluster_rows.append((ctx.run_id, ocid, iid, b.get("feedback_id"), 0, None))

    ctx.db.executemany(
        "INSERT OR REPLACE INTO cluster_memberships(run_id,cluster_id,insight_id,feedback_id,is_noise,distance_to_centroid) VALUES(?,?,?,?,?,?)",
        cluster_rows,
    )

    non_noise = [l for l in final_labels if l != -1]
    report = {
        "method": method,
        "svd_components": svd_n,
        "n_insights": n,
        "n_clusters": len(set(non_noise)),
        "noise": int((final_labels == -1).sum()),
        "mega_cluster_splits": split_info,
        "open_set_groups": [{"intent": k[0], "symptom": k[1], "count": len(v)} for k, v in open_kept.items()],
        "open_set_group_count": len(open_kept),
        "params": {"min_cluster_size": ctx.settings.min_cluster_size, "min_samples": ctx.settings.min_samples, "metric": "euclidean"},
    }
    c = ctx.artifacts.write_json("direct/clusters_report.json", report)
    ctx.artifacts.write_json("direct/open_set_groups.json", report["open_set_groups"])
    ctx.record_artifact("module_d_clustering", "report", "direct/clusters_report.json", c)
    ctx.update_counts(cluster_count=report["n_clusters"] + report["open_set_group_count"])
    ctx.module_done("module_d_clustering", input_count=n, output_count=report["n_clusters"], message=f"clusters={report['n_clusters']} noise={report['noise']}", artifacts=report)
    return report
