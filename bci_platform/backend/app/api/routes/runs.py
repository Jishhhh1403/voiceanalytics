from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...config import Settings, get_settings
from ...db.database import Database

router = APIRouter(tags=["runs"])
_db: Database | None = None


def get_db(settings: Settings = Depends(get_settings)) -> Database:
    global _db
    if _db is None:
        _db = Database(settings.db_path)
    return _db


class ExportRequest(BaseModel):
    candidate_ids: list[str] = Field(default_factory=list)
    format: str = "json"


def _load_unified(run_id: str, settings: Settings):
    p = settings.artifacts_dir / run_id / "unified" / "candidates.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return []


@router.get("/runs")
def list_runs(db: Database = Depends(get_db)):
    return db.query(
        "SELECT run_id,status,current_module,feedback_count,cluster_count,uncovered_gap_count,whitespace_candidate_count,created_at,completed_at,error FROM pipeline_runs ORDER BY created_at DESC LIMIT 50"
    )


@router.get("/runs/{run_id}/status")
def get_run_status(run_id: str, db: Database = Depends(get_db)):
    run = db.query_one("SELECT * FROM pipeline_runs WHERE run_id=?", (run_id,))
    if not run:
        raise HTTPException(404, "Run not found")
    mods = db.query(
        "SELECT module,status,input_count,output_count,message,error,started_at,completed_at FROM pipeline_module_runs WHERE run_id=? ORDER BY id",
        (run_id,),
    )
    counts = {k: run.get(k) for k in ["feedback_count", "cluster_count", "uncovered_gap_count", "whitespace_candidate_count"]}
    warnings = json.loads(run.get("warnings_json") or "[]")
    return {"run_id": run_id, "status": run["status"], "current_module": run.get("current_module"), "modules": mods, "counts": counts, "warnings": warnings, "error": run.get("error"), "started_at": run.get("started_at"), "completed_at": run.get("completed_at")}


@router.get("/runs/{run_id}/gaps")
def get_gaps(run_id: str, source: str | None = None, min_score: float = 0.0, sort: str = "evidence", settings: Settings = Depends(get_settings), db: Database = Depends(get_db)):
    run = db.query_one("SELECT run_id FROM pipeline_runs WHERE run_id=?", (run_id,))
    if not run:
        raise HTTPException(404, "Run not found")
    items = _load_unified(run_id, settings)
    if source:
        items = [i for i in items if i.get("discovery_source") == source]
    items = [i for i in items if (i.get("evidence_strength_score") or 0) >= min_score]
    if sort == "priority":
        items.sort(key=lambda x: (x.get("business_priority") or 0), reverse=True)
    else:
        items.sort(key=lambda x: (x.get("evidence_strength_score") or 0), reverse=True)
    out = []
    for it in items:
        pid = it.get("linked_problem_id")
        prob = db.query_one(
            "SELECT problem_id,title,problem_statement,priority_score,feedback_count,mean_effort,journey_node_id,mds_x,mds_y FROM canonical_problems WHERE problem_id=?",
            (pid,),
        ) if pid else None
        vf = db.query_one(
            "SELECT relationship_type,alignment_score,best_ticket_id,top_candidates_json,reason FROM validation_findings WHERE run_id=? AND problem_id=?",
            (run_id, pid),
        ) if pid else None
        out.append({**it, "problem": prob, "validation": vf})
    return {"run_id": run_id, "count": len(out), "items": out}


@router.get("/runs/{run_id}/gaps/{candidate_id}/evidence")
def get_evidence(run_id: str, candidate_id: str, settings: Settings = Depends(get_settings), db: Database = Depends(get_db)):
    items = _load_unified(run_id, settings)
    cand = next((i for i in items if i.get("candidate_id") == candidate_id), None)
    if not cand:
        raise HTTPException(404, "Candidate not found")
    fids = json.loads(cand.get("supporting_feedback_ids_json") or "[]")[:50]
    feedback = []
    if fids:
        q = ",".join(["?"] * len(fids))
        feedback = db.query(
            f"SELECT feedback_id,channel,customer_tier,raw_text,cleaned_text,timestamp,platform,rating FROM feedback_records WHERE run_id=? AND feedback_id IN ({q})",
            (run_id, *fids),
        )
        ins = db.query(
            f"SELECT feedback_id,intent,aspect,symptom,sentiment,emotion,effort_score,evidence_span,evidence_start,evidence_end,workarounds_json,journey_node_id,enriched_sentence FROM extracted_insights WHERE run_id=? AND feedback_id IN ({q})",
            (run_id, *fids),
        )
        by_fb = {}
        for i in ins:
            by_fb.setdefault(i["feedback_id"], []).append(i)
        for f in feedback:
            f["insights"] = by_fb.get(f["feedback_id"], [])
    pid = cand.get("linked_problem_id")
    validation = db.query_one("SELECT * FROM validation_findings WHERE run_id=? AND problem_id=?", (run_id, pid)) if pid else None
    matches = db.query("SELECT * FROM backlog_problem_matches WHERE run_id=? AND problem_id=? ORDER BY rank", (run_id, pid)) if pid else []
    return {"candidate": cand, "feedback": feedback, "validation": validation, "matches": matches}


@router.get("/runs/{run_id}/gaps/{candidate_id}/lineage")
@router.get("/runs/{run_id}/lineage")
def get_lineage(run_id: str, candidate_id: str | None = None, settings: Settings = Depends(get_settings), db: Database = Depends(get_db)):
    unified = _load_unified(run_id, settings)
    if candidate_id:
        unified = [u for u in unified if u.get("candidate_id") == candidate_id]
    problems = db.query("SELECT problem_id,title,journey_node_id,representative_feedback_id,supporting_feedback_ids_json,priority_score FROM canonical_problems WHERE run_id=?", (run_id,))
    vals = db.query("SELECT problem_id,relationship_type,alignment_score,best_ticket_id,top_candidates_json,reason FROM validation_findings WHERE run_id=?", (run_id,))
    dets = db.query("SELECT detection_id,lens,detector_type,title,score,supporting_feedback_ids_json,evidence_json FROM lens_detections WHERE run_id=?", (run_id,))
    val_by_pid = {v["problem_id"]: v for v in vals}
    nodes = []
    edges = []
    for u in unified[:100]:
        uid = f"cand:{u['candidate_id']}"
        nodes.append({"id": uid, "type": "unified_candidate", "label": u.get("title"), "lane": 4, "data": {"source": u.get("discovery_source"), "score": u.get("evidence_strength_score")}})
        pid = u.get("linked_problem_id")
        if pid:
            p = next((x for x in problems if x["problem_id"] == pid), None)
            if p:
                pn = f"problem:{pid}"
                nodes.append({"id": pn, "type": "canonical_problem", "label": p.get("title"), "lane": 3, "data": {"priority": p.get("priority_score")}})
                edges.append({"source": pn, "target": uid, "type": "forms_candidate"})
                for fid in json.loads(p.get("supporting_feedback_ids_json") or "[]")[:8]:
                    fn = f"fb:{fid}"
                    nodes.append({"id": fn, "type": "feedback", "label": fid, "lane": 1})
                    inn = f"ins:{fid}"
                    nodes.append({"id": inn, "type": "insight", "label": f"signals:{fid}", "lane": 2})
                    edges.append({"source": fn, "target": inn, "type": "extracted"})
                    edges.append({"source": inn, "target": pn, "type": "clustered"})
                v = val_by_pid.get(pid)
                if v and v.get("best_ticket_id"):
                    bn = f"backlog:{v['best_ticket_id']}"
                    nodes.append({"id": bn, "type": "backlog_audit", "label": f"{v['best_ticket_id']} ({v.get('relationship_type')})", "lane": 5, "data": {"alignment": v.get("alignment_score"), "relationship": v.get("relationship_type")}})
                    edges.append({"source": uid, "target": bn, "type": "audited_against", "dashed": v.get("relationship_type") not in ("COVERED", "COVERED_BY_JUDGE")})
    # dedupe
    seen = set()
    uniq = []
    for n in nodes:
        if n["id"] in seen:
            continue
        seen.add(n["id"])
        uniq.append(n)
    return {"nodes": uniq, "edges": edges}


@router.get("/runs/{run_id}/spatial-map")
def get_spatial(run_id: str, settings: Settings = Depends(get_settings), db: Database = Depends(get_db)):
    p = settings.artifacts_dir / run_id / "spatial" / "spatial_map.json"
    if not p.exists():
        raise HTTPException(404, "Spatial map not available")
    data = json.loads(p.read_text(encoding="utf-8"))
    probs = db.query("SELECT problem_id,title,mds_x,mds_y,priority_score,feedback_count,journey_node_id FROM canonical_problems WHERE run_id=? AND mds_x IS NOT NULL", (run_id,))
    data["problems"] = probs
    return data


@router.get("/runs/{run_id}/graph-motifs")
def get_graph(run_id: str, settings: Settings = Depends(get_settings)):
    p = settings.artifacts_dir / run_id / "graph" / "motifs.json"
    g = settings.artifacts_dir / run_id / "graph" / "graph.json"
    if not p.exists():
        raise HTTPException(404, "Graph motifs not available")
    data = json.loads(p.read_text(encoding="utf-8"))
    if g.exists():
        data["graph_summary"] = json.loads(g.read_text(encoding="utf-8"))
    return data


@router.post("/runs/{run_id}/export-backlog")
def export_backlog(run_id: str, req: ExportRequest, settings: Settings = Depends(get_settings)):
    items = _load_unified(run_id, settings)
    if req.candidate_ids:
        sel = set(req.candidate_ids)
        items = [i for i in items if i.get("candidate_id") in sel]
    if req.format == "csv":
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["candidate_id", "discovery_source", "title", "evidence_strength_score", "business_priority", "linked_problem_id", "hypothesis"])
        for i in items:
            w.writerow([i.get("candidate_id"), i.get("discovery_source"), i.get("title"), i.get("evidence_strength_score"), i.get("business_priority"), i.get("linked_problem_id"), i.get("hypothesis")])
        out.seek(0)
        return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=backlog_{run_id}.csv"})
    return {"run_id": run_id, "count": len(items), "candidates": items}
