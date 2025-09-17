"use client"
import React, { useState, useEffect } from 'react'

interface RunStartResponse { task_id: string }
interface RunStatus { id:number; status:string; stage:string; counts: {jobs:number; enriched:number; emails:number; generated?:number; generation_progress?:{processed:number; total:number}}; errors?:string[] }
interface EmailEvent { job_id?:number|null; email?:string; subject?:string; dry_run?:boolean; status?:string; error?:string; template?:boolean }
interface TrackedMessage { id:string; to_email:string; subject:string; created_at:string; events:number; provider_msgid?:string|null }
interface TrackedEvent { id:number; msg_id:string; event:string; email?:string; url?:string; reason?:string; timestamp:number }
interface RecruiterContact { job_id:number; contacts:{name:string; title:string; email:string; linkedin_url?:string}[] }
interface CoverLetterDoc { job_id:number; docx_filename:string; size:number }

const apiBases = () => {
  return [
    process.env.NEXT_PUBLIC_API_BASE_URL,
    typeof window !== 'undefined' ? window.location.origin + '/api' : undefined,
    'http://localhost:8011/api',
    'http://127.0.0.1:8011/api'
  ].filter(Boolean) as string[]
}

export default function PipelinePage(){
  const [query,setQuery]=useState('data engineer remote')
  const [loading,setLoading]=useState(false)
  const [run,setRun]=useState<RunStartResponse|null>(null)
  const [status,setStatus]=useState<RunStatus|null>(null)
  const [polling,setPolling]=useState(false)
  const [sending,setSending]=useState(false)
  const [sendResult,setSendResult]=useState<any|null>(null)
  const [emailEvents,setEmailEvents]=useState<EmailEvent[]>([])
  const [loadingEmails,setLoadingEmails]=useState(false)
  const [tracking,setTracking]=useState(false)
  const [tracked,setTracked]=useState<TrackedMessage[]>([])
  const [showTracked,setShowTracked]=useState(false)
  const [trackedEvents,setTrackedEvents]=useState<TrackedEvent[]|null>(null)
  const [recruiters,setRecruiters]=useState<RecruiterContact[]|null>(null)
  const [loadingRecruiters,setLoadingRecruiters]=useState(false)
  const [coverDocs,setCoverDocs]=useState<CoverLetterDoc[]|null>(null)
  const [loadingCovers,setLoadingCovers]=useState(false)
  const devToken=process.env.NEXT_PUBLIC_DEV_BEARER || 'dev-local-token'

  async function startRun(){
    setLoading(true)
    setStatus(null)
    for(const base of apiBases()){
      try{
        const res = await fetch(base.replace(/\/$/,'')+ '/jobs/run', {
          method:'POST',
          headers:{'Content-Type':'application/json','Authorization':`Bearer ${devToken}`},
          body: JSON.stringify({query, locations:[], sources:['indeed'], auto_send:false})
        })
        if(!res.ok) continue
        const json:RunStartResponse = await res.json()
        const runId = parseInt(json.task_id,10)
        setRun({...json, task_id: json.task_id})
        poll(runId)
        return
      }catch(_){/* try next */}
    }
    setLoading(false)
  }

  async function trackEmails(){
    setTracking(true); setShowTracked(true); setTrackedEvents(null);
    for(const base of apiBases()){
      try{
        const res = await fetch(base.replace(/\/$/,'')+ '/emails/tracked');
        if(!res.ok) continue;
        const js:TrackedMessage[] = await res.json();
        setTracked(js);
        break;
      }catch(_){/* try next */}
    }
    setTracking(false);
  }

  async function poll(id:number){
    setPolling(true)
    let attempts=0
    while(attempts<60){
      attempts++
      let updated=false
      for(const base of apiBases()){
        try{
          const res = await fetch(base.replace(/\/$/,'')+ `/runs/${id}`, {headers:{'Authorization':`Bearer ${devToken}`}})
          if(!res.ok) continue
            const json:RunStatus = await res.json()
            setStatus(json)
            updated=true
            if(json.status==='done' || json.status==='error'){
              setPolling(false)
              setLoading(false)
              // auto fetch email events when finished
              fetchEmailEvents(id)
              return
            }
            break
        }catch(_){ /* try other base */ }
      }
      if(!updated) await new Promise(r=>setTimeout(r, 1500))
      else await new Promise(r=>setTimeout(r, 800))
    }
    setPolling(false)
    setLoading(false)
  }

  async function sendDry(){
    if(!status) return
    setSending(true)
    setSendResult(null)
    for(const base of apiBases()){
      try{
        const res = await fetch(base.replace(/\/$/,'')+ `/runs/${status.id}/send`, {
          method:'POST',
          headers:{'Content-Type':'application/json','Authorization':`Bearer ${devToken}`},
          body: JSON.stringify({max_emails:5, dry_run:true})
        })
        if(!res.ok) continue
        const json = await res.json()
        setSendResult(json)
        // after sending, refresh events list
        await fetchEmailEvents(status.id)
        break
      }catch(_){/* try next */}
    }
    setSending(false)
  }

  async function fetchEmailEvents(id:number){
    setLoadingEmails(true)
    for(const base of apiBases()){
      try{
        const res = await fetch(base.replace(/\/$/,'')+ `/runs/${id}/emails`, {headers:{'Authorization':`Bearer ${devToken}`}})
        if(!res.ok) continue
        const json:EmailEvent[] = await res.json()
        setEmailEvents(json)
        break
      }catch(_){/* try others */}
    }
    setLoadingEmails(false)
  }

  async function fetchRecruiters(){
    if(!status) return; setLoadingRecruiters(true); setRecruiters(null);
    for(const base of apiBases()){
      try{
        const res= await fetch(base.replace(/\/$/,'')+`/runs/${status.id}/recruiters`);
        if(!res.ok) continue; const js:RecruiterContact[]=await res.json(); setRecruiters(js); break;
      }catch(_){/* try next */}
    }
    setLoadingRecruiters(false);
  }

  async function fetchCoverLetters(){
    if(!status) return; setLoadingCovers(true); setCoverDocs(null);
    for(const base of apiBases()){
      try{
        const res= await fetch(base.replace(/\/$/,'')+`/runs/${status.id}/coverletters`);
        if(!res.ok) continue; const js:CoverLetterDoc[]=await res.json(); setCoverDocs(js); break;
      }catch(_){/* try next */}
    }
    setLoadingCovers(false);
  }

  const hasRun = !!status

  // When status transitions to done outside polling (edge), fetch events
  useEffect(()=>{
    if(status && (status.status==='done' || status.status==='error')){
      fetchEmailEvents(status.id)
    }
  }, [status?.status])

  return (
    <div style={{display:'flex', flexDirection:'column', gap:'1rem'}}>
      <h2 style={{fontSize:'1.1rem'}}>Pipeline Runner</h2>
      <div style={{display:'flex', gap:'.5rem'}}>
        <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search keywords" style={{flex:1, padding:'.5rem', background:'#1c232c', border:'1px solid #2a3542', borderRadius:6}} />
        <button disabled={loading} onClick={startRun} style={{padding:'.55rem .9rem', background:'#2563eb', border:'none', borderRadius:6, color:'#fff', fontWeight:600}}>{loading? 'Starting…':'Run'}</button>
  <button onClick={trackEmails} style={{padding:'.55rem .9rem', background:'#0d9488', border:'none', borderRadius:6, color:'#fff', fontWeight:600}}>{tracking? 'Tracking…':'Track Emails'}</button>
      </div>
      {run && status && (
        <div style={{fontSize:'.7rem', opacity:.7}}>Run ID: {status.id} | Task: {run.task_id}</div>
      )}
      {status && (
        <div style={{display:'flex', gap:'1rem', flexWrap:'wrap'}}>
          {['jobs','enriched','emails','generated'].map(k=>{
            if(k==='generated' && !(status.counts as any)['generated']) return null;
            const v=(status.counts as any)[k]||0
            return <div key={k} style={{background:'#1c232c', border:'1px solid #2a3542', padding:'.7rem .9rem', borderRadius:8, minWidth:110}}>
              <div style={{fontSize:'.6rem', letterSpacing:'.08em', textTransform:'uppercase', opacity:.55}}>{k}</div>
              <div style={{fontSize:'1.1rem', fontWeight:600}}>{v}</div>
            </div>
          })}
          <div style={{background:'#1c232c', border:'1px solid #2a3542', padding:'.7rem .9rem', borderRadius:8, minWidth:140}}>
            <div style={{fontSize:'.6rem', letterSpacing:'.08em', textTransform:'uppercase', opacity:.55}}>Status</div>
            <div style={{fontSize:'1.1rem', fontWeight:600}}>{status.status}</div>
          </div>
        </div>
      )}
      <div style={{display:'flex', gap:'.5rem', marginTop:'.9rem', flexWrap:'wrap', alignItems:'center'}}>
        <button onClick={sendDry} disabled={sending || !hasRun} style={{padding:'.45rem .8rem', background: hasRun? '#9333ea':'#4b5563', border:'none', borderRadius:6, color:'#fff', fontSize:'.8rem', fontWeight:600, cursor: hasRun? 'pointer':'not-allowed'}}>
          {sending? 'Sending…':'Send (Dry)'}
        </button>
        <button onClick={()=> hasRun && fetchEmailEvents(status!.id)} disabled={loadingEmails || !hasRun} style={{padding:'.45rem .8rem', background:'#374151', border:'1px solid #4b5563', borderRadius:6, color:'#fff', fontSize:'.75rem', cursor: hasRun? 'pointer':'not-allowed'}}>
          {loadingEmails? 'Loading…':'Refresh Emails'}
        </button>
        <button onClick={fetchRecruiters} disabled={!hasRun || loadingRecruiters} style={{padding:'.45rem .8rem', background: hasRun? '#059669':'#4b5563', border:'none', borderRadius:6, color:'#fff', fontSize:'.75rem', fontWeight:600}}>
          {loadingRecruiters? 'Loading recruiters…':'Load Recruiters'}
        </button>
        <button onClick={fetchCoverLetters} disabled={!hasRun || loadingCovers} style={{padding:'.45rem .8rem', background: hasRun? '#d97706':'#4b5563', border:'none', borderRadius:6, color:'#fff', fontSize:'.75rem', fontWeight:600}}>
          {loadingCovers? 'Loading cover letters…':'Load Cover Letters (.docx)'}
        </button>
        {!hasRun && <div style={{fontSize:'.62rem', opacity:.55}}>Run first to enable sending & tracking.</div>}
        {sendResult && (
          <div style={{fontSize:'.65rem', opacity:.7}}>
            sent: {sendResult.sent} &nbsp; failures: {sendResult.failures} &nbsp; template: {String(sendResult.template_used)}
          </div>
        )}
      </div>
      {hasRun && emailEvents.length>0 && (
        <div style={{marginTop:'1rem'}}>
          <div style={{fontSize:'.65rem', opacity:.6, marginBottom:'.35rem', letterSpacing:'.05em'}}>EMAIL EVENTS ({emailEvents.length})</div>
          <div style={{border:'1px solid #2a3542', borderRadius:8, overflow:'hidden'}}>
            <table style={{width:'100%', borderCollapse:'collapse', fontSize:'.7rem'}}>
              <thead style={{background:'#111827'}}>
                <tr>
                  <th style={{textAlign:'left', padding:'.45rem .6rem', borderBottom:'1px solid #1f2937'}}>Email</th>
                  <th style={{textAlign:'left', padding:'.45rem .6rem', borderBottom:'1px solid #1f2937'}}>Subject</th>
                  <th style={{textAlign:'left', padding:'.45rem .6rem', borderBottom:'1px solid #1f2937'}}>Status</th>
                  <th style={{textAlign:'left', padding:'.45rem .6rem', borderBottom:'1px solid #1f2937'}}>Job</th>
                  <th style={{textAlign:'left', padding:'.45rem .6rem', borderBottom:'1px solid #1f2937'}}>Template</th>
                </tr>
              </thead>
              <tbody>
                {emailEvents.map((e,i)=>{
                  return <tr key={i} style={{background:i%2? '#1c232c':'#161d25'}}>
                    <td style={{padding:'.4rem .6rem', maxWidth:160, overflow:'hidden', textOverflow:'ellipsis'}} title={e.email}>{e.email}</td>
                    <td style={{padding:'.4rem .6rem', maxWidth:260, overflow:'hidden', textOverflow:'ellipsis'}} title={e.subject}>{e.subject}</td>
                    <td style={{padding:'.4rem .6rem'}}>{e.status || (e.dry_run? 'dry-run':'?')}</td>
                    <td style={{padding:'.4rem .6rem'}}>{e.job_id ?? ''}</td>
                    <td style={{padding:'.4rem .6rem'}}>{e.template? 'yes':''}</td>
                  </tr>
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {!status && !loading && (
        <div style={{fontSize:'.65rem', opacity:.5}}>Enter keywords and click Run to start background pipeline.</div>
      )}
      <hr style={{margin:'1.6rem 0', borderColor:'#243042'}} />
      <div style={{display:'flex', gap:'.6rem', flexWrap:'wrap', alignItems:'center'}}>
        <button onClick={async()=>{setTracking(true); setShowTracked(true); setTrackedEvents(null); for(const base of apiBases()){ try{ const res=await fetch(base.replace(/\/$/,'')+ '/emails/tracked'); if(!res.ok) continue; const js:TrackedMessage[]=await res.json(); setTracked(js); break;}catch(_){}} setTracking(false)}} style={{padding:'.5rem .9rem', background:'#0d9488', border:'none', borderRadius:6, color:'#fff', fontWeight:600, fontSize:'.8rem'}}>
          {tracking? 'Loading…':'Track Emails'}
        </button>
        {showTracked && <button onClick={()=>{setShowTracked(false);}} style={{padding:'.45rem .8rem', background:'#374151', border:'1px solid #4b5563', borderRadius:6, color:'#fff', fontSize:'.7rem'}}>Hide</button>}
      </div>
      {showTracked && (
        <div style={{marginTop:'1rem'}}>
          <div style={{fontSize:'.7rem', opacity:.65, marginBottom:'.4rem'}}>Tracked Sent Emails ({tracked.length})</div>
          <div style={{border:'1px solid #2a3542', borderRadius:8, overflow:'hidden'}}>
            <table style={{width:'100%', borderCollapse:'collapse', fontSize:'.65rem'}}>
              <thead style={{background:'#111827'}}>
                <tr>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>Msg ID</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>To</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>Subject</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>Events</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}></th>
                </tr>
              </thead>
              <tbody>
                {tracked.map((m,i)=> (
                  <tr key={m.id} style={{background: i%2? '#1c232c':'#161d25'}}>
                    <td style={{padding:'.4rem .55rem', maxWidth:140, overflow:'hidden', textOverflow:'ellipsis'}} title={m.id}>{m.id}</td>
                    <td style={{padding:'.4rem .55rem'}}>{m.to_email}</td>
                    <td style={{padding:'.4rem .55rem', maxWidth:260, overflow:'hidden', textOverflow:'ellipsis'}} title={m.subject}>{m.subject}</td>
                    <td style={{padding:'.4rem .55rem'}}>{m.events}</td>
                    <td style={{padding:'.4rem .55rem'}}>
                      <button onClick={async()=>{setTrackedEvents(null); for(const base of apiBases()){ try{ const r=await fetch(base.replace(/\/$/,'')+ `/emails/tracked/${m.id}`); if(!r.ok) continue; const ev:TrackedEvent[]=await r.json(); setTrackedEvents(ev); break;}catch(_){}} }} style={{padding:'.25rem .55rem', background:'#2563eb', border:'none', borderRadius:5, color:'#fff'}}>View</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {trackedEvents && (
            <div style={{marginTop:'1rem'}}>
              <div style={{fontSize:'.65rem', opacity:.6, marginBottom:'.3rem'}}>Events for {trackedEvents[0]?.msg_id}</div>
              <div style={{border:'1px solid #2a3542', borderRadius:8, overflow:'hidden'}}>
                <table style={{width:'100%', borderCollapse:'collapse', fontSize:'.6rem'}}>
                  <thead style={{background:'#111827'}}>
                    <tr>
                      <th style={{textAlign:'left', padding:'.35rem .5rem', borderBottom:'1px solid #1f2937'}}>Time</th>
                      <th style={{textAlign:'left', padding:'.35rem .5rem', borderBottom:'1px solid #1f2937'}}>Event</th>
                      <th style={{textAlign:'left', padding:'.35rem .5rem', borderBottom:'1px solid #1f2937'}}>Email</th>
                      <th style={{textAlign:'left', padding:'.35rem .5rem', borderBottom:'1px solid #1f2937'}}>Reason/URL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trackedEvents.map((e,i)=> (
                      <tr key={e.id} style={{background: i%2? '#1c232c':'#161d25'}}>
                        <td style={{padding:'.35rem .5rem'}}>{new Date(e.timestamp*1000).toISOString().replace('T',' ').slice(0,19)}</td>
                        <td style={{padding:'.35rem .5rem'}}>{e.event}</td>
                        <td style={{padding:'.35rem .5rem'}}>{e.email || ''}</td>
                        <td style={{padding:'.35rem .5rem', maxWidth:220, overflow:'hidden', textOverflow:'ellipsis'}} title={e.reason || e.url}>{e.reason || e.url || ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
      {recruiters && (
        <div style={{marginTop:'1.2rem'}}>
          <div style={{fontSize:'.65rem', opacity:.65, marginBottom:'.4rem'}}>Real Recruiter Contacts (Apollo) – no fallbacks</div>
          <div style={{border:'1px solid #2a3542', borderRadius:8, overflow:'hidden'}}>
            <table style={{width:'100%', borderCollapse:'collapse', fontSize:'.65rem'}}>
              <thead style={{background:'#111827'}}>
                <tr>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>Job ID</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>Name</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>Title</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>Email</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>LinkedIn</th>
                </tr>
              </thead>
              <tbody>
                {recruiters.flatMap(rc=> rc.contacts.length? rc.contacts.map((c,i)=>(
                  <tr key={rc.job_id+"-"+i} style={{background:'#161d25'}}>
                    <td style={{padding:'.4rem .55rem'}}>{rc.job_id}</td>
                    <td style={{padding:'.4rem .55rem'}}>{c.name}</td>
                    <td style={{padding:'.4rem .55rem'}}>{c.title}</td>
                    <td style={{padding:'.4rem .55rem'}}>{c.email}</td>
                    <td style={{padding:'.4rem .55rem'}}>{c.linkedin_url? <a href={c.linkedin_url} target="_blank" rel="noreferrer" style={{color:'#3b82f6'}}>Profile</a>: ''}</td>
                  </tr>
                )) : (
                  <tr key={rc.job_id+"-empty"} style={{background:'#1c232c'}}>
                    <td style={{padding:'.4rem .55rem'}}>{rc.job_id}</td>
                    <td style={{padding:'.4rem .55rem'}} colSpan={4}>(no unlocked contacts)</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {coverDocs && (
        <div style={{marginTop:'1.2rem'}}>
          <div style={{fontSize:'.65rem', opacity:.65, marginBottom:'.4rem'}}>Cover Letters (.docx) Generated For Run (Total {coverDocs.length})</div>
          <div style={{border:'1px solid #2a3542', borderRadius:8, overflow:'hidden'}}>
            <table style={{width:'100%', borderCollapse:'collapse', fontSize:'.65rem'}}>
              <thead style={{background:'#111827'}}>
                <tr>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>Job ID</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>File</th>
                  <th style={{textAlign:'left', padding:'.4rem .55rem', borderBottom:'1px solid #1f2937'}}>Size (KB)</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {coverDocs.map((d,i)=>(
                  <tr key={d.job_id} style={{background: i%2? '#1c232c':'#161d25'}}>
                    <td style={{padding:'.4rem .55rem'}}>{d.job_id}</td>
                    <td style={{padding:'.4rem .55rem'}}>{d.docx_filename}</td>
                    <td style={{padding:'.4rem .55rem'}}>{(d.size/1024).toFixed(1)}</td>
                    <td style={{padding:'.4rem .55rem'}}>
                      <a href={`http://localhost:8011/api/runs/${status?.id}/coverletters/${encodeURIComponent(d.docx_filename)}`} style={{color:'#3b82f6'}} target="_blank" rel="noreferrer">Download</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {status?.counts?.generation_progress && (
        <div style={{marginTop:'.4rem', maxWidth:420}}>
          {(()=>{ const gp=(status.counts as any).generation_progress; const pct = gp && gp.total? Math.round((gp.processed/gp.total)*100):0; return (
            <div style={{fontSize:'.6rem', opacity:.7}}>
              Cover Letter Generation: {gp.processed}/{gp.total} ({pct}%)
              <div style={{height:6, background:'#1f2937', borderRadius:4, marginTop:4, overflow:'hidden'}}>
                <div style={{height:'100%', width:pct+'%', background:'#2563eb', transition:'width .4s'}}></div>
              </div>
            </div>
          ) })()}
        </div>) }
    </div>
  )
}
