"use client";
import React, { useState, useEffect } from 'react';

interface RunStatus { status: string; stage: string; counts: any; errors: string[]; }
interface Job { id:number; title:string; company?:string; location?:string; url?:string }

const API_BASE = (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_BASE_URL) || '/api';

export default function SearchPage(){
  const [query,setQuery]=useState("");
  const [runId,setRunId]=useState<string|null>(null);
  const [status,setStatus]=useState<RunStatus|null>(null);
  const [jobs,setJobs]=useState<Job[]>([]);
  const [loading,setLoading]=useState(false);
  const [auto,setAuto]=useState(true);

  const start = async()=>{
    if(!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/jobs/run`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query, sources:['indeed']})});
      if(!res.ok){ console.error('run start failed', res.status); return; }
      const data = await res.json();
      const id = data.task_id; setRunId(id); setStatus(null); setJobs([]);
      // immediate fetch since run is synchronous
      setTimeout(async()=>{
        try {
          const st = await fetch(`${API_BASE}/runs/${id}`); if(st.ok) setStatus(await st.json());
          const jr = await fetch(`${API_BASE}/runs/${id}/jobs`); if(jr.ok) setJobs(await jr.json());
        } catch(e){ console.error('immediate fetch error', e); }
      }, 300);
    } catch(e){ console.error('start error', e); }
    finally { setLoading(false); }
  };

  useEffect(()=>{
    if(!runId) return;
    const t=setInterval(async()=>{
      const sr= await fetch(`${API_BASE}/runs/${runId}`);
      if(sr.ok){
        const st= await sr.json();
        setStatus(st);
        const jr= await fetch(`${API_BASE}/runs/${runId}/jobs`);
        if(jr.ok) setJobs(await jr.json());
        if(['done','error'].includes(st.stage)) clearInterval(t);
      }
    }, 2000);
    return ()=>clearInterval(t);
  },[runId]);

  return (
    <div className="grid" style={{gap:'32px', maxWidth:980}}>
      <div className="card">
        <div className="section-title">Keyword Job Search</div>
        <div className="input-row">
          <div className="field" style={{flex:1}}>
            <label>Keyword / Query</label>
            <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="e.g. python developer" className="input" />
          </div>
          <button onClick={start} disabled={loading || !query.trim()} className="btn" style={{marginTop:4}}>{loading? 'Running…' : 'Run'}</button>
          {runId && <div className="muted" style={{fontSize:'.7rem'}}>Run #{runId}</div>}
        </div>
      </div>
      <div className="card">
        <div className="section-title">Status</div>
        {status ? (
          <div className="stat-bar">
            <div className="stat"><span className="stat-label">Status</span><span className="stat-value">{status.status}</span></div>
            <div className="stat"><span className="stat-label">Stage</span><span className="stat-value" style={{textTransform:'capitalize'}}>{status.stage}</span></div>
            <div className="stat"><span className="stat-label">Jobs</span><span className="stat-value">{status.counts?.jobs ?? 0}</span></div>
          </div>
        ) : <div className="empty">No run yet.</div>}
        {status?.errors?.length>0 && <div className="error-text">{status.errors.join(', ')}</div>}
      </div>
      <div className="card">
        <div className="section-title">Jobs <span style={{fontWeight:400}}>({jobs.length})</span></div>
        <div className="jobs-list" style={{maxHeight:500}}>
          <div className="jobs-scroll">
            {jobs.length===0 && <div className="empty">No jobs yet.</div>}
            {jobs.map(j => (
              <div key={j.id} className="job-row">
                <div className="job-top">
                  <span style={{fontWeight:600}}>{j.title}</span>
                  {j.url && <a href={j.url} target="_blank" className="badge-link">Open</a>}
                </div>
                <div className="muted">{j.company || '—'} · {j.location || 'N/A'}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
