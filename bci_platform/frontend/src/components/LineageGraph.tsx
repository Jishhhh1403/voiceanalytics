import React, { useMemo, useState } from 'react';

type Node = { id:string; type:string; label:string; lane?:number; data?:any };
type Edge = { source:string; target:string; type?:string; dashed?:boolean };

const LANES = [
  { id:1, title:'1. Customer Feedback', sub:'verbatim evidence' },
  { id:2, title:'2. Extracted Signals', sub:'intent/symptom/emotion' },
  { id:3, title:'3. Problem/Engines', sub:'clusters & detections' },
  { id:4, title:'4. Unified Candidate', sub:'merged opportunity' },
  { id:5, title:'5. Backlog Audit', sub:'alignment (≠ resolution)' },
];
const COLORS: Record<string,string> = {
  feedback:'#38bdf8', insight:'#a78bfa', canonical_problem:'#34d399', unified_candidate:'#f59e0b', backlog_audit:'#f87171', lens_detection:'#22c55e'
};
const ICON: Record<string,string> = { feedback:'💬', insight:'🔎', canonical_problem:'🧩', unified_candidate:'🎯', backlog_audit:'📋', lens_detection:'⚙️' };

export default function LineageGraph({ data }:{ data:any }){
  const nodes: Node[] = data?.nodes || [];
  const edges: Edge[] = data?.edges || [];
  const [focus, setFocus] = useState<string|null>(null);
  const [query, setQuery] = useState('');

  const nodeMap = useMemo(()=>{ const m:Record<string,Node>={}; nodes.forEach(n=>m[n.id]=n); return m; },[nodes]);

  const layout = useMemo(()=>{
    const byLane: Record<number, Node[]> = {1:[],2:[],3:[],4:[],5:[]};
    nodes.forEach(n=>{ const l = n.lane || (n.type==='feedback'?1:n.type==='insight'?2:n.type==='unified_candidate'?4:n.type==='backlog_audit'?5:3); (byLane[l]||(byLane[l]=[])).push(n); });
    // limit per lane for readability
    Object.keys(byLane).forEach(k=>{ const L=Number(k); if(byLane[L].length>18){ byLane[L]=byLane[L].slice(0,18).concat([{id:`more-${L}`, type:'more', label:`+${nodes.filter(n=>(n.lane||3)===L).length-18} more`, lane:L} as any]); }});
    const W=1400, laneW=W/5, padTop=70, rowH=74;
    const pos: Record<string,{x:number,y:number,w:number,h:number,n:Node}> = {};
    for(let l=1;l<=5;l++){
      const arr=byLane[l]||[]; const x=laneW*(l-1)+18; const w=laneW-36;
      arr.forEach((n,i)=>{ pos[n.id]={x, y: padTop + i*rowH, w, h:54, n}; });
    }
    const height = padTop + Math.max(...Object.values(byLane).map(a=>a.length),1)*rowH + 40;
    return { pos, width: W, height, laneW };
  },[nodes]);

  const connected = useMemo(()=>{
    if(!focus) return null;
    const s=new Set<string>([focus]);
    edges.forEach(e=>{ if(e.source===focus||e.target===focus){ s.add(e.source); s.add(e.target);} });
    // one more hop
    edges.forEach(e=>{ if(s.has(e.source)) s.add(e.target); if(s.has(e.target)) s.add(e.source); });
    return s;
  },[focus,edges]);

  const filteredNodes = nodes.filter(n=> !query || (n.label||'').toLowerCase().includes(query.toLowerCase()) || n.id.toLowerCase().includes(query.toLowerCase()));

  const pathFor = (e:Edge)=>{
    const a=layout.pos[e.source], b=layout.pos[e.target]; if(!a||!b) return null;
    const x1=a.x+a.w, y1=a.y+a.h/2, x2=b.x, y2=b.y+b.h/2;
    const mx=(x1+x2)/2;
    return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
  };

  return <div>
    <div className="viz-toolbar">
      <div className="row" style={{alignItems:'center'}}>
        <input placeholder="Search nodes…" value={query} onChange={e=>setQuery(e.target.value)} style={{minWidth:260}}/>
        <button className="btn secondary" onClick={()=>setFocus(null)}>Clear focus</button>
        <span className="muted">{nodes.length} nodes · {edges.length} edges (click a node to highlight its flow)</span>
      </div>
    </div>
    {query && <div className="card"><b>Matches:</b> {filteredNodes.slice(0,20).map(n=> <span key={n.id} className="pill" style={{cursor:'pointer'}} onClick={()=>{setFocus(n.id); setQuery('');}}>{n.label||n.id}</span>)}</div>}
    <div className="viz-canvas" style={{overflow:'auto'}}>
      <svg width={layout.width} height={layout.height} style={{minWidth:'100%', background:'linear-gradient(180deg,#0b1020 0%, #0e1530 100%)'}}>
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,4 L0,8 z" fill="#5b6b93"/></marker>
          <marker id="arrowHi" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,4 L0,8 z" fill="#93c5fd"/></marker>
        </defs>
        {/* lane headers & bands */}
        {LANES.map(l=>{ const x=layout.laneW*(l.id-1); return <g key={l.id}>
          <rect x={x+6} y={6} width={layout.laneW-12} height={layout.height-12} rx={14} fill={l.id%2? 'rgba(255,255,255,0.015)':'rgba(255,255,255,0.03)'} />
          <text x={x+layout.laneW/2} y={30} textAnchor="middle" fill="#e7eaf3" fontWeight={700} fontSize={14}>{l.title}</text>
          <text x={x+layout.laneW/2} y={48} textAnchor="middle" fill="#9aa4bf" fontSize={11}>{l.sub}</text>
        </g>;})}
        {/* edges */}
        {edges.map((e,i)=>{ const d=pathFor(e); if(!d) return null; const hi = connected && (connected.has(e.source)&&connected.has(e.target)); const dim = connected && !hi; return <path key={i} d={d} fill="none" stroke={hi?'#93c5fd':'#3b4d78'} strokeWidth={hi?2.2:1.2} opacity={dim?0.08: (hi?0.95:0.45)} strokeDasharray={e.dashed?'6 4':undefined} markerEnd={hi?'url(#arrowHi)':'url(#arrow)'} />; })}
        {/* nodes */}
        {Object.values(layout.pos).map(({x,y,w,h,n})=>{
          const col = COLORS[n.type] || '#64748b'; const hi = focus===n.id; const dim = connected && !connected.has(n.id);
          return <g key={n.id} transform={`translate(${x},${y})`} onClick={()=>setFocus(n.id)} style={{cursor:'pointer', opacity: dim?0.18:1}}>
            <rect width={w} height={h} rx={12} fill="#121a36" stroke={hi?'#fff':col} strokeWidth={hi?2:1.2} />
            <rect x={0} y={0} width={6} height={h} rx={12} fill={col} />
            <text x={16} y={22} fontSize={16}>{ICON[n.type]||'•'}</text>
            <text x={38} y={22} fill="#e7eaf3" fontSize={12} fontWeight={600}>{(n.label||n.id).slice(0,22)}{(n.label||n.id).length>22?'…':''}</text>
            <text x={38} y={40} fill="#9aa4bf" fontSize={10}>{n.type.replace('_',' ')}{n.data?.score!=null?` · ${Number(n.data.score).toFixed(2)}`:''}{n.data?.relationship?` · ${n.data.relationship}`:''}</text>
          </g>;
        })}
      </svg>
    </div>
    <div className="muted" style={{marginTop:8}}>Solid edges = supported derivations; dashed = weak/rejected audit link. Lineage is evidence-traceable, not causal proof.</div>
  </div>;
}
