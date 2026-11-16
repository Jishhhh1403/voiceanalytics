import React, { useEffect, useState } from 'react';
import * as api from './services/api';
import SpatialMap from './components/SpatialMap';
import LineageGraph from './components/LineageGraph';
import GraphMotifs from './components/GraphMotifs';

type View = 'overview'|'gaps'|'spatial'|'graph'|'lineage'|'evidence';

class Boundary extends React.Component<{children:any},{err:any}>{ 
  constructor(p:any){super(p);this.state={err:null};}
  static getDerivedStateFromError(err:any){return {err};}
  render(){ if(this.state.err) return <div className="card error-card"><b>View error:</b><pre style={{marginTop:8}}>{String(this.state.err?.message||this.state.err)}{'\n'}{String(this.state.err?.stack||'')}</pre></div>; return this.props.children as any; }
}

function ScoreBar({label, value, hint}:{label:string,value:number|undefined|null,hint?:string}){
  const v = Math.max(0, Math.min(1, Number(value||0)));
  return <div className="score-row"><div className="row" style={{justifyContent:'space-between'}}><span className="muted">{label}{hint?` · ${hint}`:''}</span><b>{v.toFixed(3)}</b></div><div className="bar"><div className="bar-fill" style={{width:`${v*100}%`}}/></div></div>;
}
function Tag({children, tone='neutral'}:{children:any, tone?:'neutral'|'good'|'warn'|'bad'|'info'}){
  return <span className={`tag tag-${tone}`}>{children}</span>;
}
function Stat({label,value,sub}:{label:string,value:any,sub?:string}){
  return <div className="stat"><div className="stat-val">{value}</div><div className="stat-label">{label}</div>{sub && <div className="muted">{sub}</div>}</div>;
}
function safeParse(s:any){
  if (s==null) return s;
  if (typeof s!=='string') return s;
  try{ return JSON.parse(s); }catch{ return s; }
}
function asArray(v:any){ const x=safeParse(v); return Array.isArray(x)?x: (x?[]:[]); }

export default function App(){
  const [view,setView]=useState<View>('overview');
  const [runs,setRuns]=useState<any[]>([]);
  const [runId,setRunId]=useState<string>('');
  const [status,setStatus]=useState<any>(null);
  const [gaps,setGaps]=useState<any[]>([]);
  const [selected,setSelected]=useState<any>(null);
  const [evidence,setEvidence]=useState<any>(null);
  const [spatial,setSpatial]=useState<any>(null);
  const [graph,setGraph]=useState<any>(null);
  const [lineage,setLineage]=useState<any>(null);
  const [candLineage,setCandLineage]=useState<any>(null);
  const [sourceFilter,setSourceFilter]=useState<string>('');
  const [meta,setMeta]=useState<any>(null);
  const [loading,setLoading]=useState<string>('');
  const [err,setErr]=useState<string>('');

  async function refreshRuns(){ try{ const r=await api.listRuns(); setRuns(r||[]); if(!runId && r?.[0]) setRunId(r[0].run_id);}catch(e:any){setErr(String(e?.message||e));} }
  useEffect(()=>{ refreshRuns(); fetch('/api/v1/meta/source').then(r=>r.json()).then(setMeta).catch(()=>{}); },[]);
  useEffect(()=>{ if(!runId) return; (async()=>{ try{ setStatus(await api.getStatus(runId)); const g=await api.getGaps(runId); setGaps(g?.items||[]);}catch(e:any){setErr(String(e?.message||e));}})(); },[runId]);

  async function start(){ setLoading('starting'); setErr(''); try{ const r=await api.startRun(); setRunId(r.run_id); setTimeout(refreshRuns,1000);}catch(e:any){setErr(String(e?.message||e));} finally{setLoading('');}}
  async function refreshStatus(){ if(!runId) return; try{ setStatus(await api.getStatus(runId)); const g=await api.getGaps(runId); setGaps(g?.items||[]);}catch(e:any){setErr(String(e?.message||e));} }

  async function openCandidate(c:any){
    setSelected(c); setEvidence(null); setCandLineage(null); setErr(''); setView('evidence'); setLoading('evidence');
    try{
      const [evRes, linRes] = await Promise.allSettled([
        api.getEvidence(runId, c.candidate_id),
        api.getLineage(runId, c.candidate_id),
      ]);
      if (evRes.status==='fulfilled') setEvidence(evRes.value); else setErr(`Evidence: ${String((evRes as any).reason?.message || evRes.reason)}`);
      if (linRes.status==='fulfilled') setCandLineage(linRes.value); else console.warn('candidate lineage failed', linRes.reason);
    } finally { setLoading(''); }
  }
  async function loadSpatial(){ if(!runId) return; setLoading('spatial'); try{ setSpatial(await api.getSpatial(runId)); }catch(e:any){setErr(String(e?.message||e));} finally{setLoading('');}}
  async function loadGraph(){ if(!runId) return; setLoading('graph'); try{ setGraph(await api.getGraph(runId)); }catch(e:any){setErr(String(e?.message||e));} finally{setLoading('');}}
  async function loadLineage(){ if(!runId) return; setLoading('lineage'); try{ setLineage(await api.getLineage(runId)); }catch(e:any){setErr(String(e?.message||e));} finally{setLoading('');}}

  useEffect(()=>{ if(view==='spatial') loadSpatial(); if(view==='graph') loadGraph(); if(view==='lineage') loadLineage(); },[view,runId]);

  const filtered = gaps.filter(g=> !sourceFilter || g.discovery_source===sourceFilter);
  const counts = status?.counts||{};
  const nav: {id:View,label:string,icon:string}[] = [
    {id:'overview',label:'Overview',icon:'◫'},{id:'gaps',label:'Gap Feed',icon:'▤'},{id:'spatial',label:'Spatial Map',icon:'◔'},{id:'graph',label:'Graph Motifs',icon:'⬡'},{id:'lineage',label:'Lineage',icon:'⇄'},{id:'evidence',label:'Evidence',icon:'⎘'}
  ];

  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">BCI</div><div><div className="brand-title">Customer Intelligence</div><div className="muted">Modules A–H · evidence-backed</div></div></div>
      <div className="row" style={{marginTop:14}}>
        <button className="btn" onClick={start} disabled={loading==='starting'}>{loading==='starting'?'Starting…':'Start Run'}</button>
        <button className="btn secondary" onClick={refreshRuns}>Refresh</button>
      </div>
      <div style={{marginTop:12}}>
        <label className="muted">Run</label>
        <select value={runId} onChange={e=>setRunId(e.target.value)} style={{width:'100%',marginTop:4}}>
          <option value="">Select run</option>
          {runs.map(r=> <option key={r.run_id} value={r.run_id}>{r.run_id} · {r.status}</option>)}
        </select>
        <button className="btn secondary" style={{marginTop:6,width:'100%'}} onClick={refreshStatus}>Refresh Status</button>
      </div>
      <nav className="nav">
        {nav.map(v=> <button key={v.id} className={`nav-item ${view===v.id?'active':''}`} onClick={()=>setView(v.id)}><span className="nav-icon">{v.icon}</span>{v.label}</button>)}
      </nav>
      <div className="sidebar-foot muted">Gap feed · spatial voids · friction motifs · 5-lane lineage · evidence drawer</div>
    </aside>

    <main className="main">
      <div className="topbar">
        <div>
          <h1 className="page-title">{nav.find(n=>n.id===view)?.label}</h1>
          <div className="muted">{runId?`Run ${runId}`:'No run selected'} {status?.status?`· ${status.status}`:''}</div>
        </div>
        {view==='gaps' && <div className="row"><select value={sourceFilter} onChange={e=>setSourceFilter(e.target.value)}><option value="">All sources</option><option>DIRECT_CLUSTER</option><option>TRIANGULATED_WHITESPACE</option><option>BOTH</option></select><span className="pill">{filtered.length} candidates</span></div>}
      </div>

      <div className="warn"><b>Interpretation:</b> Bundled data is synthetic. Scores/similarity are signals, <b>not proof</b> of root cause, missing capability, or delivered resolution. H3 traffic-adjusted residual unavailable. LLM/judge outputs are proposals.</div>
      {err && <div className="card error-card">Error: <pre style={{margin:0}}>{err}</pre></div>}

      <Boundary key={view + ':' + runId + ':' + (selected?.candidate_id||'')}>
      {view==='overview' && <div>
        <div className="stats-grid">
          <Stat label="Run status" value={<span className={`status-dot s-${(status?.status||'').toLowerCase()}`}>{status?.status||'n/a'}</span>} sub={status?.current_module||'-'} />
          <Stat label="Feedback" value={counts.feedback_count||0} />
          <Stat label="Clusters" value={counts.cluster_count||0} />
          <Stat label="Uncovered gaps" value={counts.uncovered_gap_count||0} sub="vs backlog (signal)" />
          <Stat label="Candidates" value={counts.whitespace_candidate_count||0} sub="unified" />
        </div>
        <div className="grid-2">
          <div className="card"><h3>Source & Environment</h3><pre>{JSON.stringify(meta,null,2)}</pre></div>
          <div className="card"><h3>Module Pipeline</h3>
            <table><thead><tr><th>Module</th><th>Status</th><th>Out</th><th>Message</th></tr></thead><tbody>
              {(status?.modules||[]).map((m:any)=><tr key={m.module}><td><b>{m.module}</b></td><td><span className={`tag tag-${m.status==='COMPLETED'?'good':m.status==='FAILED'?'bad':m.status==='RUNNING'?'info':'neutral'}`}>{m.status}</span></td><td>{m.output_count??'—'}</td><td className="muted">{m.message||m.error||''}</td></tr>)}
              {!(status?.modules||[]).length && <tr><td colSpan={4} className="muted">No module runs yet.</td></tr>}
            </tbody></table>
          </div>
        </div>
      </div>}

      {view==='gaps' && <div className="gap-list">
        {filtered.map(c=> { const sc=safeParse(c.score_components_json)||{}; const lenses=asArray(c.lenses_triggered_json);
          return <div className="card gap-card" key={c.candidate_id} onClick={()=>openCandidate(c)}>
            <div className="row" style={{justifyContent:'space-between',alignItems:'flex-start'}}>
              <div style={{flex:1}}>
                <div className="row" style={{gap:8,marginBottom:6}}><Tag tone={c.discovery_source==='BOTH'?'warn':c.discovery_source==='TRIANGULATED_WHITESPACE'?'info':'good'}>{c.discovery_source}</Tag>{lenses.map((l:string,i:number)=><Tag key={i}>{l}</Tag>)}<span className="muted">{c.candidate_id}</span></div>
                <h3 style={{marginBottom:4}}>{c.title||'(untitled)'}</h3>
                <div className="muted">{String(c.problem?.problem_statement||c.hypothesis||'').slice(0,180)}</div>
              </div>
              <div className="score-badges"><div className="score-badge"><span>Evidence</span><b>{Number(c.evidence_strength_score||0).toFixed(2)}</b></div><div className="score-badge pri"><span>Priority</span><b>{Number(c.business_priority||0).toFixed(1)}</b></div></div>
            </div>
            <div className="grid-3" style={{marginTop:10}}>
              <ScoreBar label="Evidence strength" value={c.evidence_strength_score}/>
              <ScoreBar label="Backlog alignment" value={c.semantic_max_sim} hint="similarity, not resolution"/>
              <ScoreBar label="Graph/lens signal" value={sc.graph}/>
            </div>
            <div className="row" style={{justifyContent:'space-between',marginTop:8}}>
              <span className="muted">Validation: <b>{c.validation?.relationship_type||'n/a'}</b> · best ticket: {c.validation?.best_ticket_id||'n/a'}</span>
              <button className="btn secondary" onClick={(e)=>{e.stopPropagation(); openCandidate(c);}}>Open evidence →</button>
            </div>
          </div>; })}
        {!filtered.length && <div className="card muted">No candidates. Start/select a run and refresh.</div>}
      </div>}

      {view==='spatial' && <div>
        <div className="card muted">Interactive MDS projection of canonical problems. Scroll to zoom, drag to pan. Heat = residual pain (heuristic), <b>not proof</b> of missing capability. {loading==='spatial'?'Loading…':''}</div>
        {spatial ? <SpatialMap data={spatial}/> : <div className="card muted">No spatial data loaded.</div>}
      </div>}

      {view==='graph' && <div>
        <div className="card muted">Evidence-backed friction/workaround motifs and sampled graph. Associations are <b>not causal</b>. {loading==='graph'?'Loading…':''}</div>
        {graph ? <GraphMotifs data={graph}/> : <div className="card muted">No graph data loaded.</div>}
      </div>}

      {view==='lineage' && <div>
        <div className="card muted">End-to-end traceability across 5 lanes. {loading==='lineage'?'Loading…':''}</div>
        {lineage ? <LineageGraph data={lineage}/> : <div className="card muted">No lineage data loaded.</div>}
      </div>}

      {view==='evidence' && <div>
        {!selected && <div className="card">Select a candidate from <b>Gap Feed</b> to inspect evidence and lineage.</div>}
        {selected && <div>
          <div className="card evidence-hero">
            <div className="row" style={{justifyContent:'space-between',alignItems:'flex-start'}}>
              <div>
                <div className="row" style={{marginBottom:6}}><Tag tone={selected.discovery_source==='BOTH'?'warn':'info'}>{selected.discovery_source||'candidate'}</Tag><span className="muted">{selected.candidate_id}</span></div>
                <h2 style={{margin:'0 0 6px 0'}}>{selected.title||'(untitled)'}</h2>
                <div>{String(selected.problem?.problem_statement||selected.hypothesis||'')}</div>
              </div>
              <div className="score-badges"><div className="score-badge"><span>Evidence</span><b>{Number(selected.evidence_strength_score||0).toFixed(3)}</b></div><div className="score-badge pri"><span>Priority</span><b>{Number(selected.business_priority||0).toFixed(1)}</b></div></div>
            </div>
            <div className="grid-3" style={{marginTop:12}}>
              {(()=>{ const sc=safeParse(selected.score_components_json)||{}; return <><ScoreBar label="Evidence strength" value={selected.evidence_strength_score}/><ScoreBar label="Backlog alignment (similarity)" value={selected.semantic_max_sim}/><ScoreBar label="Graph / lens" value={sc.graph}/></>; })()}
            </div>
          </div>

          <div className="grid-2">
            <div className="card"><h3>Hypothesis & Coverage</h3>
              <p><b>Hypothesis (proposal):</b> {String(selected.hypothesis||'—')}</p>
              <p><b>Acceptance criteria:</b></p>
              <ul className="muted">{asArray(selected.acceptance_criteria_json).map((a:string,i:number)=><li key={i}>{String(a)}</li>)}</ul>
              <p><b>Coverage uncertainty:</b> {String(selected.coverage_uncertainty||'—')}</p>
              <div><b>Score components:</b><pre>{JSON.stringify(safeParse(selected.score_components_json)||{}, null, 2)}</pre></div>
            </div>
            <div className="card"><h3>Backlog Validation (signal, not proof)</h3>
              {(()=>{ const v = evidence?.validation || selected.validation || {}; return <>
                <div className="row" style={{marginBottom:8}}>
                  <Tag tone={v.relationship_type==='NO_MATCH'||v.relationship_type==='UNCOVERED_GAP'?'warn':v.relationship_type==='STRONG_MATCH'?'good':'neutral'}>{String(v.relationship_type||'n/a')}</Tag>
                  <span className="muted">best ticket: {String(v.best_ticket_id||'n/a')} · max sim {v.max_similarity ?? v.alignment_score ?? '—'}</span>
                </div>
                <div className="muted" style={{marginBottom:8}}>{String(v.reason||'')}</div>
              </>; })()}
              <h4>Top matches</h4>
              {(evidence?.matches||[]).length ? <table><thead><tr><th>Ticket</th><th>Similarity</th><th>Relation</th><th>Status</th></tr></thead><tbody>
                {(evidence?.matches||[]).map((m:any,i:number)=><tr key={i}><td><b>{m.jira_id||m.backlog_id}</b></td><td>{Number(m.similarity||m.score||0).toFixed(3)}</td><td>{m.relationship_type}</td><td>{m.status_snapshot||m.ticket_status||m.status||'—'}</td></tr>)}
              </tbody></table> : <div className="muted">{loading==='evidence'?'Loading…':'No backlog matches (treated as uncovered signal).'}</div>}
            </div>
          </div>

          <div className="card"><h3>Supporting Feedback & Extracted Signals</h3>
            {loading==='evidence' && <div className="muted">Loading evidence…</div>}
            <div className="evidence-list">
              {(evidence?.feedback||[]).map((f:any)=>{
                const ins = Array.isArray(f.insights)?f.insights:(f.insights?[f.insights]:[]);
                return <div key={f.feedback_id || Math.random()} className="evidence-item">
                  <div className="evidence-item-head">
                    <div><b>{f.feedback_id}</b> <span className="muted">· {f.channel||'—'} · tier {f.customer_tier||'n/a'} · {f.timestamp||''}</span></div>
                    <div className="row">{f.severity_proxy!=null && <Tag tone="warn">severity {String(f.severity_proxy)}</Tag>}{f.device_os && <Tag>{f.device_os}</Tag>}</div>
                  </div>
                  <div className="quote">{String(f.raw_text || f.cleaned_text || '')}</div>
                  {ins.length ? ins.map((ix:any,idx:number)=> <div key={idx} className="signal-grid">
                    {ix.intent && <span className="chip chip-intent">intent: {String(ix.intent)}</span>}
                    {ix.symptom && <span className="chip chip-sym">symptom: {String(ix.symptom)}</span>}
                    {ix.failure_point && <span className="chip chip-fail">failure: {String(ix.failure_point)}</span>}
                    {ix.journey_node && <span className="chip chip-node">journey: {String(ix.journey_node)}</span>}
                    {ix.emotion && <span className="chip chip-emo">emotion: {String(ix.emotion)}</span>}
                    {ix.workaround && <span className="chip chip-work">workaround: {String(ix.workaround)}</span>}
                  </div>) : <div className="muted">No extracted insight row.</div>}
                </div>;
              })}
              {!(evidence?.feedback||[]).length && !loading && <div className="muted">No feedback linked.</div>}
            </div>
          </div>

          <div className="card"><h3>Candidate Lineage (5-lane trace)</h3>
            {candLineage && candLineage.nodes ? <LineageGraph data={candLineage}/> : <div className="muted">{loading==='evidence'?'Loading lineage…':'No lineage for candidate.'}</div>}
          </div>
        </div>}
      </div>}
      </Boundary>
    </main>
  </div>;
}
