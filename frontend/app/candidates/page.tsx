"use client"
import React, { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { getApiBase } from '../lib/apiBase'
import { getTokenFromCookie } from '../lib/auth'
import { Plus, Search as SearchIcon, Trash2, ExternalLink, X, Loader2 } from 'lucide-react'

interface CandidateRow { id: number; name: string; created_at?: string; recruiter_identifier?: string }

function decodeToken(): any | null {
  if (typeof document === 'undefined') return null
  const token = getTokenFromCookie() || (()=>{ const m = document.cookie.match(/access_token=([^;]+)/); return m? decodeURIComponent(m[1]) : null })();
  if(!token) return null
  try { return JSON.parse(atob(token.split('.')[1])) } catch { return null }
}

export const dynamic = 'force-dynamic';

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<CandidateRow[]>([])
  const [loadedFromCache, setLoadedFromCache] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string|null>(null)
  const [showModal, setShowModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [search, setSearch] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [deletingId, setDeletingId] = useState<number|null>(null)
  const apiBase = getApiBase()
  const [isAdmin, setIsAdmin] = useState(false)
  const recruiterId = useMemo(()=> (typeof window !== 'undefined' ? (localStorage.getItem('recruiterIdentifier') || 'default') : 'default'), [])
  const [allRecruiters, setAllRecruiters] = useState<string[]>([])

  function authHeaders(): Record<string,string> {
    const token = getTokenFromCookie() || (()=>{ const m = document.cookie.match(/access_token=([^;]+)/); return m? decodeURIComponent(m[1]) : null })();
    return token ? { 'Authorization': `Bearer ${token}` } : {}
  }

  async function load(listSearch: string = '') {
    setLoading(true)
    setError(null)
    try {
      const baseUrl = isAdmin ? `${apiBase}/recruiter/admin/candidates` : `${apiBase}/recruiter/${encodeURIComponent(recruiterId)}/candidates`
      const url = new URL(baseUrl)
      url.searchParams.set('limit', '500')
      if (listSearch.trim()) url.searchParams.set('search', listSearch.trim())
      const res = await fetch(url.toString(), { cache:'no-store', headers: authHeaders() })
      if (!res.ok) throw new Error('Failed to load candidates')
      const data = await res.json()
      const items = (data?.items || []).map((c:any)=>({ id:c.id, name:c.name, created_at:c.created_at, recruiter_identifier: c.recruiter_identifier })) as CandidateRow[]
      setCandidates(items)
    } catch (e:any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }
  // Pre-populate from recruiterCandidates cache written by /recruiter page
  useEffect(() => {
    try {
      const raw = localStorage.getItem('recruiterCandidates')
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed && Array.isArray(parsed.items)) {
          setCandidates(parsed.items.map((c:any)=>({ id:c.id, name:c.name, created_at:c.created_at, recruiter_identifier: c.recruiter_identifier })))
          setLoadedFromCache(true)
        }
      }
    } catch {}
    const payload = decodeToken();
    const roles: string[] = payload?.roles || payload?.role ? [payload.role].filter(Boolean) : []
    if (roles.includes('admin')) {
      setIsAdmin(true)
      // Load recruiter list from localStorage directory if exists
      try {
        const rd = localStorage.getItem('RecruiterDirectory')
        if (rd) {
          const parsed = JSON.parse(rd)
          if (Array.isArray(parsed)) setAllRecruiters(parsed)
        }
      } catch {}
    }
    // Always still fetch fresh list (will reconcile cache)
    load('')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Keep localStorage cache in sync
  useEffect(() => {
    try {
  const payload = { items: candidates, total: candidates.length }
      localStorage.setItem('recruiterCandidates', JSON.stringify(payload))
    } catch {}
  }, [candidates])

  // Debounced search
  useEffect(() => {
    const t = setTimeout(() => {
      setSearchTerm(search)
      load(search)
    }, 300)
    return () => clearTimeout(t)
  }, [search])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    setCreating(true)
    setError(null)
    try {
      const headers: Record<string,string> = { 'Content-Type':'application/json', ...authHeaders() }
      const body = { name: newName.trim() }
      let url = `${apiBase}/recruiter/${encodeURIComponent(recruiterId)}/candidates`
      if (isAdmin && selectedRecruiterForCreate) {
        // Use admin endpoint (query params)
        const u = new URL(`${apiBase}/recruiter/admin/candidates`)
        u.searchParams.set('recruiter_identifier', selectedRecruiterForCreate)
        u.searchParams.set('name', newName.trim())
        url = u.toString()
        // Convert to GET with params? We defined POST with query params; still send POST
        const res = await fetch(url, { method:'POST', headers })
        if (!res.ok) throw new Error('Create failed')
        const created = await res.json()
        setCandidates(prev => [{ id: created.id, name: created.name, created_at: created.created_at, recruiter_identifier: created.recruiter_identifier }, ...prev])
        setShowModal(false)
        setNewName('')
        return
      }
      const res = await fetch(url, { method:'POST', headers, body: JSON.stringify(body) })
      if (!res.ok) throw new Error('Create failed')
      const created = await res.json()
      setCandidates(prev => [{ id: created.id, name: created.name, created_at: created.created_at, recruiter_identifier: recruiterId }, ...prev])
      setShowModal(false)
      setNewName('')
    } catch (e:any) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  async function removeCandidate(id: number) {
    if (!confirm('Delete this candidate? This cannot be undone.')) return
    setDeletingId(id)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/recruiter/${encodeURIComponent(recruiterId)}/candidates/${id}`, { method:'DELETE', headers: authHeaders() })
      if (!res.ok) throw new Error('Delete failed')
      setCandidates(prev => prev.filter(c => c.id !== id))
    } catch (e:any) {
      setError(e.message)
    } finally {
      setDeletingId(null)
    }
  }

  async function reassignCandidate(id:number, target:string){
    try {
      const u = new URL(`${apiBase}/recruiter/admin/candidates/${id}`)
      u.searchParams.set('new_recruiter_identifier', target)
      const res = await fetch(u.toString(), { method:'PATCH', headers: authHeaders() })
      if(!res.ok) throw new Error('Reassign failed')
      const updated = await res.json()
      setCandidates(prev => prev.map(c=> c.id===id? {...c, recruiter_identifier: updated.recruiter_identifier}: c))
    } catch(e:any){ setError(e.message) }
  }

  const [selectedRecruiterForCreate, setSelectedRecruiterForCreate] = useState('')

  return (
    <div className="card" style={{gap:16}}>
      {/* Header */}
  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <div>
      <h1 style={{ fontSize:'1.2rem', margin:0 }}>Candidates</h1>
      <div style={{ fontSize:'.8rem', color:'var(--color-text-soft)', marginTop:4 }}>Manage your talent pool and jump into each profile.{loadedFromCache && ' (cached)'} {isAdmin && '(admin view)'}</div>
        </div>
        <div style={{ display:'flex', gap:12, alignItems:'center' }}>
      <div style={{ display:'inline-flex', alignItems:'center', gap:8, background:'var(--color-bg-elevated)', border:'1px solid var(--color-border)', borderRadius:8, padding:'.4rem .6rem' }}>
            <SearchIcon size={16} color="#6b7280" />
            <input
              placeholder="Search candidates"
              value={search}
              onChange={e=>setSearch(e.target.value)}
        style={{ background:'transparent', border:'none', outline:'none', color:'var(--color-text)', fontSize:'.85rem', width:220 }}
            />
          </div>
      <button onClick={()=> setShowModal(true)} className="btn">
            <Plus size={16} />
            <span>New Candidate</span>
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div style={{ background:'#fef2f2', border:'1px solid #fecaca', color:'#b91c1c', padding:10, borderRadius:8, fontSize:'.75rem' }}>Error: {error}</div>
      )}

      {/* Table or empty/skeleton */}
  <div className="card" style={{padding:12}}>
        {loading ? (
          <SkeletonTable />
        ) : candidates.length === 0 ? (
          <EmptyState onCreate={()=> setShowModal(true)} />
        ) : (
          <div style={{ overflowX:'auto' }}>
            <table style={table}>
              <thead>
                <tr>
                  <th style={th}>Name</th>
                  {isAdmin && <th style={th}>Recruiter</th>}
                  <th style={th}>Created</th>
                  <th style={{...th, textAlign:'right'}}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => (
                  <tr key={c.id} style={tr}>
                    <td style={td}>
                      <div style={{display:'flex', alignItems:'center', gap:8}}>
                        <div style={{ width:28, height:28, borderRadius:6, background:'var(--color-accent-soft)', display:'grid', placeItems:'center', fontSize:'.8rem', fontWeight:700, color:'var(--color-text)', border:'1px solid var(--color-border)' }}>{(c.name||'?').slice(0,1).toUpperCase()}</div>
                        <Link href={`/candidates/${c.id}`} style={{ color:'var(--color-text)', textDecoration:'none', fontWeight:600 }}>{c.name}</Link>
                      </div>
                    </td>
                    {isAdmin && (
                      <td style={td}>
                        <select value={c.recruiter_identifier||''} onChange={e=> reassignCandidate(c.id, e.target.value)} className="input" style={{padding:'.45rem .55rem'}}>
                          <option value="">(none)</option>
                          {allRecruiters.map(r=> <option key={r} value={r}>{r}</option>)}
                        </select>
                      </td>
                    )}
                    <td style={td}>{c.created_at ? new Date(c.created_at).toLocaleString() : '—'}</td>
                    <td style={{...td, textAlign:'right'}}>
                      <div style={{display:'inline-flex', gap:8}}>
                        <Link href={`/candidates/${c.id}`} className="btn outline" style={{width:32, height:32, padding:0, justifyContent:'center'}} title="Open">
                          <ExternalLink size={16} />
                        </Link>
                        <button onClick={()=> removeCandidate(c.id)} className="btn outline" style={{width:32, height:32, padding:0, justifyContent:'center', ...(deletingId===c.id? {opacity:.6}: {}) , borderColor:'#fecaca', color:'#b91c1c', background:'#fef2f2'}} title="Delete" disabled={deletingId===c.id}>
                          {deletingId===c.id ? <Loader2 size={16} className="spin" /> : <Trash2 size={16} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showModal && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,.6)', display:'grid', placeItems:'center', padding:16, zIndex:50 }} onClick={()=> setShowModal(false)}>
          <div style={{ width:'100%', maxWidth:440, background:'var(--color-bg-elevated)', border:'1px solid var(--color-border)', borderRadius:12, padding:16, color:'var(--color-text)' }} onClick={e=> e.stopPropagation()}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
              <div style={{fontWeight:700}}>Create Candidate</div>
              <button onClick={()=> setShowModal(false)} className="btn outline" style={{width:32, height:32, padding:0, justifyContent:'center'}}>
                <X size={16} />
              </button>
            </div>
            <form onSubmit={submit} style={{display:'flex', flexDirection:'column', gap:12}}>
              <label style={{ fontSize:'.75rem', color:'var(--color-text-soft)' }}>Name</label>
              <input
                autoFocus
                placeholder="Full name"
                value={newName}
                onChange={e=>setNewName(e.target.value)}
                className="input"
              />
              {isAdmin && (
                <>
                  <label style={{ fontSize:'.75rem', color:'var(--color-text-soft)' }}>Recruiter</label>
                  <select value={selectedRecruiterForCreate} onChange={e=> setSelectedRecruiterForCreate(e.target.value)} className="input" style={{padding:'.5rem .55rem'}} required>
                    <option value="">Select recruiter</option>
                    {allRecruiters.map(r=> <option key={r} value={r}>{r}</option>)}
                  </select>
                </>
              )}
              <div style={{display:'flex', justifyContent:'flex-end', gap:8, marginTop:4}}>
                <button type='button' onClick={()=> setShowModal(false)} className="btn outline">Cancel</button>
                <button type='submit' disabled={creating || !newName.trim()} className="btn">
                  {creating && <Loader2 size={16} className='spin' />}<span>{creating? 'Creating...' : 'Create'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// Styles
const pageWrap: React.CSSProperties = { display:'flex', flexDirection:'column', gap:16, background:'#ffffff', border:'1px solid #e5e7eb', borderRadius:10, padding:12, color:'#111827' }
const headerRow: React.CSSProperties = { display:'flex', justifyContent:'space-between', alignItems:'center' }
const title: React.CSSProperties = { fontSize:'1.2rem', margin:0, color:'#111827' }
const subtitle: React.CSSProperties = { fontSize:'.8rem', color:'#6b7280', marginTop:4 }
const card: React.CSSProperties = { border:'1px solid #e5e7eb', background:'#ffffff', borderRadius:10, padding:12 }
const table: React.CSSProperties = { width:'100%', borderCollapse:'collapse', fontSize:'.8rem' }
const th: React.CSSProperties = { padding: '0.7rem .8rem', fontWeight: 600, fontSize: '.62rem', letterSpacing: '.08em', textTransform: 'uppercase', color:'#6b7280', textAlign:'left' }
const tr: React.CSSProperties = { borderTop:'1px solid #e5e7eb' }
const td: React.CSSProperties = { padding: '.7rem .8rem', verticalAlign: 'middle', color:'#111827' }
const nameLink: React.CSSProperties = { color:'#111827', textDecoration:'none', fontWeight:600 }
const avatar: React.CSSProperties = { width:28, height:28, borderRadius:6, background:'#f3f4f6', display:'grid', placeItems:'center', fontSize:'.8rem', fontWeight:700, color:'#111827', border:'1px solid #e5e7eb' }
const primaryBtn: React.CSSProperties = { display:'inline-flex', gap:8, alignItems:'center', background:'#111827', color:'#ffffff', border:'1px solid #111827', padding:'.5rem .85rem', borderRadius:8, fontSize:'.8rem', cursor:'pointer' }
const secondaryBtn: React.CSSProperties = { display:'inline-flex', gap:8, alignItems:'center', background:'#ffffff', color:'#111827', border:'1px solid #e5e7eb', padding:'.45rem .8rem', borderRadius:8, fontSize:'.8rem', cursor:'pointer' }
const iconBtn: React.CSSProperties = { display:'inline-flex', alignItems:'center', justifyContent:'center', width:32, height:32, borderRadius:8, border:'1px solid #e5e7eb', background:'#ffffff', color:'#374151' }
const dangerIconBtn: React.CSSProperties = { ...iconBtn, color:'#b91c1c', border:'1px solid #fecaca', background:'#fef2f2' }
const ghostIconBtn: React.CSSProperties = { ...iconBtn, background:'transparent', border:'none' }
const searchWrap: React.CSSProperties = { display:'inline-flex', alignItems:'center', gap:8, background:'#ffffff', border:'1px solid #e5e7eb', borderRadius:8, padding:'.4rem .6rem' }
const searchInput: React.CSSProperties = { background:'transparent', border:'none', outline:'none', color:'#111827', fontSize:'.85rem', width:220 }
const errorBanner: React.CSSProperties = { background:'#fef2f2', border:'1px solid #fecaca', color:'#b91c1c', padding:10, borderRadius:8, fontSize:'.75rem' }
const modalOverlay: React.CSSProperties = { position:'fixed', inset:0, background:'rgba(0,0,0,.6)', display:'grid', placeItems:'center', padding:16, zIndex:50 }
const modal: React.CSSProperties = { width:'100%', maxWidth:440, background:'#ffffff', border:'1px solid #e5e7eb', borderRadius:12, padding:16, color:'#111827' }
const modalHeader: React.CSSProperties = { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }
const label: React.CSSProperties = { fontSize:'.75rem', color:'#374151' }
const input: React.CSSProperties = { padding:'.55rem .7rem', background:'#ffffff', border:'1px solid #e5e7eb', borderRadius:8, fontSize:'.85rem', color:'#111827' }
const selectStyle: React.CSSProperties = { ...input, padding:'.5rem .55rem', cursor:'pointer' }

function SkeletonTable() {
  const rows = new Array(6).fill(0)
  return (
    <div style={{overflowX:'auto'}}>
      <table style={table}>
        <thead>
          <tr>
            <th style={th}>Name</th>
            <th style={th}>Created</th>
            <th style={{...th, textAlign:'right'}}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((_,i)=> (
            <tr key={i} style={tr}>
              <td style={td}><div style={skeleton(180)} /></td>
              <td style={td}><div style={skeleton(140)} /></td>
              <td style={{...td, textAlign:'right'}}><div style={{...skeleton(80), marginLeft:'auto'}} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function EmptyState({ onCreate }: { onCreate: ()=>void }){
  return (
    <div style={{ display:'grid', placeItems:'center', padding:'3rem 1rem', textAlign:'center', color:'#6b7280' }}>
      <div style={{fontSize:'1rem', color:'#111827', marginBottom:8}}>No candidates found</div>
      <div style={{fontSize:'.85rem', marginBottom:16}}>Create your first candidate to get started.</div>
      <button onClick={onCreate} style={primaryBtn}><Plus size={16} /><span>New Candidate</span></button>
    </div>
  )
}

function skeleton(width:number): React.CSSProperties {
  return { width, height:10, borderRadius:6, background:'linear-gradient(90deg, #f3f4f6 0%, #e5e7eb 50%, #f3f4f6 100%)', backgroundSize:'200% 100%', animation:'shine 1.2s linear infinite' } as React.CSSProperties
}
