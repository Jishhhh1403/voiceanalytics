from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import numpy as np

from ...db.database import jdump
from ...orchestration.run_context import RunContext


def _kde(points, weights, grid_x, grid_y, bw=None):
    # simple gaussian kde on grid
    if len(points) == 0:
        return np.zeros((len(grid_y), len(grid_x)))
    pts = np.array(points)
    w = np.array(weights, dtype=float)
    w = w / (w.sum() + 1e-9)
    # bandwidth heuristic
    if bw is None:
        std = pts.std(axis=0) + 1e-3
        bw = std * (len(pts) ** (-1/6))
    bw = np.maximum(bw, 1e-3)
    Z = np.zeros((len(grid_y), len(grid_x)))
    for i, gx in enumerate(grid_x):
        for j, gy in enumerate(grid_y):
            diff = (pts - np.array([gx, gy])) / bw
            val = np.exp(-0.5 * (diff**2).sum(axis=1))
            Z[j, i] = (val * w).sum()
    return Z


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_h2_spatial")
    problems = ctx.db.query("SELECT problem_id,title,mds_x,mds_y,priority_score,mean_effort,supporting_feedback_ids_json,journey_node_id FROM canonical_problems WHERE run_id=? AND mds_x IS NOT NULL", (ctx.run_id,))
    backlog = ctx.db.query("SELECT backlog_id,title,journey_node_id FROM backlog_items WHERE run_id=?", (ctx.run_id,))
    if len(problems) < 2:
        ctx.warn("H2 skipped: insufficient problem coordinates")
        ctx.module_done("module_h2_spatial", len(problems), 0, "insufficient points")
        return {"detections": 0, "skipped": True}

    pts = np.array([[p["mds_x"], p["mds_y"]] for p in problems], dtype=float)
    weights = np.array([max(0.01, float(p.get("priority_score") or 0)/100.0) * max(0.5, float(p.get("mean_effort") or 1.0)/5.0) for p in problems])
    xmin,xmax = pts[:,0].min(), pts[:,0].max()
    ymin,ymax = pts[:,1].min(), pts[:,1].max()
    pad_x = (xmax-xmin)*0.2 + 1e-3
    pad_y = (ymax-ymin)*0.2 + 1e-3
    gx = np.linspace(xmin-pad_x, xmax+pad_x, ctx.settings.spatial_grid_size)
    gy = np.linspace(ymin-pad_y, ymax+pad_y, ctx.settings.spatial_grid_size)

    pain = _kde(pts, weights, gx, gy)
    # backlog projection heuristic: place near problems of same journey else global mean, low weight
    bpts = []
    bweights = []
    for b in backlog:
        # find problems with same journey
        same = [p for p in problems if p.get("journey_node_id") and p.get("journey_node_id")==b.get("journey_node_id")]
        if same:
            arr = np.array([[s["mds_x"], s["mds_y"]] for s in same])
            bpts.append(arr.mean(axis=0))
        else:
            bpts.append(pts.mean(axis=0))
        bweights.append(0.6)
    if bpts:
        backlog_kde = _kde(np.array(bpts), np.array(bweights), gx, gy)
    else:
        backlog_kde = np.zeros_like(pain)

    def norm01(A):
        mn, mx = float(A.min()), float(A.max())
        if mx-mn < 1e-12: return np.zeros_like(A)
        return (A-mn)/(mx-mn)
    pain_n = norm01(pain); back_n = norm01(backlog_kde)
    residual = np.maximum(0.0, pain_n - ctx.settings.void_backlog_factor * back_n)

    # find local maxima / peaks
    detections = []
    if residual.max() > 0.05:
        # simple peak picking by threshold & neighborhood
        thr = residual.max()*0.6
        R = 0.25 * max(xmax-xmin, ymax-ymin, 1e-3)
        cand = []
        for j in range(1, residual.shape[0]-1):
            for i in range(1, residual.shape[1]-1):
                val = residual[j,i]
                if val < thr: continue
                neigh = residual[j-1:j+2, i-1:i+2]
                if val >= neigh.max():
                    cand.append((val, gx[i], gy[j]))
        cand.sort(reverse=True)
        taken = []
        for val,x,y in cand[:10]:
            if any((x-tx)**2+(y-ty)**2 < (R*0.5)**2 for _,tx,ty in taken): continue
            taken.append((val,x,y))
            # supporting problems within R
            sup = []
            sup_fids = []
            for p in problems:
                dx = p["mds_x"]-x; dy = p["mds_y"]-y
                if dx*dx+dy*dy <= R*R:
                    sup.append(p["problem_id"])
                    sup_fids += json.loads(p["supporting_feedback_ids_json"] or "[]")
            did = "DET-S-" + hashlib.sha1(f"{ctx.run_id}|{x:.4f}|{y:.4f}".encode()).hexdigest()[:16]
            meta = {"x":x,"y":y,"radius":R,"residual":float(val),"supporting_problem_ids":sup}
            detections.append((did, ctx.run_id, "spatial", "void_region", None, None, float(val), float(val), "Residual pain region", "Candidate residual pain/low-backlog region (heuristic; not proof of missing capability).", jdump(list(dict.fromkeys(sup_fids))[:200]), jdump(meta), jdump({"projection":"heuristic_nearest_journey_mean","kde":"gaussian_grid"})))

    if detections:
        ctx.db.executemany("INSERT OR REPLACE INTO lens_detections(detection_id,run_id,lens,detector_type,journey_node_id,intent,score,raw_score,title,description,supporting_feedback_ids_json,evidence_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", detections)

    out = {
        "grid_x": gx.tolist(), "grid_y": gy.tolist(),
        "residual_max": float(residual.max()),
        "detections": len(detections),
        "method": {"projection": "heuristic journey-mean into existing MDS (not out-of-sample MDS)", "kde": "gaussian grid heuristic", "normalization": "min-max per surface baseline"},
    }
    c = ctx.artifacts.write_json("spatial/spatial_map.json", {**out, "pain_n_sampled": pain_n[::10,::10].tolist(), "residual_sampled": residual[::10,::10].tolist(), "backlog_n_sampled": back_n[::10,::10].tolist()})
    ctx.record_artifact("module_h2_spatial", "map", "spatial/spatial_map.json", c)
    ctx.module_done("module_h2_spatial", input_count=len(problems), output_count=len(detections), message=f"spatial detections={len(detections)}")
    return out
