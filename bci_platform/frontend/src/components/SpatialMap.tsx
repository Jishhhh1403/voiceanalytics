import React, { useMemo, useRef, useState } from 'react';

type Props = { data: any };

function scaleLinear(domain: [number, number], range: [number, number]) {
  const [d0, d1] = domain; const [r0, r1] = range; const span = (d1 - d0) || 1;
  return (v: number) => r0 + ((v - d0) / span) * (r1 - r0);
}

function lerp(a:number,b:number,t:number){return a+(b-a)*t;}
function heatColor(t:number){
  // 0..1 blue->teal->yellow->red
  const x = Math.max(0, Math.min(1, t));
  if (x < 0.33){ const k=x/0.33; return `rgb(${Math.round(lerp(30,20,k))},${Math.round(lerp(60,160,k))},${Math.round(lerp(120,180,k))})`; }
  if (x < 0.66){ const k=(x-0.33)/0.33; return `rgb(${Math.round(lerp(20,240,k))},${Math.round(lerp(160,210,k))},${Math.round(lerp(180,60,k))})`; }
  const k=(x-0.66)/0.34; return `rgb(${Math.round(lerp(240,220,k))},${Math.round(lerp(210,70,k))},${Math.round(lerp(60,40,k))})`;
}

export default function SpatialMap({ data }: Props){
  const problems = data?.problems || [];
  const gridX: number[] = data?.grid_x || [];
  const gridY: number[] = data?.grid_y || [];
  const residual: number[][] = data?.residual_sampled || data?.pain_n_sampled || [];
  const wrapRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const [drag, setDrag] = useState<{sx:number,sy:number,ox:number,oy:number}|null>(null);
  const [hover, setHover] = useState<any>(null);
  const [showHeat, setShowHeat] = useState(true);

  const bounds = useMemo(()=>{
    const xs = problems.map((p:any)=>Number(p.mds_x)).filter(Number.isFinite);
    const ys = problems.map((p:any)=>Number(p.mds_y)).filter(Number.isFinite);
    let minX = Math.min(...xs, gridX[0] ?? -1), maxX = Math.max(...xs, gridX[gridX.length-1] ?? 1);
    let minY = Math.min(...ys, gridY[0] ?? -1), maxY = Math.max(...ys, gridY[gridY.length-1] ?? 1);
    if (!isFinite(minX)) { minX=-1; maxX=1; minY=-1; maxY=1; }
    const padX=(maxX-minX||1)*0.15, padY=(maxY-minY||1)*0.15;
    return { minX:minX-padX, maxX:maxX+padX, minY:minY-padY, maxY:maxY+padY };
  }, [problems, gridX, gridY]);

  const W=980, H=620, pad=40;
  const sx = useMemo(()=>scaleLinear([bounds.minX,bounds.maxX],[pad,W-pad]),[bounds]);
  const sy = useMemo(()=>scaleLinear([bounds.maxY,bounds.minY],[pad,H-pad]),[bounds]);

  const heatCells = useMemo(()=>{
    if (!showHeat || !residual.length || !gridX.length || !gridY.length) return [] as any[];
    // residual_sampled is downsampled (every ~10th) in artifact; map over its own index space
    const rows = residual.length, cols = residual[0]?.length || 0;
    let max=0; for(const r of residual) for(const v of r) if(v>max) max=v;
    const cells:any[]=[];
    for(let j=0;j<rows;j++){
      for(let i=0;i<cols;i++){
        const gx = gridX[Math.min(gridX.length-1, Math.floor(i*(gridX.length/cols)))];
        const gy = gridY[Math.min(gridY.length-1, Math.floor(j*(gridY.length/rows)))];
        const gx2 = gridX[Math.min(gridX.length-1, Math.floor((i+1)*(gridX.length/cols)))];
        const gy2 = gridY[Math.min(gridY.length-1, Math.floor((j+1)*(gridY.length/rows)))];
        const x = sx(gx), y = sy(gy2); const w = Math.abs(sx(gx2)-sx(gx))+1, h = Math.abs(sy(gy)-sy(gy2))+1;
        cells.push({x,y,w,h,v: residual[j][i], t: max? residual[j][i]/max:0});
      }
    }
    return cells;
  },[residual,gridX,gridY,sx,sy,showHeat]);

  const onWheel = (e: React.WheelEvent)=>{
    e.preventDefault();
    const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
    const mx = e.clientX-rect.left, my=e.clientY-rect.top;
    const scale = e.deltaY < 0 ? 1.12 : 0.9;
    setTransform(t=>{
      const k = Math.max(0.5, Math.min(20, t.k*scale));
      const wx = (mx - t.x)/t.k, wy=(my - t.y)/t.k;
      return { k, x: mx - wx*k, y: my - wy*k };
    });
  };
  const onDown = (e: React.MouseEvent)=>{ if(e.button!==0) return; setDrag({sx:e.clientX,sy:e.clientY,ox:transform.x,oy:transform.y}); };
  const onMove = (e: React.MouseEvent)=>{ if(!drag) return; setTransform(t=>({...t, x: drag.ox + (e.clientX-drag.sx), y: drag.oy + (e.clientY-drag.sy)})); };
  const onUp = ()=>setDrag(null);

  const reset = ()=>setTransform({x:0,y:0,k:1});
  const zoomBy = (f:number)=> setTransform(t=>({ ...t, k: Math.max(0.5, Math.min(20, t.k*f)) }));

  const colorFor = (p:any)=>{
    const pr = Number(p.priority_score||0);
    if (pr>=60) return '#ef4444'; if (pr>=40) return '#f59e0b'; if (pr>=25) return '#22c55e'; return '#3b82f6';
  };
  const rFor = (p:any)=> 4 + Math.min(12, Math.sqrt(Number(p.feedback_count||1))*1.8);

  return <div>
    <div className="viz-toolbar">
      <div className="row">
        <button className="btn secondary" onClick={()=>zoomBy(1.2)}>+</button>
        <button className="btn secondary" onClick={()=>zoomBy(1/1.2)}>−</button>
        <button className="btn secondary" onClick={reset}>Reset view</button>
        <label className="muted" style={{display:'flex',alignItems:'center',gap:6}}><input type="checkbox" checked={showHeat} onChange={e=>setShowHeat(e.target.checked)}/> Residual heat overlay</label>
      </div>
      <div className="muted">Scroll to zoom · drag to pan · hover points for details. Axes are relative MDS dimensions (not business axes).</div>
    </div>
    <div ref={wrapRef} className="viz-canvas" style={{height:640, position:'relative'}}>
      <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`}
        onWheel={onWheel} onMouseDown={onDown} onMouseMove={onMove} onMouseLeave={onUp} onMouseUp={onUp}
        style={{cursor: drag?'grabbing':'grab', background:'radial-gradient(ellipse at 30% 20%, #121a36 0%, #0b1020 70%)'}}>
        <defs>
          <filter id="glow"><feGaussianBlur stdDeviation="2.5" result="coloredBlur"/><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        </defs>
        <g transform={`translate(${transform.x},${transform.y}) scale(${transform.k})`}>
          {/* grid */}
          {[0,1,2,3,4].map(i=>{ const x=pad + i*(W-2*pad)/4; const y=pad + i*(H-2*pad)/4; return <g key={i}>
            <line x1={x} y1={pad} x2={x} y2={H-pad} stroke="#1d2a4a" strokeWidth={1/transform.k}/>
            <line x1={pad} y1={y} x2={W-pad} y2={y} stroke="#1d2a4a" strokeWidth={1/transform.k}/>
          </g>;})}
          <rect x={pad} y={pad} width={W-2*pad} height={H-2*pad} fill="none" stroke="#2a3a63" strokeWidth={1.2/transform.k} />
          {/* heat */}
          {heatCells.map((c,i)=> <rect key={i} x={c.x} y={c.y} width={c.w} height={c.h} fill={heatColor(c.t)} opacity={0.08 + c.t*0.35} />)}
          {/* points */}
          {problems.map((p:any,i:number)=>{
            const cx=sx(Number(p.mds_x)), cy=sy(Number(p.mds_y)); const r=rFor(p); const col=colorFor(p);
            const isH = hover?.problem_id===p.problem_id;
            return <g key={p.problem_id||i} onMouseEnter={()=>setHover(p)} onMouseLeave={()=>setHover(null)} style={{cursor:'pointer'}}>
              <circle cx={cx} cy={cy} r={r*(isH?1.35:1)} fill={col} opacity={0.85} stroke={isH?'#fff':'rgba(255,255,255,0.25)'} strokeWidth={(isH?2:1)/transform.k} filter={isH? 'url(#glow)': undefined} />
              {(isH || r>8) && <text x={cx} y={cy-r-4/transform.k} textAnchor="middle" fontSize={11/transform.k} fill="#e7eaf3" style={{pointerEvents:'none'}}>{(p.title||'').slice(0,18)}</text>}
            </g>;
          })}
        </g>
      </svg>
      {hover && <div className="viz-tooltip" style={{left:16,bottom:16}}>
        <div style={{fontWeight:600}}>{hover.title}</div>
        <div className="muted">{hover.problem_id}</div>
        <div>Journey: <b>{hover.journey_node_id||'n/a'}</b></div>
        <div>Priority: <b>{Number(hover.priority_score||0).toFixed(1)}</b> · Feedback: <b>{hover.feedback_count||0}</b></div>
        <div className="muted">MDS ({Number(hover.mds_x).toFixed(3)}, {Number(hover.mds_y).toFixed(3)})</div>
      </div>}
      <div className="viz-legend">
        <div style={{fontWeight:600, marginBottom:4}}>Priority</div>
        <div><span className="dot" style={{background:'#ef4444'}}/> ≥60 high</div>
        <div><span className="dot" style={{background:'#f59e0b'}}/> 40–59</div>
        <div><span className="dot" style={{background:'#22c55e'}}/> 25–39</div>
        <div><span className="dot" style={{background:'#3b82f6'}}/> &lt;25</div>
        <div className="muted" style={{marginTop:6}}>Size = feedback count<br/>Heat = residual pain</div>
      </div>
    </div>
  </div>;
}
