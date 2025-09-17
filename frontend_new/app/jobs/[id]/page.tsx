"use client";
import React, { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { getApiBase } from '../../lib/apiBase';
import { getAuthHeaders } from '../../lib/auth';

interface RecruiterContact { name?:string; title?:string; email?:string; linkedin_url?:string }
interface JobDetail { id:number; title:string; company?:string; location?:string; url?:string; cover_letter?:string|null; resume_custom?:string|null; recruiter_contacts?:RecruiterContact[]; resume_txt_url?:string|null; resume_docx_url?:string|null; resume_match?: number|null }

const API_BASE = getApiBase();

export default function JobDetailPage(){
  const params = useSearchParams();
  const jobId = Number(params.get('id')) || Number(globalThis.location.pathname.split('/').pop());
  const runId = params.get('runId');
  const [data, setData] = useState<JobDetail|null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);

  const headers = useMemo(()=> (getAuthHeaders() as Record<string,string>), []);

  useEffect(()=>{
    let cancelled=false;
    async function load(){
  if(!runId || !jobId){ setError('Missing runId or job id in URL. Open this page via the dashboard Details button.'); setLoading(false); return; }
      try {
        const r = await fetch(`${API_BASE}/runs/${runId}/jobs/${jobId}/details`, { headers });
        if(!r.ok){ throw new Error(`Status ${r.status}`); }
        const d = await r.json();
        if(!cancelled){ setData(d); }
      } catch(e:any){ if(!cancelled) setError(e.message||'Failed to load'); }
      finally { if(!cancelled) setLoading(false); }
    }
    load();
    return ()=>{ cancelled=true; };
  }, [runId, jobId, headers]);

  function copy(txt?:string|null){ if(!txt) return; try { navigator.clipboard.writeText(txt); } catch {} }

  const initials = (name?:string)=> (name||'')
    .split(/\s+/).filter(Boolean).slice(0,2).map(p=>p[0]?.toUpperCase()).join('');

  return (
    <main className="page" style={{maxWidth:1100, margin:'0 auto', display:'flex', flexDirection:'column', gap:32}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', gap:24}}>
        <div style={{display:'flex', flexDirection:'column', gap:6}}>
          <h1 style={{fontSize:'1.15rem', margin:0, letterSpacing:'.5px'}}>{data?.title || 'Job Detail'}</h1>
          {data && <div style={{fontSize:'.7rem', color:'var(--color-text-soft)'}}>{data.company || '—'} • {data.location || 'N/A'}</div>}
          {data?.url && <a href={data.url} target="_blank" rel="noreferrer" className="badge-link" style={{width:'fit-content'}}>Original Posting</a>}
          <div style={{fontSize:'.55rem', color:'var(--color-text-soft)'}}>Run: {runId} • Job ID: {jobId} {typeof data?.resume_match === 'number' && (
            <span
              style={data.resume_match>=70? {marginLeft:8, padding:'2px 6px', background:'#14532d', borderRadius:4} : data.resume_match>=40? {marginLeft:8, padding:'2px 6px', background:'#1e3a8a', borderRadius:4} : {marginLeft:8, padding:'2px 6px', background:'#fff', color:'#6b4a2f', border:'1px solid #e5d9cf', borderRadius:4, fontWeight:600}}
            >{data.resume_match}% match</span>
          )}</div>
        </div>
        <div style={{display:'flex', gap:8}}>
          <button className="btn outline" onClick={()=> window.print()} style={{fontSize:'.6rem'}}>Print</button>
          <button className="btn outline" onClick={()=> copy(data?.cover_letter)} style={{fontSize:'.6rem'}} disabled={!data?.cover_letter}>Copy Cover</button>
          <button className="btn outline" onClick={()=> copy(data?.resume_custom)} style={{fontSize:'.6rem'}} disabled={!data?.resume_custom}>Copy Resume</button>
          <button className="btn" style={{fontSize:'.6rem'}} onClick={()=> window.close()}>Close</button>
        </div>
      </div>
      {loading && (
        <div style={{display:'flex', flexDirection:'column', gap:16}}>
          <div className="skeleton" style={{height:24, width:320}} />
          <div className="skeleton" style={{height:140, width:'100%'}} />
        </div>
      )}
      {error && !loading && <div className="error-text">{error}</div>}
      {!runId && !loading && (
        <div className="card" style={{padding:24}}>
          <div style={{fontSize:'.7rem', marginBottom:8}}>Run ID missing.</div>
          <div style={{fontSize:'.6rem', color:'var(--color-text-soft)'}}>Return to the dashboard and click the Details button for a specific job to open full view.</div>
        </div>
      )}
      {data && !loading && !error && (
        <div style={{display:'flex', flexDirection:'column', gap:32}}>
          <section style={{display:'flex', flexDirection:'column', gap:16}}>
            <h2 style={{fontSize:'.75rem', letterSpacing:'.1em', textTransform:'uppercase', margin:0, color:'var(--color-text-soft)'}}>Recruiter Contacts</h2>
            <div className="contact-grid">
              {(data.recruiter_contacts && data.recruiter_contacts.length>0) ? data.recruiter_contacts.map((c,i)=> (
                <div key={i} className="contact-card">
                  <div className="contact-head">
                    <div style={{display:'flex', alignItems:'center', gap:8}}>
                      <div className="contact-avatar">{initials(c.name)||'RC'}</div>
                      <div style={{display:'flex', flexDirection:'column', gap:2}}>
                        <span style={{fontSize:'.55rem', fontWeight:600}}>{c.name || '—'}</span>
                        {c.title && <span className="contact-title">{c.title}</span>}
                      </div>
                    </div>
                    {c.linkedin_url && <a href={c.linkedin_url} target="_blank" rel="noreferrer" className="chip-btn" style={{fontSize:'.45rem'}}>LI</a>}
                  </div>
                  {c.email && <div className="contact-email"><a style={{color:'var(--color-accent)', textDecoration:'none'}} href={`mailto:${c.email}`}>{c.email}</a>
                    <button className="chip-btn" onClick={()=> copy(c.email)}>Copy</button></div>}
                </div>
              )) : <div className="muted" style={{fontSize:'.55rem'}}>No contacts.</div>}
            </div>
          </section>
          <section style={{display:'grid', gap:24, gridTemplateColumns:'repeat(auto-fit,minmax(320px,1fr))'}}>
            <div className="doc-panel">
              <h4>Cover Letter</h4>
              <div className="doc-snippet" style={{fontSize:'.58rem'}} onDoubleClick={()=> copy(data.cover_letter)}>{data.cover_letter || '—'}</div>
            </div>
            <div className="doc-panel">
              <h4>Tailored Resume</h4>
              <div className="doc-snippet" style={{fontSize:'.58rem'}} onDoubleClick={()=> copy(data.resume_custom)}>{data.resume_custom || '—'}</div>
            </div>
          </section>
          <section style={{display:'flex', flexDirection:'column', gap:10}}>
            <h2 style={{fontSize:'.75rem', letterSpacing:'.1em', textTransform:'uppercase', margin:0, color:'var(--color-text-soft)'}}>Downloads</h2>
            <div className="inline-badges">
              {data.resume_txt_url && <a className="dw-link" href={data.resume_txt_url} target="_blank" rel="noreferrer">Resume TXT</a>}
              {data.resume_docx_url && <a className="dw-link" href={data.resume_docx_url} target="_blank" rel="noreferrer">Resume DOCX</a>}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
