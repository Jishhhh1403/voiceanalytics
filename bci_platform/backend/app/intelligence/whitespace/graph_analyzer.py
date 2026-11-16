from __future__ import annotations

import hashlib
import json
from collections import defaultdict, Counter
from datetime import datetime
from typing import Any

import networkx as nx

from ...db.database import jdump
from ...orchestration.run_context import RunContext


def _parse_ts(ts):
    if not ts: return None
    try:
        if ts.endswith("Z"): ts = ts[:-1]+"+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_h1_graph")
    insights = ctx.db.query(
        """SELECT i.insight_id,i.feedback_id,i.journey_node_id,i.intent,i.aspect,i.symptom,i.effort_score,i.workarounds_json,
                  f.customer_id_hash,f.timestamp
           FROM extracted_insights i JOIN feedback_records f ON f.run_id=i.run_id AND f.feedback_id=i.feedback_id
           WHERE i.run_id=?""", (ctx.run_id,)
    )
    findings = ctx.db.query("SELECT problem_id,best_ticket_id,alignment_score,relationship_type FROM validation_findings WHERE run_id=?", (ctx.run_id,))
    covered_by_problem = {f["problem_id"]: f for f in findings}
    # map feedback->problems (via supporting ids)
    problems = ctx.db.query("SELECT problem_id, supporting_feedback_ids_json, priority_score FROM canonical_problems WHERE run_id=?", (ctx.run_id,))
    fb_to_problems = defaultdict(list)
    for p in problems:
        for fid in json.loads(p["supporting_feedback_ids_json"] or "[]"):
            fb_to_problems[fid].append(p)

    G = nx.DiGraph()
    edge_evidence = defaultdict(list)

    def add_edge(u,v,etype,weight=1.0,ev=None):
        if G.has_edge(u,v):
            G[u][v]["weight"] = G[u][v].get("weight",0)+weight
        else:
            G.add_edge(u,v,type=etype,weight=weight)
        if ev: edge_evidence[(u,v,etype)].append(ev)

    # nodes/edges
    cust_symptoms = defaultdict(list)  # cust -> [(ts, feedback, symptom_node)]
    for ins in insights:
        fid = ins["feedback_id"]
        j = f"node:{ins['journey_node_id'] or 'OPEN_SET'}"
        intent = f"intent:{(ins['intent'] or 'general')}"
        aspect = f"aspect:{(ins['aspect'] or 'general')}"
        sym = f"symp:{(ins['symptom'] or 'unknown')}"
        for n, t in [(j,"journey"),(intent,"intent"),(aspect,"aspect"),(sym,"symptom")]:
            if not G.has_node(n): G.add_node(n, ntype=t)
        # CO_OCCURS within feedback
        w = float(ins.get("effort_score") or 1.0)
        for a,b in [(j,intent),(j,aspect),(intent,sym),(aspect,sym)]:
            add_edge(a,b,"CO_OCCURS",w,fid); add_edge(b,a,"CO_OCCURS",w,fid)
        # ESCAPES_TO + symptom workaround relation (explicit to satisfy Motif 1 contract)
        wtags = json.loads(ins.get("workarounds_json") or "[]")
        for wt in wtags:
            tag = wt.get("tag") if isinstance(wt, dict) else str(wt)
            wn = f"work:{tag}"
            if not G.has_node(wn): G.add_node(wn, ntype="workaround")
            add_edge(intent, wn, "ESCAPES_TO", w, fid)
            add_edge(j, wn, "ESCAPES_TO", w, fid)
            add_edge(sym, wn, "WORKAROUND_OF", w, fid)  # evidence-backed same-feedback relation for motif path
        # temporal collection
        cust = ins.get("customer_id_hash")
        ts = _parse_ts(ins.get("timestamp"))
        if cust and ts:
            cust_symptoms[cust].append((ts, fid, sym))

    # FOLLOWED_BY within window per customer
    window_days = ctx.settings.graph_followed_by_days
    for cust, evs in cust_symptoms.items():
        evs.sort(key=lambda x: x[0])
        for i in range(len(evs)):
            for j in range(i+1, len(evs)):
                dt = (evs[j][0]-evs[i][0]).total_seconds()/86400.0
                if dt > window_days: break
                if evs[i][2] == evs[j][2] or evs[i][1] == evs[j][1]: continue
                add_edge(evs[i][2], evs[j][2], "FOLLOWED_BY", 1.0, {"from": evs[i][1], "to": evs[j][1], "customer": cust[:8], "days": round(dt,2)})

    # ADDRESSED_BY (provisional associations from validation)
    # connect journey/intent nodes of problem's representative evidence to best ticket when alignment >= threshold or covered-like
    prob_meta = {p["problem_id"]: p for p in problems}
    val_rows = ctx.db.query("SELECT * FROM validation_findings WHERE run_id=?", (ctx.run_id,))
    for vf in val_rows:
        if not vf.get("best_ticket_id"): continue
        score = float(vf.get("alignment_score") or 0)
        if score < ctx.settings.graph_addressed_by_threshold and vf.get("relationship_type") not in ("COVERED","COVERED_BY_JUDGE"):
            continue
        p = prob_meta.get(vf["problem_id"])
        if not p: continue
        # find intents/journeys from supporting insights
        fids = json.loads(p["supporting_feedback_ids_json"] or "[]")[:20]
        if not fids: continue
        qmarks = ",".join(["?"]*len(fids))
        ins2 = ctx.db.query(f"SELECT journey_node_id,intent FROM extracted_insights WHERE run_id=? AND feedback_id IN ({qmarks})", (ctx.run_id, *fids))
        bn = f"backlog:{vf['best_ticket_id']}"
        if not G.has_node(bn): G.add_node(bn, ntype="backlog")
        for r in ins2:
            for src in [f"intent:{(r['intent'] or 'general')}", f"node:{r['journey_node_id'] or 'OPEN_SET'}"]:
                if G.has_node(src): add_edge(src,bn,"ADDRESSED_BY",score,vf["problem_id"])

    # Motif 1: workaround escape Intent -> Symptom -> Workaround (path exists via CO_OCCURS + WORKAROUND_OF/ESCAPES_TO evidence) with no intent ADDRESSED_BY
    motif1 = []
    # aggregate by (intent,symptom,workaround)
    m1_groups = defaultdict(lambda: {"count":0,"efforts":[],"fids":set(),"intents":set()})
    for ins in insights:
        wtags = json.loads(ins.get("workarounds_json") or "[]")
        if not wtags: continue
        intent = f"intent:{(ins['intent'] or 'general')}"
        sym = f"symp:{(ins['symptom'] or 'unknown')}"
        # check intent not addressed
        addressed = any(d.get("type")=="ADDRESSED_BY" for _,_,d in G.out_edges(intent, data=True)) if G.has_node(intent) else False
        if addressed: continue
        for wt in wtags:
            tag = wt.get("tag") if isinstance(wt, dict) else str(wt)
            key = (intent,sym,tag)
            m1_groups[key]["count"] += 1
            m1_groups[key]["efforts"].append(float(ins.get("effort_score") or 0))
            m1_groups[key]["fids"].add(ins["feedback_id"])
            m1_groups[key]["intents"].add(intent)
    for (intent,sym,tag), v in m1_groups.items():
        if v["count"] >= ctx.settings.motif_min_support:
            raw = v["count"] * (sum(v["efforts"])/len(v["efforts"]) if v["efforts"] else 1.0)
            motif1.append({"type":"workaround_escape","intent":intent,"symptom":sym,"workaround":tag,"count":v["count"],"mean_effort": (sum(v["efforts"])/len(v["efforts"]) if v["efforts"] else None),"raw_score": raw,"supporting_feedback_ids": list(v["fids"])[:200]})

    # Motif 2: temporal friction chain symptom A->B, count>=5, lift>=2, downstream not addressed
    transitions = Counter()
    out_count = Counter(); in_count = Counter()
    for u,v,d in G.edges(data=True):
        if d.get("type")=="FOLLOWED_BY":
            transitions[(u,v)] += 1; out_count[u]+=1; in_count[v]+=1
    Ntrans = sum(transitions.values()) or 1
    motif2 = []
    for (a,b), c in transitions.items():
        if c < ctx.settings.motif_min_support: continue
        lift = (c * Ntrans) / max(1, out_count[a]*in_count[b])
        if lift < 2.0: continue
        # downstream addressed?
        addressed_b = any(x[0].startswith("intent:") and any(dd.get("type")=="ADDRESSED_BY" for _,_,dd in G.out_edges(x[0], data=True)) for x in G.in_edges(b))
        # simpler: any predecessor intent addressed - conservative
        addressed = False
        for pred in G.predecessors(b):
            if pred.startswith("intent:") and any(dd.get("type")=="ADDRESSED_BY" for _,_,dd in G.out_edges(pred, data=True)):
                addressed = True
        if addressed: continue
        import math
        raw = math.log(1+c)*lift
        # collect evidence
        evs = edge_evidence.get((a,b,"FOLLOWED_BY"), [])[:200]
        motif2.append({"type":"temporal_chain","from":a,"to":b,"count":c,"lift": round(lift,4),"raw_score": raw,"evidence": evs})

    # Motif 3: bridge nodes top 15% betweenness on undirected projection (journey/aspect), no ADDRESSED_BY
    UG = nx.Graph()
    for n,d in G.nodes(data=True):
        if d.get("ntype") in ("journey","aspect"): UG.add_node(n, **d)
    for u,v,d in G.edges(data=True):
        if u in UG and v in UG: UG.add_edge(u,v)
    motif3 = []
    if UG.number_of_nodes() > 2:
        bc = nx.betweenness_centrality(UG, normalized=True)
        vals = sorted(bc.values())
        thresh = vals[int(0.85*len(vals))] if vals else 0
        for n, val in bc.items():
            if val < thresh: continue
            addressed = any(dd.get("type")=="ADDRESSED_BY" for _,_,dd in G.out_edges(n, data=True)) if G.has_node(n) else False
            if addressed: continue
            motif3.append({"type":"bridge_node","node":n,"betweenness": round(val,6),"raw_score": val})

    # normalize scores within each detector
    def norm_scores(items, key="raw_score"):
        if not items: return
        vals = [x[key] for x in items]
        mn, mx = min(vals), max(vals)
        for x in items:
            x["score"] = 0.5 if mx==mn else (x[key]-mn)/(mx-mn)

    norm_scores(motif1); norm_scores(motif2); norm_scores(motif3)

    detections = []
    for m in motif1+motif2+motif3:
        did = "DET-G-" + hashlib.sha1((ctx.run_id+json.dumps(m,sort_keys=True,default=str)).encode()).hexdigest()[:16]
        fids = m.get("supporting_feedback_ids") or [e.get("from") for e in m.get("evidence",[]) if isinstance(e,dict) and e.get("from")] or []
        detections.append((did, ctx.run_id, "graph", m["type"], None, m.get("intent"), float(m.get("score",0)), float(m.get("raw_score",0)), m["type"], json.dumps(m,default=str)[:500], jdump(list(dict.fromkeys(fids))[:200]), jdump(m), jdump({})))

    if detections:
        ctx.db.executemany("INSERT OR REPLACE INTO lens_detections(detection_id,run_id,lens,detector_type,journey_node_id,intent,score,raw_score,title,description,supporting_feedback_ids_json,evidence_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", detections)

    graph_out = {"nodes": [{"id":n, **d} for n,d in G.nodes(data=True)], "edges": [{"source":u,"target":v, **d} for u,v,d in G.edges(data=True)]}
    # trim for artifact size
    if len(graph_out["edges"]) > 5000:
        graph_out["edges_truncated"] = True
        graph_out["edges"] = graph_out["edges"][:5000]
    c = ctx.artifacts.write_json("graph/motifs.json", {"motif1": motif1, "motif2": motif2, "motif3": motif3, "counts": {"m1":len(motif1),"m2":len(motif2),"m3":len(motif3)}})
    ctx.artifacts.write_json("graph/graph.json", {"node_count": G.number_of_nodes(), "edge_count": G.number_of_edges(), "sample_edges": graph_out["edges"][:200]})
    ctx.record_artifact("module_h1_graph", "motifs", "graph/motifs.json", c)
    ctx.module_done("module_h1_graph", input_count=len(insights), output_count=len(detections), message=f"detections={len(detections)}")
    return {"detections": len(detections), "nodes": G.number_of_nodes(), "edges": G.number_of_edges()}
