"use client";
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useState, useCallback } from 'react';
import { getApiBase } from '../../lib/apiBase';
import { getAuthHeaders } from '../../lib/auth';

// Simple deterministic gradient palette derived from name hash
function gradientForName(name:string){
  // Pastel, smooth gradients aligned with Admin Access palette
  const palettes = [
    ['#5d92ff','#9ec2ff'], // soft blue
    ['#60a5fa','#93c5fd'], // sky
    ['#8b5cf6','#c4b5fd'], // purple
    ['#22d3ee','#a5f3fc'], // cyan
    ['#34d399','#a7f3d0'], // emerald
    ['#f59e0b','#fbd38d'], // amber
    ['#f472b6','#fbcfe8'], // pink
    ['#14b8a6','#99f6e4'], // teal
    ['#67e8f9','#a5f3fc'], // light aqua
    ['#93c5fd','#bfdbfe']  // pale sky
  ];
  let hash=0; for(let i=0;i<name.length;i++){ hash = (hash*31 + name.charCodeAt(i)) >>> 0; }
  const pair = palettes[ hash % palettes.length ];
  return `linear-gradient(135deg,${pair[0]},${pair[1]})`;
}

// Fixed recruiter directory per requirement: only these four recruiter profiles
const ALLOWED_RECRUITERS: { email: string; display: string }[] = [
  { email: 'Sriman@svksystems.com', display: 'Sriman' },
  { email: 'kumar@svksystems.com', display: 'Kumar' },
  { email: 'Joseph@svksystems.com', display: 'Joseph' },
  { email: 'Rajv@molinatek.com', display: 'Raj' },
];

export default function RecruiterLevel(){
  const router = useRouter();
  const [recruiterId, setRecruiterId] = useState(''); // stores selected recruiter email
  const [candidateName, setCandidateName] = useState('');
  const [candidates, setCandidates] = useState<{id:number; name:string}[]>([]);
  const [pendingLocal, setPendingLocal] = useState<string[]>([]); // names captured before recruiter set
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string|undefined>();

  useEffect(()=>{
    const stored = localStorage.getItem('recruiterIdentifier') || '';
    // Only restore if still in allowed list (in case list changed)
    if(ALLOWED_RECRUITERS.some(r=> r.email === stored)) {
      setRecruiterId(stored);
    } else {
      localStorage.removeItem('recruiterIdentifier');
    }
  },[]);

  const apiBase = getApiBase();

  const fetchCandidates = useCallback(async (rid:string)=>{
    if(!rid) return;
    setLoading(true); setError(undefined);
    try {
      const res = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates`, {
        headers: { ...getAuthHeaders() }
      });
      if(!res.ok){ throw new Error('Failed to load'); }
      const data = await res.json();
      setCandidates(data.items || []);
    } catch(e:any){ setError(e.message); }
    finally { setLoading(false); }
  },[apiBase]);

  useEffect(()=>{ if(recruiterId) fetchCandidates(recruiterId); },[recruiterId, fetchCandidates]);

  const selectRecruiter = async (email:string) => {
    if(email === recruiterId) return; // no change
    localStorage.setItem('recruiterIdentifier', email);
    setRecruiterId(email);
    // flush any locally buffered names
    if(pendingLocal.length){
      for(const n of pendingLocal){
        await persistCandidate(n, email);
      }
      setPendingLocal([]);
      localStorage.removeItem('pendingCandidateNames');
    }
    fetchCandidates(email);
  };

  const persistCandidate = async (raw:string, overrideRecruiter?:string) => {
    const name = raw.trim();
    if(!name) return;
    const rid = overrideRecruiter || recruiterId;
    if(!rid){
      setPendingLocal(prev => {
        if(prev.includes(name)) return prev;
        const next = [name, ...prev];
        localStorage.setItem('pendingCandidateNames', JSON.stringify(next));
        return next;
      });
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(`${apiBase}/recruiter/${encodeURIComponent(rid)}/candidates`,{
        method:'POST', headers:{'Content-Type':'application/json', ...getAuthHeaders()},
        body: JSON.stringify({ recruiter_identifier: rid, name })
      });
      if(!res.ok) return; // silent fail
      const data = await res.json();
      setCandidates(prev => prev.some(c=>c.id===data.id)? prev : [data, ...prev]);
    } finally { setSaving(false); }
  };

  const addCandidate = async () => {
    const tokens = candidateName.split(/[,\n]/).map(t=> t.trim()).filter(Boolean);
    if(tokens.length===0) return;
    setCandidateName('');
    for(const t of tokens){ await persistCandidate(t); }
  };

  useEffect(()=>{
    // load pending local names if any
    const raw = localStorage.getItem('pendingCandidateNames');
    if(raw){
      try { setPendingLocal(JSON.parse(raw)||[]); } catch {}
    }
  },[]);

  const deleteCandidate = async (id:number) => {
    if(!recruiterId) return;
    const prev = candidates;
    setCandidates(candidates.filter(c=> c.id!==id));
  const res = await fetch(`${apiBase}/recruiter/${encodeURIComponent(recruiterId)}/candidates/${id}`, { method:'DELETE', headers: { ...getAuthHeaders() } });
    if(!res.ok){
      // rollback on error
      setCandidates(prev);
    }
  };

  return (
    <main style={{minHeight:'100vh', display:'flex', flexDirection:'column', padding:'40px 32px 80px', gap:32}}>
      <div className="admin-hero" style={{marginBottom:8}}>
        <h1>Recruiter Space</h1>
        <p>Manage candidate list & navigate tools</p>
      </div>
      <div style={{textAlign:'center'}}>
        <Link href="/" className="badge-link" style={{textDecoration:'none'}}>← Admin</Link>
      </div>
      <section style={{display:'grid', gap:24, gridTemplateColumns:'repeat(auto-fit,minmax(260px,1fr))'}}>
  <div style={{border:'1px solid var(--color-border)', borderRadius:12, padding:20, background:'var(--color-bg-alt)'}}>
          <h2 style={{marginTop:0, fontSize:20}}>Recruiter Identity</h2>
            <p style={{fontSize:13, opacity:.8, marginTop:-4}}>Set a simple identifier (email or username) to scope your candidate names.</p>
            <div style={{display:'flex', gap:8, marginTop:12}}>
              <div style={{display:'flex', flexWrap:'wrap', gap:10}}>
                {ALLOWED_RECRUITERS.map(r=>{
                  const active = r.email === recruiterId;
                  return (
                    <button
                      key={r.email}
                      onClick={()=> selectRecruiter(r.email)}
                      style={{
                        padding:'8px 14px',
                        borderRadius:30,
                        border: active? '2px solid #5d92ff':'1px solid var(--color-border)',
                        background: active? 'linear-gradient(135deg,#5d92ff,#9ec2ff)':'#fff',
                        color: active? '#fff':'var(--color-text)',
                        fontWeight:600,
                        cursor:'pointer',
                        boxShadow: active? '0 2px 4px rgba(0,0,0,0.12)':'none'
                      }}
                      title={r.email}
                    >{r.display}</button>
                  );
                })}
              </div>
            </div>
            {recruiterId && (
              <div style={{marginTop:18}}>
                <div style={{fontSize:11, letterSpacing:'.08em', textTransform:'uppercase', color:'var(--color-text-soft)', marginBottom:10}}>Active Recruiter</div>
                <div className="profile-grid" style={{margin:0, gridTemplateColumns:'repeat(auto-fit,minmax(120px,1fr))', gap:20}}>
                  <div className="profile-tile" title={recruiterId} style={{cursor:'default'}}>
                    <div className="profile-avatar" style={{width:120, height:120, fontSize:'2.1rem', background: gradientForName(recruiterId || 'R')}}>
                      {(() => {
                        const found = ALLOWED_RECRUITERS.find(r=> r.email===recruiterId);
                        return (found?.display || recruiterId).charAt(0).toUpperCase();
                      })()}
                    </div>
                    <div className="profile-name" style={{maxWidth:130, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{ALLOWED_RECRUITERS.find(r=> r.email===recruiterId)?.display || recruiterId}</div>
                    <div className="profile-extra" style={{fontSize:'.5rem'}}>Recruiter</div>
                  </div>
                </div>
              </div>
            )}
        </div>
  <div style={{border:'1px solid var(--color-border)', borderRadius:12, padding:20, background:'var(--color-bg-alt)', display:'flex', flexDirection:'column'}}>
          <h2 style={{marginTop:0, fontSize:20}}>Candidate Names</h2>
          {!recruiterId && <p style={{fontSize:13, opacity:.7}}>Set recruiter identity first.</p>}
          {recruiterId && (
            <>
              <div style={{display:'flex', gap:8}}>
                <input
                  value={candidateName}
                  onChange={e=> setCandidateName(e.target.value)}
                  placeholder={recruiterId ? 'Type name, press Enter or comma to add multiple' : 'Set recruiter first, names will buffer'}
                  style={{flex:1, padding:'8px 10px', borderRadius:8, border:'1px solid var(--color-border)', background:'#fff', color:'var(--color-text)'}}
                  onKeyDown={e=> {
                    if(e.key==='Enter' || e.key===','){
                      e.preventDefault();
                      addCandidate();
                    }
                  }}
                  onBlur={()=> addCandidate()}
                />
                <button onClick={addCandidate} disabled={saving || !candidateName.trim()} style={{padding:'8px 14px', borderRadius:8, background:'linear-gradient(135deg,#8b5cf6,#c4b5fd)', border:'none', color:'#fff', fontWeight:600}}>{saving? '...':'Add'}</button>
              </div>
              <div style={{marginTop:14, fontSize:12, opacity:.9}}>
                {loading? 'Loading...': (
                  <span style={{display:'inline-block', padding:'2px 10px', borderRadius:999, background:'var(--color-accent-soft)', border:'1px solid var(--color-border)', color:'var(--color-text-soft)'}}>
                    {candidates.length} stored
                  </span>
                )}
              </div>
              {error && <div style={{color:'#f87171', fontSize:12, marginTop:6}}>{error}</div>}
              {(!recruiterId && pendingLocal.length>0) && <div style={{marginTop:8, fontSize:11, color:'var(--color-accent)'}}>{pendingLocal.length} buffered (will save when recruiter set)</div>}
              <div style={{marginTop:18, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase', color:'var(--color-text-soft)'}}>{candidates.length} profiles</div>
              <div className="profile-grid" style={{margin: '12px 0 8px', gridTemplateColumns:'repeat(auto-fit,minmax(120px,1fr))', gap:28, maxHeight:320, overflowY:'auto', padding:'4px 6px'}}>
                {candidates.map(c=> {
                  const initial = c.name.trim().charAt(0).toUpperCase() || '?';
                  return (
                    <div
                      key={c.id}
                      className="profile-tile"
                      title={c.name}
                      style={{whiteSpace:'normal', position:'relative', cursor:'pointer'}}
                      onClick={()=> router.push(`/dashboard?candidateId=${c.id}&candidateName=${encodeURIComponent(c.name)}`)}
                    >
                      <div className="profile-avatar" style={{background: gradientForName(c.name), width:120, height:120, fontSize:'2.2rem'}}>{initial}</div>
                      <div className="profile-name" style={{maxWidth:130, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{c.name}</div>
                      <div className="profile-extra" style={{fontSize:'.5rem'}}>Candidate</div>
                      <button
                        onClick={(e)=> { e.stopPropagation(); deleteCandidate(c.id); }}
                        style={{position:'absolute', top:4, right:4, background:'rgba(255,255,255,0.85)', border:'1px solid var(--color-border)', borderRadius:8, padding:'2px 6px', fontSize:10, cursor:'pointer'}}
                      >✕</button>
                    </div>
                  );
                })}
                {(!loading && candidates.length===0) && (
                  <div style={{fontSize:12, opacity:.6, gridColumn:'1 / -1', textAlign:'center'}}>No candidates yet.</div>
                )}
              </div>
            </>
          )}
        </div>
  <div style={{border:'1px solid var(--color-border)', borderRadius:12, padding:20, background:'var(--color-bg-alt)'}}>
          <h2 style={{marginTop:0, fontSize:20}}>Navigation</h2>
      <div className="profile-grid" style={{marginTop:12, '--grid-min':'140px'} as any}>
            <button className="profile-tile" onClick={()=> router.push('/admin/recruiter/candidate')}>
        <div className="profile-avatar" style={{background:'linear-gradient(135deg,#8b5cf6,#c4b5fd)'}} aria-label="Candidate">C</div>
              <div className="profile-name">CANDIDATE</div>
              <div className="profile-extra">Automation</div>
            </button>
          </div>
        </div>
      </section>
      <div className="admin-footer" style={{marginTop:'auto'}}>
        <Link href="/dashboard" style={{textDecoration:'none', color:'var(--color-accent)'}}>Legacy Dashboard</Link>
      </div>
    </main>
  );
}
