"use client";
import React, { useEffect, useState } from 'react';
import { getTokenFromCookie } from '../lib/auth';
import { useRouter } from 'next/navigation';

// Fixed recruiter mapping: email -> display name
const RECRUITER_DISPLAY: Record<string,string> = {
  'Sriman@svksystems.com': 'Sriman',
  'kumar@svksystems.com': 'Kumar',
  'Joseph@svksystems.com': 'Joseph',
  'Rajv@molinatek.com': 'Raj',
};

interface CandidateItem { id: number; name: string; recruiter_identifier: string; }
interface CandidateList { items: CandidateItem[]; total: number; }

// Detail profiles now load in dedicated page; dashboard only lists tiles

function decodeToken(): any | null {
  if (typeof document === 'undefined') return null;
  // Prefer unified auth cookie
  const token = getTokenFromCookie() || (()=>{
    const alt = document.cookie.match(/access_token=([^;]+)/);
    return alt ? decodeURIComponent(alt[1]) : null;
  })();
  if(!token) return null;
  try { return JSON.parse(atob(token.split('.')[1])); } catch { return null; }
}

export const dynamic = 'force-dynamic';

export default function RecruiterDashboard(){
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);
  const [data, setData] = useState<CandidateList|null>(null);
  const [rid, setRid] = useState<string|null>(null); // recruiter email (scoping key)
  const [displayName, setDisplayName] = useState<string>('');
  // no profile prefetch for Netflix tile style

  useEffect(()=> {
  const payload = decodeToken();
  const email = payload?.email || null;
    // fallback: backend tokens earlier may not include email; rely on custom claim if present
    // if absent we cannot fetch scoped list
    if(!email){ setError('Missing recruiter identifier (email) in token'); setLoading(false); return; }
    setRid(email);
    const dn = RECRUITER_DISPLAY[email] || email;
    setDisplayName(dn);
    try { localStorage.setItem('recruiterDisplayName', dn); } catch {}
  fetch(`/api/recruiter/${encodeURIComponent(email)}/candidates`, { headers: authHeaders() })
      .then(r=> r.ok? r.json(): Promise.reject(r))
  .then(json => { setData(json); try { localStorage.setItem('recruiterCandidates', JSON.stringify(json)); } catch {} })
      .catch(async r=> { try { const j = await r.json(); setError(j.detail || 'Failed'); } catch { setError('Failed'); } })
      .finally(()=> setLoading(false));
  }, []);

  function authHeaders(){
    const token = getTokenFromCookie() || (()=>{ const m = document.cookie.match(/access_token=([^;]+)/); return m? decodeURIComponent(m[1]): null; })();
    if(!token) return {} as Record<string,string>;
    return { 'Authorization': `Bearer ${token}`, 'Content-Type':'application/json' };
  }

  // Removed profile prefetch logic (handled in detail page)

  return (
    <main className="page" style={{padding:'30px 40px'}}>
      <h1 style={{fontSize:28, fontWeight:600, marginBottom:4}}>Recruiter Dashboard</h1>
      <p style={{opacity:.7, marginBottom:8}}>Your candidate list.</p>
      {rid && (
        <div style={{marginBottom:18, fontSize:14, fontWeight:500, display:'flex', alignItems:'center', gap:12}}>
          <span style={{padding:'4px 10px', border:'1px solid var(--color-border)', borderRadius:20, background:'var(--color-accent-soft)'}}>
            Active Recruiter: <strong>{displayName}</strong>
          </span>
          <span style={{fontSize:11, opacity:.55}}>({rid})</span>
        </div>
      )}
      {loading && <div>Loading...</div>}
      {error && <div style={{color:'#d14343', marginBottom:12}}>{error}</div>}
      {!loading && !error && (
        <div className="tile-grid">
          {data?.items.map(c=> (
            <button
              key={c.id}
              className="candidate-tile"
              onClick={()=> {
                try { localStorage.setItem('activeCandidate', JSON.stringify({id:c.id, name:c.name})); localStorage.setItem('recruiterIdentifier', rid||''); } catch {}
                const qp = new URLSearchParams({ candidateId: String(c.id), candidateName: c.name });
                router.push(`/dashboard?${qp.toString()}`);
              }}
            >
              <div className="candidate-initial">{c.name.charAt(0).toUpperCase()}</div>
              <div className="candidate-meta">
                <div className="candidate-name">{c.name}</div>
                <div className="candidate-action">Start</div>
              </div>
            </button>
          ))}
          {!data?.items.length && <div style={{opacity:.7}}>No candidates.</div>}
        </div>
      )}
    </main>
  );
}
