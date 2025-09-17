"use client"
import React, { useEffect, useState } from 'react'
import { getAuthHeaders } from '../lib/auth'

type Job = {
  id: string
  title: string
  location?: string
  status?: string
  updated_at?: string
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string|null>(null)

  useEffect(() => {
    let cancelled = false
  async function load() {
      try {
    const headers: Record<string,string> = { ...(getAuthHeaders() as any), 'Accept': 'application/json' }
    const base = process.env.NEXT_PUBLIC_API_BASE_URL || (typeof window === 'undefined' ? 'http://localhost:8080/api' : '/api')
    const res = await fetch(`${base}/v1/candidate/jobs?limit=25`, { cache: 'no-store', headers })
        if (!res.ok) throw new Error('Failed to load jobs')
        const data = await res.json()
        if (!cancelled) setJobs(data.jobs || data.items || [])
      } catch (e:any) {
        if (!cancelled) {
          setError(e.message)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: '1.1rem', margin: 0 }}>Jobs</h1>
        <button style={{ background: '#2563eb', color: '#fff', border: 'none', padding: '.5rem .85rem', borderRadius: 6, fontSize: '.75rem', cursor: 'pointer' }}>New Job</button>
      </div>
      {error && (
        <div style={{ fontSize: '.65rem', color: '#f87171' }}>Error: {error}</div>
      )}
      <div style={{ overflowX: 'auto', border: '1px solid #24313e', borderRadius: 8 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.75rem' }}>
          <thead style={{ background: '#1c232c', textAlign: 'left' }}>
            <tr>
              <th style={th}>Title</th>
              <th style={th}>Location</th>
              <th style={th}>Status</th>
              <th style={th}>Updated</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={4} style={{ padding: '1rem', textAlign: 'center' }}>Loading...</td></tr>
            )}
            {!loading && jobs.map(j => (
              <tr key={j.id} style={{ borderTop: '1px solid #24313e' }}>
                <td style={td}>{j.title}</td>
                <td style={td}>{j.location || '—'}</td>
                <td style={td}><StatusBadge value={j.status} /></td>
                <td style={td}>{j.updated_at ? new Date(j.updated_at).toLocaleDateString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const th: React.CSSProperties = { padding: '.6rem .75rem', fontWeight: 600, fontSize: '.6rem', letterSpacing: '.08em', textTransform: 'uppercase' }
const td: React.CSSProperties = { padding: '.55rem .75rem', verticalAlign: 'top' }

function StatusBadge({ value }: { value?: string }) {
  const color = (v?: string) => {
    switch(v) {
      case 'open': return '#16a34a'
      case 'screening': return '#2563eb'
      case 'closed': return '#64748b'
      default: return '#475569'
    }
  }
  return (
    <span style={{ background: color(value), color: '#fff', padding: '.25rem .5rem', borderRadius: 12, fontSize: '.55rem', fontWeight: 600 }}>
      {value || 'unknown'}
    </span>
  )
}
