"use client";
import React, { useEffect, useState } from 'react';
import { getAuthHeaders } from '../lib/auth';

interface CandidateProfile {
  id: number; user_id: number; location: string; bio?: string|null; currency: string;
  created_at: string; updated_at: string; avatar_url?: string|null; resume_url?: string|null;
}

export default function CandidateHome(){
  const [profile, setProfile] = useState<CandidateProfile|null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);

  useEffect(()=>{
    let cancelled=false;
    async function load(){
      setLoading(true); setError(null);
      try {
        const res = await fetch('/api/v1/candidate/profile', { headers: { ...getAuthHeaders(), 'Accept':'application/json' }});
        if(!res.ok) throw new Error(`Profile load failed (${res.status})`);
        const data = await res.json();
        if(!cancelled) setProfile(data);
      } catch(e:any){ if(!cancelled) setError(e.message); }
      finally { if(!cancelled) setLoading(false); }
    }
    load();
    return ()=>{ cancelled=true; };
  },[]);

  return (
    <main style={{minHeight:'100vh', background:'#fff', color:'#111', fontFamily:'system-ui,Segoe UI,Roboto,sans-serif', padding:'32px 20px'}}>
      <div style={{maxWidth:860, margin:'0 auto'}}>
        <h1 style={{fontSize:32, fontWeight:800, margin:'0 0 10px'}}>Welcome Bhuvan</h1>
        <p style={{margin:'0 0 24px', fontSize:14, opacity:.75}}>Candidate view (read‑only). This account can only see this profile.</p>
        {loading && <div>Loading profile…</div>}
        {error && <div style={{color:'#b91c1c', fontSize:14}}>{error}</div>}
        {profile && !loading && (
          <div style={{border:'1px solid #e5e7eb', borderRadius:8, padding:20, background:'#fafafa'}}>
            <div style={{display:'flex', gap:20, alignItems:'flex-start', flexWrap:'wrap'}}>
              <div style={{width:90, height:90, borderRadius:8, background:'#e5e7eb', display:'flex', alignItems:'center', justifyContent:'center', fontWeight:600, fontSize:32}}>
                {(profile as any).full_name?.[0] || 'B'}
              </div>
              <div style={{flex:1, minWidth:240}}>
                <h2 style={{margin:'0 0 4px', fontSize:22}}>Bhuvan</h2>
                <div style={{fontSize:13, opacity:.7}}>Location: {profile.location || 'Unknown'}</div>
                <div style={{fontSize:13, opacity:.7}}>Currency: {profile.currency}</div>
                <div style={{marginTop:12, fontSize:14, lineHeight:1.5}}>{profile.bio || 'No bio yet.'}</div>
              </div>
            </div>
            <div style={{marginTop:24, display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(160px,1fr))', gap:12}}>
              <Metric label="Profile ID" value={String(profile.id)} />
              <Metric label="User ID" value={String(profile.user_id)} />
              <Metric label="Created" value={new Date(profile.created_at).toLocaleDateString()} />
              <Metric label="Updated" value={new Date(profile.updated_at).toLocaleDateString()} />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

function Metric({label, value}:{label:string; value:string}){
  return (
    <div style={{border:'1px solid #e5e7eb', background:'#fff', padding:'10px 12px', borderRadius:6}}>
      <div style={{fontSize:11, textTransform:'uppercase', letterSpacing:.5, opacity:.6, marginBottom:4}}>{label}</div>
      <div style={{fontSize:14, fontWeight:600}}>{value}</div>
    </div>
  );
}
