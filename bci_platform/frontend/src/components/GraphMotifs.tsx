import React, { useMemo, useState } from 'react';

function MiniNetwork({ edges, nodes }:{edges:any[]; nodes?:string[]}){
  // simple circular layout
  const ns = nodes || Array.from(new Set(edges.flatMap(e=>[e.source,e.target,e.from,e.to,e.node].filter(Boolean))));
  const show = ns.slice(0,18);
  const R=90, cx=140, cy=110;
  const pos:Record<string,{x:number,y:number}> = {};
  show.forEach((n,i)=>{ const a=(Math.PI*2*i)/show.length - Math.PI/2; pos[n]={x:cx+R*Math.cos(a), y:cy+R*Math.sin(a)}; });
  const col=(n:string)=> n.startsWith('intent')?'#a78bfa': n.startsWith('symp')?'#f87171': n.startsWith('work')?'#f59e0b': n.startsWith('node')?'#34d399':'#38bdf8';
  return <svg width="100%" height="240" viewBox="0 0 280 220">
    {edges.slice(0,40).map((e,i)=>{ const s=e.source||e.from||e.intent; const t=e.target||e.to||e.symptom||e.workaround; const a=pos[s], b=pos[t]; if(!a||!b) return null; return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#3b4d78" strokeWidth={1.2} opacity={0.6}/>; })}
    {show.map(n=>{ const p=pos[n]; if(!p) return null; return <g key={n}><circle cx={p.x} cy={p.y} r={10} fill={col(n)} opacity={0.9}/><text x={p.x} y={p.y-14} textAnchor="middle" fontSize={9} fill="#cbd5e1">{String(n).replace(/^(intent:|symp:|work:|node:)/,'').slice(0,10)}</text></g>; })}
  </svg>;
}

function MotifCard({title, color, items, render}:{title:string;color:string;items:any[];render:(m:any)=>React.ReactNode}){
  const [open,setOpen]=useState(true);
  return <div className="card" style={{borderTop:`3px solid ${color}`}}>
    <div className="row" style={{justifyContent:'space-between',alignItems:'center'}}><h3>{title} <span className="pill">{items.length}</span></h3><button className="btn secondary" onClick={()=>setOpen(o=>!o)}>{open?'Hide':'Show'}</button></div>
    {open && (items.length? <div className="grid">{items.slice(0,12).map((m,i)=><div key={i} className="card" style={{background:'#0b1020'}}>{render(m)}</div>)}</div> : <div className="muted">No motifs detected for this lens in this run (can be normal depending on evidence/thresholds).</div>)}
  </div>;
}

export default function GraphMotifs({ data }:{data:any}){
  const m1 = data?.motif1 || [];
  const m2 = data?.motif2 || [];
  const m3 = data?.motif3 || [];
  const summary = data?.graph_summary || {};
  const edges = summary.sample_edges || [];
  const [tab,setTab]=useState<'motifs'|'network'>('motifs');

  const netNodes = useMemo(()=> Array.from(new Set(edges.flatMap((e:any)=>[e.source,e.target]))),[edges]);

  return <div>
    <div className="viz-toolbar row">
      <button className={`btn ${tab==='motifs'?'':'secondary'}`} onClick={()=>setTab('motifs')}>Motif Panels</button>
      <button className={`btn ${tab==='network'?'':'secondary'}`} onClick={()=>setTab('network')}>Evidence Network</button>
      <span className="muted">Counts — escape: {data?.counts?.m1||0}, temporal: {data?.counts?.m2||0}, bridge: {data?.counts?.m3||0} · graph nodes {summary.node_count||'?'} / edges {summary.edge_count||'?'}</span>
    </div>
    {tab==='network' && <div className="split">
      <div className="card"><h3>Sample evidence network</h3>
        <svg width="100%" height="520" viewBox="0 0 800 520" style={{background:'radial-gradient(ellipse at 50% 30%, #121a36 0%, #0b1020 70%)', borderRadius:10}}>
          {(()=>{
            const show=netNodes.slice(0,40); const pos:Record<string,{x:number,y:number}>={}; const cx=400,cy=260,R=210;
            show.forEach((n:string,i:number)=>{const a=(Math.PI*2*i)/show.length - Math.PI/2; pos[n]={x:cx+R*Math.cos(a), y:cy+R*Math.sin(a)*0.75};});
            const col=(n:string)=> n.startsWith('intent')?'#a78bfa': n.startsWith('symp')?'#f87171': n.startsWith('work:')?'#f59e0b': n.startsWith('node:')?'#34d399': n.startsWith('backlog:')?'#60a5fa':'#94a3b8';
            return <>
              {edges.slice(0,120).map((e:any,i:number)=>{ const a=pos[e.source], b=pos[e.target]; if(!a||!b) return null; const hi=e.type==='FOLLOWED_BY'; return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={hi?'#f59e0b':'#334155'} strokeWidth={hi?1.8:1} opacity={0.55}/>; })}
              {show.map((n:string)=>{ const p=pos[n]; if(!p) return null; return <g key={n}><circle cx={p.x} cy={p.y} r={11} fill={col(n)} opacity={0.9} stroke="#0b1020" strokeWidth={2}/><text x={p.x} y={p.y-15} textAnchor="middle" fontSize={10} fill="#e2e8f0">{String(n).split(':').pop()?.slice(0,12)}</text></g>; })}
            </>;
          })()}
        </svg>
        <div className="muted">Sampled edges from evidence graph (CO_OCCURS/ESCAPES_TO/FOLLOWED_BY/ADDRESSED_BY). Associations, not causation.</div>
      </div>
      <div className="card"><h3>Legend & sample edges</h3>
        <div style={{marginBottom:8}}>
          <div><span className="dot" style={{background:'#a78bfa'}}/> intent</div><div><span className="dot" style={{background:'#f87171'}}/> symptom</div><div><span className="dot" style={{background:'#f59e0b'}}/> workaround / FOLLOWED_BY</div><div><span className="dot" style={{background:'#34d399'}}/> journey node</div><div><span className="dot" style={{background:'#60a5fa'}}/> backlog</div>
        </div>
        <pre>{JSON.stringify(edges.slice(0,15), null, 2)}</pre>
      </div>
    </div>}
    {tab==='motifs' && <div>
      <MotifCard title="Motif 1 — Workaround Escapes" color="#f59e0b" items={m1} render={(m)=> <>
        <div style={{fontWeight:600}}>{m.intent} → {m.symptom} → {m.workaround}</div>
        <div className="muted">count {m.count} · mean effort {m.mean_effort} · score {Number(m.score||0).toFixed(2)}</div>
        <div className="muted">supporting feedback: {(m.supporting_feedback_ids||[]).slice(0,5).join(', ')}</div>
      </>} />
      <MotifCard title="Motif 2 — Temporal Friction Chains" color="#f87171" items={m2} render={(m)=> <>
        <div style={{fontWeight:600}}>{m.from} ⇒ {m.to}</div>
        <div className="muted">count {m.count} · lift {m.lift} · score {Number(m.score||0).toFixed(2)}</div>
        <div className="muted">evidence: {(m.evidence||[]).length} transitions (association, not causation)</div>
      </>} />
      <MotifCard title="Motif 3 — Structural Bridge Nodes" color="#34d399" items={m3} render={(m)=> <>
        <div style={{fontWeight:600}}>{m.node}</div>
        <div className="muted">betweenness {m.betweenness} · score {Number(m.score||0).toFixed(2)}</div>
        <div className="muted">High-centrality journey/aspect with weak addressed coverage (structural signal, not root cause).</div>
      </>} />
    </div>}
  </div>;
}
