"use client";
import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { getApiBase } from '../../lib/apiBase';
import { getAuthHeaders } from '../lib/auth';

interface RunStatus { status: string; stage: string; counts: { jobs?: number; enriched?: number; emails?: number; generated?: number }; errors: string[]; }

interface JobItem { id: number; title: string; company?: string; url?: string; location?: string; recruiter_name?:string|null; recruiter_email?:string|null; cover_letter?:string|null; resume_custom?:string|null; resume_txt_url?:string|null; resume_docx_url?:string|null; recruiter_contacts?: Array<{name?:string; title?:string; email?:string; linkedin_url?:string}>; resume_match?: number|null }
interface RunSummary { id: number; query: string; status: string; stage: string; jobs: number; }
interface EmailEvent { job_id?: number; email?: string; subject?: string; dry_run?: boolean }
interface TrackedMessage { id: string; to_email: string; subject: string; created_at: string; events: number; provider_msgid?: string|null }

const API_BASE = getApiBase();

const STAGE_ORDER = ['discover','parse','enrich','generate','email','done'];
function stageProgress(stage?: string){
  if(!stage) return 0;
  const idx = STAGE_ORDER.indexOf(stage.toLowerCase());
  if(idx === -1) return 0;
  const base = (idx)/(STAGE_ORDER.length-1);
  return Math.min(1, Math.max(0, base));
}

// Fine-grained progress leveraging counts for intra-stage completion
function detailedProgress(status?: RunStatus){
  if(!status) return 0;
  const stage = status.stage?.toLowerCase();
  const idx = STAGE_ORDER.indexOf(stage);
  if(idx < 0) return 0;
  const totalSegments = STAGE_ORDER.length - 1; // transitions between stages
  const base = idx / totalSegments; // fully completed stages
  const counts = status.counts || {};
  const span = 1 / totalSegments; // width of one stage segment
  let intra = 0;
  try {
    // For early stages we may have no enriched/generated/email counts yet.
    // Provide an estimation so UI does not stay at 0% for long periods.
    if(stage==='discover'){
      // If jobs count is appearing, scale within first segment (discover->parse)
      const j = (counts.jobs || 0);
      // Assume typical batch target of 40 jobs; clamp 0..1
      const est = Math.min(1, j / 40);
      intra = est * span; // occupy portion of first segment
    } else if(stage==='parse'){
      // Parsing after discovery: treat parse progress as half the segment if no downstream counts yet
      const j = (counts.jobs || 0);
      const est = j ? 0.5 : 0.1; // minimal movement if nothing yet
      intra = est * span;
    }
    if(stage==='enrich' && counts.jobs){ intra = Math.min(1, (counts.enriched || 0) / (counts.jobs || 1)) * span; }
    else if(stage==='generate' && counts.jobs){ intra = Math.min(1, (counts.generated || 0) / (counts.jobs || 1)) * span; }
    else if(stage==='email' && counts.jobs){ intra = Math.min(1, (counts.emails || 0) / (counts.jobs || 1)) * span; }
  } catch {/* ignore */}
  const total = base + intra;
  return Math.max(0, Math.min(1, total));
}

export default function DashboardPage() {
  const params = useSearchParams();
  const [query, setQuery] = useState("software engineer");
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [resumeText, setResumeText] = useState("");
  const [resumeSaved, setResumeSaved] = useState(false);
  const [fileUploading, setFileUploading] = useState(false);
  const [fileInfo, setFileInfo] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File|null>(null); // file chosen before run exists
  const [genStatus, setGenStatus] = useState<string | null>(null);
  const [sendStatus, setSendStatus] = useState<string | null>(null);
  const [regenStatus, setRegenStatus] = useState<string | null>(null);
  const [enrichStatus, setEnrichStatus] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all'|'withDocs'|'withoutDocs'>('all');
  const [quickQuery, setQuickQuery] = useState('frontend engineer');
  const [quickResults, setQuickResults] = useState<any[]|null>(null);
  const [quickLoading, setQuickLoading] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [hoveredJob, setHoveredJob] = useState<number|null>(null);
  // Selected candidate context (from recruiter tiles)
  const [activeCandidate, setActiveCandidate] = useState<{id:number; name:string} | null>(null);
  // Auto search disabled per request; keep state for potential future but default false and not exposed
  const [autoMode, setAutoMode] = useState(false);
  const [lastRunQuery, setLastRunQuery] = useState<string>('');
  const [seedEnabled, setSeedEnabled] = useState<boolean>(false);
  // Email tracking moved to /analytics page
  // Map of job_id -> cover letter DOCX download URL
  const [coverDocxMap, setCoverDocxMap] = useState<Record<number, string>>({});
  // Map of job_id -> tailored resume DOCX download URL (parity with coverDocxMap)
  const [resumeDocxMap, setResumeDocxMap] = useState<Record<number, string>>({});

  const baseHeaders = getAuthHeaders() as Record<string,string>;

  // Helper to persist a recruiter activity for the active candidate
  const postActivity = async (payload: { type: string; title?: string; job_id?: number; run_id?: number; details?: any }) => {
    try {
      if (!activeCandidate) return;
      const rid = (typeof window !== 'undefined' ? (localStorage.getItem('recruiterIdentifier') || 'default') : 'default');
      const actHeaders: Record<string,string> = { ...(baseHeaders as any), 'Content-Type':'application/json' };
      await fetch(`${API_BASE}/recruiter/${encodeURIComponent(rid)}/candidates/${activeCandidate.id}/activities`, {
        method: 'POST', headers: actHeaders,
        body: JSON.stringify({ recruiter_identifier: rid, candidate_id: activeCandidate.id, ...payload })
      });
    } catch {/* ignore */}
  };

  const refreshRuns = async () => {
    try {
  const r = await fetch(`${API_BASE}/runs`, { headers: baseHeaders });
      if (r.ok) { setRuns(await r.json()); setApiError(null); }
  else { console.warn('Runs list fetch failed', r.status); setApiError(`Runs fetch failed (${r.status})`); }
    } catch (e) { console.error('refreshRuns error', e); setApiError('Cannot reach backend API'); }
  };

  const startRun = async () => {
    setLoading(true);
    try {
  const res = await fetch(`${API_BASE}/jobs/run`, { method: 'POST', headers: { ...baseHeaders, 'Content-Type':'application/json' }, body: JSON.stringify({ query, sources: ['indeed'] }) });
  if(!res.ok){ console.error('startRun failed', res.status); setApiError(`Start failed (${res.status})`); setLoading(false); return; }
      const data = await res.json();
      const id = data.task_id;
      setRunId(id);
  setLastRunQuery(query.trim());
      // If user pre-selected a resume file before run started, upload it now
      if(pendingFile){
        try {
          setFileUploading(true);
          const form = new FormData(); form.append('file', pendingFile);
          const upHeaders: Record<string,string> = { ...baseHeaders }; delete (upHeaders as any)['Content-Type'];
          const uploadRes = await fetch(`${API_BASE}/runs/${id}/resume/upload`, { method:'POST', headers: upHeaders, body: form });
          if(uploadRes.ok){ const udata = await uploadRes.json(); setFileInfo(`${udata.stored || pendingFile.name} (${udata.length||pendingFile.size} chars)`); setResumeSaved(true); }
        } catch { /* ignore */ }
        finally { setFileUploading(false); setPendingFile(null); }
      }
      // Auto-fetch candidate resume if no resume text/file present yet
      if(!pendingFile && !resumeText.trim() && !fileInfo && activeCandidate){
        try {
          const rid = (typeof window !== 'undefined' ? (localStorage.getItem('recruiterIdentifier') || 'default') : 'default');
          const docsRes = await fetch(`${API_BASE}/recruiter/${encodeURIComponent(rid)}/candidates/${activeCandidate.id}/documents` , { headers: baseHeaders });
          if(docsRes.ok){
            const docs = await docsRes.json();
            // Prefer document_type === 'resume', else filename hints
            const resumeDoc = (docs||[]).find((d:any)=> d.document_type==='resume') || (docs||[]).find((d:any)=> /resume/i.test(d.filename||''));
            if(resumeDoc && resumeDoc.download_url){
              // Fetch file content (text if possible) and upload to run
              const raw = await fetch(resumeDoc.download_url);
              if(raw.ok){
                const blob = await raw.blob();
                const form = new FormData(); form.append('file', new File([blob], resumeDoc.filename || 'resume_uploaded', { type: blob.type||'application/octet-stream' }));
                const upHeaders: Record<string,string> = { ...baseHeaders }; delete (upHeaders as any)['Content-Type'];
                const uploadRes2 = await fetch(`${API_BASE}/runs/${id}/resume/upload`, { method:'POST', headers: upHeaders, body: form });
                if(uploadRes2.ok){
                  const udata2 = await uploadRes2.json(); setFileInfo(`${udata2.stored || resumeDoc.filename}`); setResumeSaved(true);
                }
              }
            }
          }
        } catch {/* silent */}
      }
      // Record candidate activity if selected
      try {
        if (activeCandidate) {
          const rid = (typeof window !== 'undefined' ? (localStorage.getItem('recruiterIdentifier') || 'default') : 'default');
          const actHeaders: Record<string,string> = { ...(baseHeaders as any), 'Content-Type':'application/json' };
          await fetch(`${API_BASE}/recruiter/${encodeURIComponent(rid)}/candidates/${activeCandidate.id}/activities`, {
            method: 'POST', headers: actHeaders,
            body: JSON.stringify({ recruiter_identifier: rid, candidate_id: activeCandidate.id, type: 'run_started', title: `Run started: ${query}`, run_id: Number(id) || undefined, details: { query } })
          });
        }
      } catch {/* ignore */}
      // Because pipeline is synchronous, fetch results immediately
      setTimeout(async () => {
        try {
          const st = await fetch(`${API_BASE}/runs/${id}`, { headers: baseHeaders });
            if(st.ok) { setStatus(await st.json()); setApiError(null);} else setApiError(`Status failed (${st.status})`);
          const jr = await fetch(`${API_BASE}/runs/${id}/jobs`, { headers: baseHeaders });
            if(jr.ok) setJobs(await jr.json()); else setApiError(`Jobs failed (${jr.status})`);
          // Record completion activity if selected
          try {
            if (activeCandidate) {
              const rid = (typeof window !== 'undefined' ? (localStorage.getItem('recruiterIdentifier') || 'default') : 'default');
              const actHeaders: Record<string,string> = { ...(baseHeaders as any), 'Content-Type':'application/json' };
              await fetch(`${API_BASE}/recruiter/${encodeURIComponent(rid)}/candidates/${activeCandidate.id}/activities`, {
                method: 'POST', headers: actHeaders,
                body: JSON.stringify({ recruiter_identifier: rid, candidate_id: activeCandidate.id, type: 'run_completed', title: `Run completed`, run_id: Number(id) || undefined })
              });
            }
          } catch {/* ignore */}
        } catch (e) { console.error('immediate fetch error', e); setApiError('Immediate fetch error'); }
        refreshRuns();
      }, 300);
    } catch(e){
      console.error('startRun error', e); setApiError('Start run network error');
    } finally { setLoading(false); }
  };

  useEffect(() => { refreshRuns(); const t=setInterval(refreshRuns, 8000); return ()=>clearInterval(t); }, []);

  // Load candidate context from URL/localStorage on mount, and persist
  useEffect(()=>{
    const idStr = params?.get('candidateId');
    const name = params?.get('candidateName');
    if(idStr && name){
      const id = parseInt(idStr,10);
      if(!isNaN(id)){
        setActiveCandidate({id, name});
        try { localStorage.setItem('activeCandidate', JSON.stringify({id, name})); } catch {}
      }
    } else {
      // fallback from storage
      try {
        const raw = localStorage.getItem('activeCandidate');
        if(raw){ const obj = JSON.parse(raw); if(obj && typeof obj.id==='number' && typeof obj.name==='string'){ setActiveCandidate(obj); } }
      } catch {}
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Health check on mount to set early apiError if backend down
  useEffect(()=>{
    (async()=>{
  try { const h = await fetch(`${API_BASE}/health`, { headers: baseHeaders }); if(!h.ok) setApiError('Health check failed'); } catch { setApiError('Backend unreachable'); }
    })();
  },[]);

  useEffect(() => {
    if (!runId) return;
    const interval = setInterval(async () => {
      try {
        const sres = await fetch(`${API_BASE}/runs/${runId}`, { headers: baseHeaders });
        if (sres.ok) {
          const st = await sres.json();
          setStatus(st);
          const jres = await fetch(`${API_BASE}/runs/${runId}/jobs`, { headers: baseHeaders });
          if (jres.ok) { setJobs(await jres.json()); setApiError(null);} else { console.warn('Jobs fetch failed', jres.status); setApiError(`Jobs fetch failed (${jres.status})`); }
          if (['done','error'].includes(st.stage)) clearInterval(interval);
        } else {
          console.warn('Status fetch failed', sres.status); setApiError(`Status fetch failed (${sres.status})`);
        }
      } catch (e) { console.error('poll error', e); setApiError('Polling network error'); }
    }, 2500);
    return () => clearInterval(interval);
  }, [runId]);

  // (email tracking polling removed from dashboard)

  // Debounced auto-run when typing
  useEffect(()=>{
    if(!autoMode) return; // feature off
    const q = query.trim();
    if(q.length < 3) return; // avoid tiny queries
    if(loading) return;
    if(q === lastRunQuery) return; // already ran
    const t = setTimeout(()=>{ startRun(); }, 750); // debounce
    return ()=> clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, autoMode]);

  async function runQuickSearch(){
    setQuickLoading(true); setQuickResults(null); setApiError(null);
    try {
  const r = await fetch(`${API_BASE}/search/jobs`, {method:'POST', headers: { ...baseHeaders, 'Content-Type':'application/json' }, body: JSON.stringify({query: quickQuery, limit: 8})});
      if(r.ok){ setQuickResults(await r.json()); } else { setApiError(`Quick search failed (${r.status})`); }
    } catch(e){ setApiError('Quick search network error'); }
    finally{ setQuickLoading(false); }
  }

  const filteredJobs = useMemo(()=>{
    if(filter==='withDocs') return jobs.filter(j=> j.cover_letter || j.resume_custom);
    if(filter==='withoutDocs') return jobs.filter(j=> !(j.cover_letter || j.resume_custom));
    return jobs;
  }, [jobs, filter]);
  
  const progress = stageProgress(status?.stage); // coarse
  const fineProgress = detailedProgress(status); // fine
  const jobsWithDocs = useMemo(()=> jobs.filter(j=> j.cover_letter || j.resume_custom).length, [jobs]);
  const generationRatio = jobs.length? Math.round((jobsWithDocs / jobs.length)*100):0;

  function prettyStage(s?:string){ if(!s) return '—'; return s.charAt(0).toUpperCase()+s.slice(1); }
  function copyToClipboard(txt:string){ try { navigator.clipboard.writeText(txt); } catch { /* ignore */ } }

  const showEmpty = !filteredJobs.length && !!runId;

  // Load available cover letter DOCX files for the active run and map by job_id
  useEffect(() => {
    let aborted = false;
    async function loadCoverDocs(){
      if(!runId){ setCoverDocxMap({}); return; }
      try {
  const r = await fetch(`${API_BASE}/runs/${runId}/coverletters`, { headers: baseHeaders });
        if(!r.ok) return;
        const list: Array<{job_id:number; docx_filename:string; size?:number}> = await r.json();
        if(aborted) return;
        const m: Record<number,string> = {};
        for(const it of list){
          m[it.job_id] = `${API_BASE}/runs/${runId}/coverletters/${encodeURIComponent(it.docx_filename)}`;
        }
        setCoverDocxMap(m);
      } catch {/* ignore */}
    }
    loadCoverDocs();
    // Refresh when the count of jobs with docs changes (after Generate/Upload)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return () => { aborted = true; };
  }, [runId, jobsWithDocs]);

  const [expandedJobId, setExpandedJobId] = useState<number|null>(null);
  const [jobDetailCache, setJobDetailCache] = useState<Record<number, JobItem>>({});
  const [detailLoading, setDetailLoading] = useState<number|null>(null);

  async function loadJobDetails(jobId:number){
    if(!runId) return; if(jobDetailCache[jobId]){ setExpandedJobId(jobId); return; }
    setDetailLoading(jobId);
    try {
      const r = await fetch(`${API_BASE}/runs/${runId}/jobs/${jobId}/details`, { headers: baseHeaders });
      if(r.ok){ const d = await r.json(); setJobDetailCache(prev=>({...prev, [jobId]: d})); setExpandedJobId(jobId); }
    } catch {/* ignore */} finally { setDetailLoading(null); }
  }

  return (
    <div className="grid" style={{gap:'32px'}}>
      {activeCandidate && (
        <div className="card" style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:12}}>
          <div style={{display:'flex', alignItems:'center', gap:10}}>
            <div style={{width:28, height:28, borderRadius:6, background:'#e5f0ff', color:'#1e3a8a', display:'grid', placeItems:'center', fontWeight:700}}>{activeCandidate.name.charAt(0).toUpperCase()}</div>
            <div>
              <div className="section-title" style={{margin:0}}>Working on: {activeCandidate.name}</div>
              <div className="muted" style={{fontSize:'.6rem'}}>Candidate ID #{activeCandidate.id}</div>
            </div>
          </div>
          <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
            <button className="btn outline" onClick={()=> setQuery(prev => prev || 'software engineer')}>Use Default Query</button>
            <button className="btn" onClick={()=> startRun() } disabled={loading || !query.trim() || !(resumeText.trim() || fileInfo)}>Run Search</button>
            <button className="btn outline" onClick={()=>{ setActiveCandidate(null); try{ localStorage.removeItem('activeCandidate'); } catch{} }}>Clear</button>
          </div>
        </div>
      )}
      {apiError && (
        <div className="card" style={{border:'1px solid #b33', background:'#2a0000'}}>
          <div className="section-title" style={{color:'#ffb3b3'}}>Backend Error</div>
          <div style={{fontSize:'.7rem', color:'#ffdddd', lineHeight:1.4}}>{apiError}</div>
          <div style={{marginTop:6}}>
            <button className="btn" style={{background:'#661f1f'}} onClick={()=>{ setApiError(null); refreshRuns(); }}>Retry</button>
          </div>
        </div>
      )}
      <div className="grid" style={{gap:24, gridTemplateColumns:'repeat(auto-fit,minmax(320px,1fr))'}}>
        <div className="card" style={{position:'relative', overflow:'hidden'}}>
          <div style={{display:'flex', flexDirection:'column', gap:12}}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
              <div>
                <div className="section-title" style={{marginBottom:6}}>Search & Run</div>
                <div className="muted" style={{fontSize:'.65rem'}}>Live scrape + enrich + generate</div>
              </div>
              {runId && <span className="badge-link" style={{background:'var(--color-accent)', color:'#fff'}}># {runId}</span>}
            </div>
            <input
              value={query}
              onChange={e=>setQuery(e.target.value)}
              onKeyDown={e=>{
                if(e.key==='Enter' && !e.shiftKey){
                  e.preventDefault();
                  if(!loading && query.trim()) startRun();
                }
              }}
              className="input"
              placeholder="e.g. staff machine learning engineer (Press Enter)"
            />
            <div style={{display:'flex', gap:8, flexWrap:'wrap', alignItems:'center'}}>
            <div style={{marginTop:12, paddingTop:12, borderTop:'1px solid var(--color-border)'}}>
              <div className="section-title" style={{marginBottom:6}}>Quick Search (no run)</div>
              <div style={{display:'flex', gap:6, marginBottom:6}}>
                <input value={quickQuery} onChange={e=>setQuickQuery(e.target.value)} className="input" placeholder="e.g. frontend engineer" />
                <button className="btn outline" disabled={quickLoading || !quickQuery.trim()} onClick={runQuickSearch}>{quickLoading? 'Searching…':'Go'}</button>
              </div>
              {quickResults && (
                <div style={{maxHeight:160, overflow:'auto', display:'grid', gap:6}}>
                  {quickResults.map((r,i)=>(
                    <div key={i} style={{fontSize:'.55rem', padding:'4px 6px', background:'#1e2731', border:'1px solid #2c3744', borderRadius:4}}>
                      <strong>{r.title}</strong> <span className="muted">{r.company||''}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
              <button disabled={loading || !query.trim() || !(resumeText.trim() || fileInfo)} onClick={async ()=>{
                if(seedEnabled){
                  // pass flag via query param hack (backend reads env, but we hint user to set env permanently)
                  // For immediate UX, just run normally; seeding controlled by backend env.
                }
                await startRun();
              }} className="btn" style={{alignSelf:'flex-start'}}>{loading? 'Starting…' : (runId && status && !['done','error'].includes(status.stage) ? `Running ${Math.round(fineProgress*100)}%` : 'Start Run')}</button>
              {!(resumeText.trim() || fileInfo) && <div style={{fontSize:'.5rem', color:'var(--color-accent)', fontWeight:500}}>Upload or paste a resume first</div>}
              {/* Auto mode removed; manual runs only */}
              {jobs.length===0 && !loading && (
                <label style={{display:'flex', alignItems:'center', gap:4, fontSize:'.55rem', cursor:'pointer'}} title="Enable DEMO_SEED_JOBS in backend env for synthetic fallback jobs when scrape empty">
                  <input type="checkbox" checked={seedEnabled} onChange={e=> setSeedEnabled(e.target.checked)} /> Seed if empty
                </label>
              )}
              {/* Removed autoMode hint */}
            </div>
            <div style={{marginTop:4}}>
              <div style={{display:'flex', justifyContent:'space-between', fontSize:'.55rem', letterSpacing:'.08em', textTransform:'uppercase', color:'var(--color-text-soft)', marginBottom:4}}>
                <span>{prettyStage(status?.stage)}</span><span>{(()=>{ const pct=Math.round(fineProgress*100); if(pct===0 && (status?.counts?.jobs||0)>0) return '1%'; return pct+'%'; })()}</span>
              </div>
              <div className="progress-track"><div className="progress-fill" style={{width:`${Math.round(fineProgress*100)}%`}} /></div>
              {status && !['done','error'].includes(status.stage) && (
                <div style={{marginTop:4, display:'flex', justifyContent:'space-between', fontSize:'.5rem', color:'var(--color-text-soft)'}}>
                  {status.stage==='enrich' && status.counts?.jobs ? <span>Enriched {status.counts.enriched||0}/{status.counts.jobs}</span> : null}
                  {status.stage==='generate' && status.counts?.jobs ? <span>Generated {status.counts.generated||0}/{status.counts.jobs}</span> : null}
                  {status.stage==='email' && status.counts?.jobs ? <span>Emailed {status.counts.emails||0}/{status.counts.jobs}</span> : null}
                  <span style={{marginLeft:'auto'}}>Stage {Math.round(progress*100)}%</span>
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="card" style={{display:'flex', flexDirection:'column'}}>
          <div className="section-title" style={{marginBottom:4}}>Resume</div>
          <textarea className="input" style={{minHeight:120, fontSize:'.7rem'}} placeholder="Paste plain text resume here" value={resumeText} onChange={e=>{setResumeText(e.target.value); setResumeSaved(false);}} />
          <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
            <button className="btn" disabled={!runId || !resumeText.trim()} onClick={async ()=>{
              if(!runId) return;
              const res = await fetch(`${API_BASE}/runs/${runId}/resume`, {method:'POST', headers: baseHeaders, body: JSON.stringify({run_id: Number(runId), resume_text: resumeText})});
              if(res.ok){ setResumeSaved(true); await postActivity({ type: 'resume_saved', title: 'Saved resume text', run_id: Number(runId)||undefined, details: { length: resumeText.length } }); } }}>
              {resumeSaved? 'Saved' : 'Save Resume'}
            </button>
            <label className="btn outline" style={{cursor:'pointer'}}>
              <input type="file" style={{display:'none'}} accept=".pdf,.docx,.txt,.md" onChange={async e=>{
                const f = e.target.files?.[0]; if(!f) return; setFileInfo(null);
                if(!runId){
                  setPendingFile(f); setFileInfo(`Selected: ${f.name}`);
                  // Optionally parse text if plain text to prefill resumeText
                  if(f.type==='text/plain'){
                    try { const txt = await f.text(); if(txt){ setResumeText(txt.slice(0,20000)); setResumeSaved(true); } } catch { /* ignore */ }
                  }
                  return;
                }
                setFileUploading(true);
                const form = new FormData(); form.append('file', f);
                try { const res = await fetch(`${API_BASE}/runs/${runId}/resume/upload`, {method:'POST', headers: (():Record<string,string>=>{ const h={...baseHeaders}; delete h['Content-Type']; return h;})(), body: form}); if(res.ok){ const data = await res.json(); setFileInfo(`${data.stored} (${data.length} chars)`); setResumeSaved(true); await postActivity({ type: 'resume_uploaded', title: 'Uploaded resume file', run_id: Number(runId)||undefined, details: { name: f.name, size: f.size } }); 
                  // After upload, auto-regenerate tailored resumes for all jobs
                  try { setRegenStatus('Retailoring…'); const regen = await fetch(`${API_BASE}/runs/${runId}/resumes/generate`, {method:'POST', headers: baseHeaders, body: JSON.stringify({all:true, force:true})});
                    if(regen.ok){ const info = await regen.json(); setRegenStatus(`Retailored ${info.processed} resumes`); await postActivity({ type: 'resume_retailored', title: 'Retailored resumes', run_id: Number(runId)||undefined, details: info }); const rj = await fetch(`${API_BASE}/runs/${runId}/jobs`, { headers: baseHeaders }); if(rj.ok) setJobs(await rj.json()); }
                    else setRegenStatus('Retailor failed');
                  } catch { setRegenStatus('Retailor error'); }
                } else { setFileInfo('Upload failed'); } }
                catch{ setFileInfo('Error'); } finally { setFileUploading(false); }
              }} />Upload File
            </label>
            {resumeSaved && <span className="muted" style={{fontSize:'.55rem'}}>Saved</span>}
          </div>
          <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
            {fileUploading && <div className="muted" style={{fontSize:'.55rem'}}>Uploading...</div>}
            {fileInfo && <div className="muted" style={{fontSize:'.55rem'}}>Uploaded: {fileInfo}</div>}
            {regenStatus && <div className="muted" style={{fontSize:'.55rem'}}>{regenStatus}</div>}
          </div>
        </div>
        <div className="card" style={{display:'flex', flexDirection:'column', gap:12}}>
          <div className="section-title">Generation & Email</div>
          <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
            <button className="btn" disabled={!runId || !jobs.length} onClick={async ()=>{
              if(!runId) return; setGenStatus('Generating...');
              try { const r = await fetch(`${API_BASE}/runs/${runId}/generate`, {method:'POST', headers: baseHeaders, body: JSON.stringify({limit:10})}); if(r.ok){ const d=await r.json(); setGenStatus(`Generated for ${d.generated}`); await postActivity({ type: 'doc_generated', title: 'Generated documents', run_id: Number(runId)||undefined, details: { generated: d.generated, scope: 'bulk' } }); const jr = await fetch(`${API_BASE}/runs/${runId}/jobs`, { headers: baseHeaders }); if(jr.ok) setJobs(await jr.json()); }
                else setGenStatus('Generation failed'); }
              catch{ setGenStatus('Generation error'); }
            }}>Generate</button>
            <button className="btn outline" disabled={!runId || !jobs.length} onClick={async ()=>{
              if(!runId) return; setSendStatus('Sending...');
              try { const r = await fetch(`${API_BASE}/runs/${runId}/send`, {method:'POST', headers: baseHeaders, body: JSON.stringify({max_emails:3, dry_run:true})}); if(r.ok){ const d=await r.json(); setSendStatus(`Sent ${d.sent} dry-run`); await postActivity({ type: 'email_send_dry', title: 'Sent emails (dry run)', run_id: Number(runId)||undefined, details: d }); const sr=await fetch(`${API_BASE}/runs/${runId}`, { headers: baseHeaders }); if(sr.ok) setStatus(await sr.json()); } else setSendStatus('Send failed'); }
              catch{ setSendStatus('Send error'); }
            }}>Send (Dry)</button>
            <button className="btn outline" disabled={!runId || !jobs.length} onClick={async ()=>{
              if(!runId) return; setEnrichStatus('Re-enriching...');
              try { const r = await fetch(`${API_BASE}/runs/${runId}/enrich`, {method:'POST', headers: baseHeaders}); if(r.ok){ const d=await r.json(); setEnrichStatus(`Enriched: email ${d.updated_with_email}, name ${d.updated_name_only}`); await postActivity({ type: 're_enrich', title: 'Re-enriched jobs', run_id: Number(runId)||undefined, details: d }); const jr = await fetch(`${API_BASE}/runs/${runId}/jobs`, { headers: baseHeaders }); if(jr.ok) setJobs(await jr.json()); }
                else setEnrichStatus('Re-enrich failed'); }
              catch { setEnrichStatus('Re-enrich error'); }
            }}>Re-Enrich</button>
            <button className="btn outline" disabled={!runId} onClick={()=>{ setShowRaw(v=>!v); }}>{showRaw? 'Hide Raw' : 'Show Raw'}</button>
          </div>
          <div style={{display:'flex', gap:16, flexWrap:'wrap'}}>
            <div style={{fontSize:'.6rem'}} className="muted">Docs: {jobsWithDocs}/{jobs.length} ({generationRatio}%)</div>
            {genStatus && <div style={{fontSize:'.6rem'}} className="muted">{genStatus}</div>}
            {sendStatus && <div style={{fontSize:'.6rem'}} className="muted">{sendStatus}</div>}
            {enrichStatus && <div style={{fontSize:'.6rem'}} className="muted">{enrichStatus}</div>}
          </div>
          {status?.errors?.length>0 && <div className="error-text" style={{fontSize:'.6rem'}}>{status.errors.join(', ')}</div>}
        </div>
      </div>

      <div className="grid" style={{gap:32, gridTemplateColumns:'minmax(540px,1fr) 320px'}}>
  <div style={{display:'flex', flexDirection:'column', gap:24}}>
          <div className="card" style={{padding:'0', overflow:'hidden'}}>
            <div style={{display:'flex', alignItems:'center', gap:24, padding:'20px 24px', borderBottom:'1px solid var(--color-border)'}}>
              <div style={{flex:1}}>
                <div className="section-title" style={{marginBottom:6}}>Jobs ({filteredJobs.length})</div>
                <div className="muted" style={{fontSize:'.6rem'}}>Filtered view • {filter==='all'?'All Jobs': filter==='withDocs' ? 'With Docs' : 'Missing Docs'}</div>
              </div>
              <div className="tabs">
                <button className={`tab ${filter==='all'?'active':''}`} onClick={()=>setFilter('all')}>All</button>
                <button className={`tab ${filter==='withDocs'?'active':''}`} onClick={()=>setFilter('withDocs')}>Docs</button>
                <button className={`tab ${filter==='withoutDocs'?'active':''}`} onClick={()=>setFilter('withoutDocs')}>None</button>
              </div>
            </div>
            <div style={{maxHeight:560, overflow:'auto', padding:24, display:'grid', gap:16, gridTemplateColumns:'repeat(auto-fill,minmax(240px,1fr))'}}>
              {showEmpty && <div className="empty" style={{gridColumn:'1 / -1'}}>No jobs match this filter.</div>}
              {!runId && jobs.length===0 && <div className="empty" style={{gridColumn:'1 / -1'}}>Start a run to see jobs.</div>}
              {filteredJobs.map(j => {
                const hasDocs = !!(j.cover_letter || j.resume_custom);
                const expanded = expandedJobId===j.id;
                const detail = expanded ? (jobDetailCache[j.id] || j) : null;
                return (
                  <div key={j.id} className="job-card" onMouseEnter={()=>setHoveredJob(j.id)} onMouseLeave={()=>setHoveredJob(null)} style={{position:'relative'}}>
                    <div style={{display:'flex', justifyContent:'space-between', gap:8}}>
                      <div style={{fontWeight:600, fontSize:'.74rem', lineHeight:1.3}}>{j.title}</div>
                      <div style={{display:'flex', gap:4}}>
                        {j.url && <a className="badge-link" href={j.url} target="_blank" rel="noreferrer">Open</a>}
                        {runId && <button className="mini-btn" title="Open full view" onClick={(e)=>{ e.stopPropagation(); const w = window.open(`/jobs/${j.id}?runId=${runId}`, '_blank', 'noopener'); if(!w){ alert('Popup blocked'); } }} style={{minWidth:50}}>Details</button>}
                        <button className="mini-btn" onClick={()=> expanded ? setExpandedJobId(null) : loadJobDetails(j.id)} disabled={detailLoading===j.id} style={{minWidth:54}}>{expanded? 'Close' : (detailLoading===j.id? 'Loading':'Open')}</button>
                      </div>
                    </div>
                    <div className="muted" style={{fontSize:'.58rem'}}>{j.company || '—'} • {j.location || 'N/A'}</div>
                    <div style={{display:'flex', gap:4, flexWrap:'wrap', marginTop:6}}>
                      {hasDocs && <span className="pill green">Docs</span>}
                      {!hasDocs && <span className="pill gray">Pending</span>}
                      {(j.recruiter_email || j.recruiter_name) && <span className="pill blue" title={j.recruiter_email || ''}>Recruiter</span>}
                      {typeof j.resume_match === 'number' && (
                        <span
                          className="pill"
                          style={j.resume_match>=70? {background:'#14532d'} : j.resume_match>=40? {background:'#1e3a8a'} : {background:'#fff', color:'#6b4a2f', border:'1px solid #e5d9cf', fontWeight:600}}
                          title="Resume match score"
                        >{j.resume_match}%</span>
                      )}
                    </div>
                    {expanded && detail && (
                      <div style={{marginTop:8, display:'flex', flexDirection:'column', gap:8}}>
                        <div className="two-col-flex">
                          <div style={{display:'flex', flexDirection:'column', gap:8, flex:1}}>
                            <div className="panel-subtitle">Recruiter Contacts</div>
                            <div className="contact-grid">
                              {(detail.recruiter_contacts && detail.recruiter_contacts.length>0) ? detail.recruiter_contacts.map((c,i)=> {
                                const initials = (c.name||'').split(/\s+/).filter(Boolean).slice(0,2).map(p=>p[0]?.toUpperCase()).join('') || 'RC';
                                return (
                                  <div key={i} className="contact-card">
                                    <div className="contact-head">
                                      <div style={{display:'flex', alignItems:'center', gap:8}}>
                                        <div className="contact-avatar">{initials}</div>
                                        <div style={{display:'flex', flexDirection:'column', gap:2}}>
                                          <span style={{fontSize:'.55rem', fontWeight:600}}>{c.name || '—'}</span>
                                          {c.title && <span className="contact-title">{c.title}</span>}
                                        </div>
                                      </div>
                                      {c.linkedin_url && <a href={c.linkedin_url} target="_blank" rel="noreferrer" className="chip-btn" style={{fontSize:'.45rem'}}>LI</a>}
                                    </div>
                                    {c.email && <div className="contact-email">
                                      <a href={`mailto:${c.email}`} style={{color:'var(--color-accent)', textDecoration:'none'}}>{c.email}</a>
                                      <button className="chip-btn" onClick={()=>{ try{ navigator.clipboard.writeText(c.email||''); }catch{} }}>Copy</button>
                                    </div>}
                                  </div>
                                );
                              }) : <div className="muted" style={{fontSize:'.5rem'}}>No contacts yet.</div>}
                            </div>
                          </div>
                          <div style={{display:'flex', flexDirection:'column', gap:12, flex:1}}>
                            <div className="doc-panel">
                              <h4>Cover Letter</h4>
                              <div className="doc-snippet" style={{fontSize:'.55rem'}} onDoubleClick={()=> detail.cover_letter && copyToClipboard(detail.cover_letter)}>
                                {detail.cover_letter || '—'}
                              </div>
                              <div className="inline-badges">
                                {coverDocxMap[j.id] && <a href={coverDocxMap[j.id]} target="_blank" rel="noreferrer" className="dw-link" onClick={async()=>{ await postActivity({ type: 'doc_download', title: 'Downloaded cover letter', job_id: j.id, run_id: Number(runId)||undefined }); }}>DOCX</a>}
                                {detail.resume_txt_url && <a href={detail.resume_txt_url} target="_blank" rel="noreferrer" className="dw-link">Plain TXT</a>}
                              </div>
                            </div>
                            <div className="doc-panel">
                              <h4>Tailored Resume</h4>
                              <div className="doc-snippet" style={{fontSize:'.55rem'}} onDoubleClick={()=> detail.resume_custom && copyToClipboard(detail.resume_custom)}>
                                {detail.resume_custom || '—'}
                              </div>
                              <div className="inline-badges">
                                {resumeDocxMap[j.id] && <a href={resumeDocxMap[j.id]} target="_blank" rel="noreferrer" className="dw-link" onClick={async()=>{ await postActivity({ type: 'doc_download', title: 'Downloaded resume', job_id: j.id, run_id: Number(runId)||undefined }); }}>DOCX</a>}
                                {detail.resume_docx_url && <a href={detail.resume_docx_url} target="_blank" rel="noreferrer" className="dw-link">Raw DOCX</a>}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    {!expanded && (j.recruiter_name || j.recruiter_email) && (
                      <div style={{marginTop:4}} className="muted">
                        <div style={{fontSize:'.52rem'}}>Name: {j.recruiter_name || '—'}</div>
                        <div style={{fontSize:'.52rem', overflow:'hidden', textOverflow:'ellipsis'}} title={j.recruiter_email || ''}>Email: {j.recruiter_email || '—'}</div>
                      </div>
                    )}
                    {!expanded && hasDocs && (
                      <>
                        <details style={{marginTop:8}}>
                          <summary className="summary-line">Cover Letter</summary>
                          <div className="doc-snippet" onDoubleClick={()=> j.cover_letter && copyToClipboard(j.cover_letter)}>{j.cover_letter?.slice(0,500) || '—'}{(j.cover_letter||'').length>500 && '…'}</div>
                        </details>
                        {(j.resume_txt_url || j.resume_docx_url || coverDocxMap[j.id]) && (
                          <div style={{marginTop:6, display:'flex', flexWrap:'wrap', gap:6}}>
                            {coverDocxMap[j.id] && <a href={coverDocxMap[j.id]} target="_blank" rel="noreferrer" className="badge-link" style={{fontSize:'.52rem'}} onClick={async()=>{ await postActivity({ type: 'doc_download', title: 'Downloaded cover letter', job_id: j.id, run_id: Number(runId)||undefined }); }}>Cover DOCX</a>}
                            {j.resume_txt_url && <a href={j.resume_txt_url} target="_blank" rel="noreferrer" className="badge-link" style={{fontSize:'.52rem'}}>Resume TXT</a>}
                            {j.resume_docx_url && <a href={j.resume_docx_url} target="_blank" rel="noreferrer" className="badge-link" style={{fontSize:'.52rem'}}>Resume DOCX</a>}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
          {showRaw && (
            <div className="card" style={{maxHeight:280, overflow:'auto'}}>
              <div className="section-title">Raw JSON (Jobs)</div>
              <pre style={{fontSize:'.55rem', whiteSpace:'pre-wrap'}}>{JSON.stringify(jobs.slice(0,50), null, 2)}</pre>
            </div>
          )}
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:24}}>
          <div className="card">
            <div className="section-title">Pipeline Status</div>
            {status ? (
              <div style={{display:'flex', flexDirection:'column', gap:12}}>
                <div className="stat-bar">
                  <div className="stat"><span className="stat-label">Status</span><span className="stat-value">{status.status}</span></div>
                  <div className="stat"><span className="stat-label">Stage</span><span className="stat-value" style={{textTransform:'capitalize'}}>{status.stage}</span></div>
                  <div className="stat"><span className="stat-label">Jobs</span><span className="stat-value">{status.counts?.jobs ?? jobs.length}</span></div>
                </div>
                <div>
                  <div style={{display:'flex', justifyContent:'space-between', fontSize:'.5rem', textTransform:'uppercase', letterSpacing:'.08em', color:'var(--color-text-soft)', marginBottom:4}}>
                    <span>Progress</span><span>{(()=>{ const pct=Math.round(fineProgress*100); if(pct===0 && (status?.counts?.jobs||0)>0) return '1%'; return pct+'%'; })()}</span>
                  </div>
                  <div className="progress-track small"><div className="progress-fill" style={{width:`${Math.round(fineProgress*100)}%`}} /></div>
                  {status && !['done','error'].includes(status.stage) && (
                    <div style={{marginTop:4, display:'flex', gap:8, flexWrap:'wrap', fontSize:'.45rem', color:'var(--color-text-soft)'}}>
                      {status.stage==='enrich' && status.counts?.jobs ? <span>Enriched {status.counts.enriched||0}/{status.counts.jobs}</span> : null}
                      {status.stage==='generate' && status.counts?.jobs ? <span>Generated {status.counts.generated||0}/{status.counts.jobs}</span> : null}
                      {status.stage==='email' && status.counts?.jobs ? <span>Emailed {status.counts.emails||0}/{status.counts.jobs}</span> : null}
                      <span style={{marginLeft:'auto'}}>Stage {Math.round(progress*100)}%</span>
                    </div>
                  )}
                </div>
              </div>
            ) : <div className="empty">No active run.</div>}
          </div>
          <div className="card">
            <div className="section-title">Recent Runs</div>
            <div className="runs-list" style={{maxHeight:400}}>
              <div className="runs-scroll">
                {runs.length === 0 && <div className="empty">No runs yet.</div>}
                {runs.map(r => (
                  <button key={r.id} onClick={()=> setRunId(String(r.id))} className={`run-row ${runId==String(r.id)?'active':''}`} style={{textAlign:'left', width:'100%', border:'none', background:'transparent', cursor:'pointer'}}>
                    <div className="job-top" style={{alignItems:'baseline'}}>
                      <span style={{fontWeight:600}}>Run #{r.id}</span>
                      <span className="muted" style={{fontSize:'.55rem', textTransform:'uppercase', letterSpacing:'.08em'}}>{r.status}</span>
                    </div>
                    <div className="muted" style={{fontSize:'.65rem'}}>{r.query}</div>
                    <div className="muted" style={{fontSize:'.55rem'}}>Stage: {r.stage} · Jobs: {r.jobs}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
          {/* Email Tracking moved to /analytics */}
        </div>
      </div>
    </div>
  );
}
