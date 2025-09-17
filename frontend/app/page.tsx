"use client";
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getTokenFromCookie } from './lib/auth';

export default function AdminHome(){
  const router = useRouter();
  const [role, setRole] = useState<string|null>(null);
  useEffect(()=>{
    try {
      const tok = getTokenFromCookie();
      if (!tok) return;
      const parts = tok.split('.');
      if (parts.length===3){
        const payload = JSON.parse(atob(parts[1].replace(/-/g,'+').replace(/_/g,'/')));
        if (payload.role) {
          setRole(payload.role);
          // If recruiter role, immediately send to recruiter dashboard, skip selector
          if (payload.role === 'recruiter') {
            router.replace('/recruiter');
            return; // skip further rendering logic
          }
        }
      }
    } catch(e){ /* ignore */ }
  },[router]);
  const isCandidate = role === 'candidate';
  return (
    <main style={{minHeight:'100vh', display:'flex', flexDirection:'column', padding:'40px 32px 60px'}}>
      <div className="admin-hero">
        <h1>{isCandidate? 'Candidate Access':'Admin Access'}</h1>
        <p>{isCandidate? 'Select your candidate profile' : 'Select a profile to continue'}</p>
      </div>
      <div className="profile-grid">
        {!isCandidate && (
        <button className="profile-tile" onClick={()=> router.push('/admin/recruiter')}>
          <div className="profile-avatar" aria-label="Recruiter">R</div>
          <div className="profile-name">RECRUITER</div>
          <div className="profile-extra">Talent ops</div>
        </button>)}
        <button className="profile-tile" onClick={()=> isCandidate? router.push('/candidate'):null} disabled={!isCandidate} style={!isCandidate? {opacity:.35, cursor:'not-allowed'}: undefined}>
          <div className="profile-avatar" style={{background:'linear-gradient(135deg,#0d9488,#14b8a6)'}} aria-label="Candidate">C</div>
          <div className="profile-name">CANDIDATE</div>
          <div className="profile-extra">{isCandidate? 'Your portal':'Disabled'}</div>
        </button>
      </div>
      <div className="admin-footer">
        {!isCandidate && <Link href="/dashboard" style={{textDecoration:'none', color:'var(--color-accent)'}}>Legacy Dashboard</Link>}
      </div>
    </main>
  );
}
