"use client"
import React, { useEffect, useMemo, useState } from 'react'
import { getApiBase } from '../../lib/apiBase'
import { useParams, useRouter } from 'next/navigation'
import { getAuthHeaders } from '../../lib/auth'

interface AppItem {
  id: number
  job_id: number
  job_title?: string | null
  status: string
  applied_at: string
  last_updated: string
  source?: string | null
}

interface DocMeta { id?: number|string; filename: string; document_type?: string; download_url?: string | null; created_at?: string }
interface Note { id?: number|string; title?: string|null; content: string; created_at?: string }
interface Communication { id?: string; communication_type?: string; subject?: string; content?: string; created_at?: string }
interface Interview { id?: string; title?: string; interview_type?: string; scheduled_at?: string; status?: string; job_title?: string }

interface Profile { id:number; email?:string|null; phone?:string|null; title?:string|null; company?:string|null; location?:string|null; notes?:string|null; last_activity_at?:string|null }
interface Activity { id:number; type:string; title?:string|null; job_id?:number|null; run_id?:number|null; details?:any; occurred_at:string }


export default function CandidateDetailPage(){
  const params = useParams();
  const router = useRouter();
  const candidateId = useMemo(()=>{
    const v = params?.id
    if (!v) return null
    const n = Array.isArray(v)? v[0] : v
    const parsed = parseInt(n,10)
    return Number.isNaN(parsed) ? null : parsed
  },[params])

  const apiBase = getApiBase()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string|null>(null)

  const [apps, setApps] = useState<AppItem[]>([])
  const [docs, setDocs] = useState<DocMeta[]>([])
  const [notes, setNotes] = useState<Note[]>([])
  const [comms, setComms] = useState<Communication[]>([])
  const [interviews, setInterviews] = useState<Interview[]>([])
  const [profile, setProfile] = useState<Profile|undefined>()
  const [activities, setActivities] = useState<Activity[]>([])
  const [newNote, setNewNote] = useState('')
  const [noteSaving, setNoteSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string|null>(null)
  const [docType, setDocType] = useState('')
  const [candidateName, setCandidateName] = useState<string>('')

  useEffect(()=>{
    let cancelled = false
    async function load(){
      if (!candidateId) return
      setLoading(true)
      setError(null)
      try{
  const headers: Record<string,string> = { ...(getAuthHeaders() as any), 'Accept':'application/json' }

        // Applications for this candidate
        const appsRes = await fetch(`${apiBase}/v1/recruiter/applications?candidate_id=${candidateId}&limit=100`, { cache:'no-store', headers })
        const appsJson = appsRes.ok ? await appsRes.json() : { data: [] }
        const aitems: AppItem[] = (appsJson.data||[]).map((a:any)=>({
          id:a.id, job_id:a.job_id, job_title:a.job_title, status:a.status, applied_at:a.applied_at, last_updated:a.last_updated, source:a.source
        }))
        if(!cancelled) setApps(aitems)

  const rid = (typeof window !== 'undefined' ? (localStorage.getItem('recruiterIdentifier') || 'default') : 'default')
  // Documents
  const docsRes = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates/${candidateId}/documents`, { cache:'no-store', headers })
  const docsJson = docsRes.ok ? await docsRes.json() : []
  if(!cancelled) setDocs(docsJson||[])

  // Notes
  const notesRes = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates/${candidateId}/notes`, { cache:'no-store', headers })
  const notesJson = notesRes.ok ? await notesRes.json() : []
  if(!cancelled) setNotes(notesJson||[])

  // Communications
  const commsRes = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates/${candidateId}/communications`, { cache:'no-store', headers })
  const commsJson = commsRes.ok ? await commsRes.json() : []
  if(!cancelled) setComms(commsJson||[])

  // Interviews
  const ivRes = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates/${candidateId}/interviews`, { cache:'no-store', headers })
  const ivJson = ivRes.ok ? await ivRes.json() : []
  if(!cancelled) setInterviews((ivJson||[]) as Interview[])

        // Recruiter-managed profile and activities (new endpoints)
        try {
          const rid = (typeof window !== 'undefined' ? (localStorage.getItem('recruiterIdentifier') || 'default') : 'default')
          // Resolve candidate display name
          try {
            const cr = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates?limit=500`, { cache:'no-store' })
            if (cr.ok) {
              const cj = await cr.json()
              const match = (cj.items||[]).find((x:any)=> x.id === candidateId)
              if (!cancelled && match) setCandidateName(match.name)
              if (!cancelled && !match) setError('Candidate not found for current recruiter')
            }
          } catch {}
          const pRes = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates/${candidateId}/profile`, { cache:'no-store', headers })
          if (pRes.ok) {
            const pj = await pRes.json();
            if(!cancelled) setProfile(pj)
          }
          const aRes = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates/${candidateId}/activities?limit=200`, { cache:'no-store', headers })
          if (aRes.ok) {
            const aj = await aRes.json();
            if(!cancelled) setActivities(aj.items||[])
          }
        } catch {}
      }catch(e:any){
        if(!cancelled) setError(e.message)
      }finally{
        if(!cancelled) setLoading(false)
      }
    }
    load()
    return ()=>{ cancelled = true }
  },[candidateId, apiBase])

  if (candidateId == null) {
    return (
      <div style={{padding:'1rem'}}>
        <div style={{fontSize:'.9rem', marginBottom:'.5rem'}}>Invalid candidate</div>
        <button onClick={()=> router.push('/candidates')} style={{padding:'.4rem .7rem', borderRadius:6, border:'1px solid #cbd5e1'}}>Back</button>
      </div>
    )
  }

  return (
    <div style={{display:'flex', flexDirection:'column', gap:'1rem'}}>
      <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
        <div>
          <h1 style={{fontSize:'1.1rem', margin:0}}>{candidateName || `Candidate #${candidateId}`}</h1>
          {profile && (
            <div style={{fontSize:'.8rem', color:'#6b7280', marginTop:4}}>
              {(profile.title || '—')} {profile.company ? `@ ${profile.company}` : ''} {profile.location ? `· ${profile.location}` : ''}
              {profile.email ? ` · ${profile.email}` : ''}
              {profile.phone ? ` · ${profile.phone}` : ''}
            </div>
          )}
        </div>
  <button onClick={()=> router.push('/candidates')} style={{padding:'.5rem .85rem', background:'#ffffff', color:'#111827', border:'1px solid #e5e7eb', borderRadius:8, fontSize:'.8rem'}}>Back</button>
      </div>
      {error && <div style={{color:'#b91c1c', fontSize:'.75rem'}}>Error: {error}</div>}
      {loading && <div style={{padding:'.75rem'}}>Loading…</div>}

      {/* Applications */}
      <section style={card}>
        <div style={sectionTitle}>Applications</div>
        {apps.length === 0 ? (
          <div style={{fontSize:'.75rem', opacity:.7}}>No applications yet.</div>
        ):(
      <div style={{overflowX:'auto', border:'1px solid #e5e7eb', borderRadius:8}}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.8rem' }}>
        <thead style={{ background: '#ffffff', textAlign: 'left' }}>
                <tr>
                  <th style={th}>Job</th>
                  <th style={th}>Stage</th>
                  <th style={th}>Source</th>
                  <th style={th}>Applied</th>
                  <th style={th}>Updated</th>
                </tr>
              </thead>
              <tbody>
                {apps.map(a=> (
          <tr key={a.id} style={{ borderTop: '1px solid #e5e7eb' }}>
                    <td style={td}>{a.job_title || `Job #${a.job_id}`}</td>
                    <td style={td}><Badge value={a.status} /></td>
                    <td style={td}>{a.source || '—'}</td>
                    <td style={td}>{a.applied_at ? new Date(a.applied_at).toLocaleString(): '—'}</td>
                    <td style={td}>{a.last_updated ? new Date(a.last_updated).toLocaleString(): '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Documents */}
    <section style={card}>
        <div style={sectionTitle}>Documents</div>
        <div style={{display:'flex', gap:8, alignItems:'center', marginBottom:8}}>
          <select value={docType} onChange={e=>setDocType(e.target.value)} style={{padding:'.4rem .6rem', border:'1px solid #e5e7eb', background:'#ffffff', color:'#111827', borderRadius:8, fontSize:'.85rem', outline:'none'}}>
            <option value=''>Type</option>
            <option value='resume'>Resume</option>
            <option value='cover_letter'>Cover Letter</option>
            <option value='other'>Other</option>
          </select>
          <input type="file" onChange={async (e)=>{
            if (!e.target.files || !e.target.files[0]) return;
            const rid = (typeof window !== 'undefined' ? (localStorage.getItem('recruiterIdentifier') || 'default') : 'default')
            const file = e.target.files[0]
            setUploading(true)
            setUploadError(null)
            try{
              const form = new FormData()
              form.append('file', file)
              if (docType) form.append('document_type', docType)
              const res = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates/${candidateId}/documents`, { method:'POST', body: form })
              if (res.ok) {
                const created = await res.json()
                setDocs(prev => [created, ...prev])
              } else {
                let detail = ''
                try { const j = await res.json(); detail = j?.detail || '' } catch {}
                setUploadError(detail ? `Upload failed (${res.status}): ${detail}` : `Upload failed (${res.status})`)
              }
            } finally{
              setUploading(false)
              // reset file input
              e.currentTarget.value = ''
            }
          }} disabled={uploading} />
        </div>
        {uploadError && <div style={{fontSize:'.75rem', color:'#b91c1c', marginBottom:8}}>{uploadError} · Check your recruiter in Settings → Admin → Recruiter.</div>}
        {docs.length === 0 ? (
          <div style={{fontSize:'.8rem', color:'#6b7280'}}>No documents.</div>
        ):(
          <ul style={{listStyle:'none', padding:0, margin:0, display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))', gap:8}}>
            {docs.map((d,idx)=> (
              <li key={d.id || idx} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8, background:'#ffffff'}}>
                <div style={{fontWeight:600, fontSize:'.85rem', color:'#111827'}}>{d.filename}</div>
                <div style={{fontSize:'.7rem', color:'#6b7280'}}>{d.document_type || 'file'}</div>
                {d.download_url && <a href={d.download_url} target="_blank" style={{fontSize:'.8rem', color:'#111827', textDecoration:'underline'}}>Download</a>}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Notes */}
  <section style={card}>
        <div style={sectionTitle}>Notes</div>
        <form onSubmit={async (e)=>{
          e.preventDefault();
          if (!newNote.trim()) return;
          setNoteSaving(true)
          try{
            const rid = (typeof window !== 'undefined' ? (localStorage.getItem('recruiterIdentifier') || 'default') : 'default')
            const headers: Record<string,string> = { ...(getAuthHeaders() as any), 'Content-Type':'application/json' }
            const body = { recruiter_identifier: rid, candidate_id: candidateId, content: newNote }
            const res = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates/${candidateId}/notes`, { method:'POST', headers, body: JSON.stringify(body)})
            if (res.ok) {
              const created = await res.json()
              setNotes(prev => [created, ...prev])
              setNewNote('')
            }
          } finally{
            setNoteSaving(false)
          }
        }} style={{display:'flex', gap:8, marginBottom:8}}>
          <input placeholder='Add a quick note…' value={newNote} onChange={e=>setNewNote(e.target.value)} style={{flex:1, padding:'.55rem .7rem', border:'1px solid #e5e7eb', borderRadius:8, fontSize:'.85rem', background:'#ffffff', color:'#111827', outline:'none'}} />
          <button disabled={noteSaving || !newNote.trim()} type='submit' style={{padding:'.5rem .85rem', background:'#16a34a', color:'#fff', border:'none', borderRadius:8, fontSize:'.8rem'}}>{noteSaving ? 'Saving…' : 'Add'}</button>
        </form>
        {notes.length === 0 ? (
          <div style={{fontSize:'.8rem', color:'#6b7280'}}>No notes.</div>
        ):(
      <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(260px,1fr))', gap:8}}>
            {notes.map((n,idx)=> (
        <div key={n.id || idx} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8, background:'#ffffff'}}>
                <div style={{fontSize:'.7rem', color:'#6b7280', marginBottom:4}}>{n.created_at ? new Date(n.created_at).toLocaleString(): ''}</div>
                {n.title && <div style={{fontWeight:700, fontSize:'.9rem', marginBottom:4, color:'#111827'}}>{n.title}</div>}
                <div style={{fontSize:'.9rem', color:'#111827'}}>{n.content}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Communications */}
      <section style={card}>
        <div style={sectionTitle}>Communications</div>
        {comms.length === 0 ? (
          <div style={{fontSize:'.75rem', opacity:.7}}>No communications.</div>
        ):(
  <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(260px,1fr))', gap:8}}>
            {comms.map((c,idx)=> (
        <div key={c.id || idx} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8, background:'#ffffff'}}>
        <div style={{fontSize:'.7rem', color:'#6b7280'}}>{c.communication_type || 'message'}</div>
                <div style={{fontWeight:600, fontSize:'.9rem', margin:'.25rem 0', color:'#111827'}}>{c.subject || '—'}</div>
                <div style={{fontSize:'.9rem', color:'#111827'}}>{c.content || '—'}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Interviews */}
      <section style={card}>
        <div style={sectionTitle}>Interviews</div>
        {interviews.length === 0 ? (
          <div style={{fontSize:'.75rem', opacity:.7}}>No interviews.</div>
        ):(
          <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(260px,1fr))', gap:8}}>
            {interviews.map((iv,idx)=> (
              <div key={iv.id || idx} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8, background:'#ffffff'}}>
                <div style={{fontSize:'.7rem', color:'#6b7280'}}>{iv.interview_type || 'interview'}</div>
                <div style={{fontWeight:600, fontSize:'.9rem', margin:'.25rem 0', color:'#111827'}}>{iv.title || '—'}</div>
                <div style={{fontSize:'.8rem', color:'#111827'}}>{iv.job_title || ''}</div>
                <div style={{fontSize:'.75rem', color:'#6b7280'}}>{iv.scheduled_at ? new Date(iv.scheduled_at).toLocaleString(): ''}</div>
                <div style={{fontSize:'.7rem', marginTop:4}}><Badge value={iv.status} /></div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Activity Timeline */}
      <section style={card}>
        <div style={sectionTitle}>Activity</div>
        {activities.length === 0 ? (
          <div style={{fontSize:'.75rem', opacity:.7}}>No activities yet.</div>
        ):(
          <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(260px,1fr))', gap:8}}>
            {activities.map(a => (
              <div key={a.id} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:8, background:'#ffffff'}}>
                <div style={{fontSize:'.7rem', color:'#6b7280'}}>{new Date(a.occurred_at).toLocaleString()}</div>
                <div style={{fontWeight:600, fontSize:'.9rem', margin:'.25rem 0', color:'#111827'}}>{a.title || a.type}</div>
                <div style={{fontSize:'.8rem', color:'#6b7280'}}>Job: {a.job_id ?? '—'} · Run: {a.run_id ?? '—'}</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

const th: React.CSSProperties = { padding: '.6rem .75rem', fontWeight: 600, fontSize: '.62rem', letterSpacing: '.08em', textTransform: 'uppercase', color:'#6b7280' }
const td: React.CSSProperties = { padding: '.6rem .75rem', verticalAlign: 'top', color:'#111827' }
const card: React.CSSProperties = { border:'1px solid #e5e7eb', borderRadius:10, padding:12, background:'#ffffff' }
const sectionTitle: React.CSSProperties = { fontWeight:700, fontSize:'.9rem', marginBottom:8 }

function Badge({ value }: { value?: string }){
  const color = (v?: string) => {
    switch(v){
      case 'screen': return '#4b5563' // neutral gray
      case 'interview': return '#6b7280' // neutral gray
  case 'offer': return '#16a34a' // keep green for success
  case 'hired': return '#16a34a' // align with success green; no teal/blue
      default: return '#4b5563'
    }
  }
  return (
    <span style={{ background: color(value), color: '#fff', padding: '.25rem .5rem', borderRadius: 12, fontSize: '.55rem', fontWeight: 600 }}>
      {value || 'unknown'}
    </span>
  )
}
