"use client";
import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getTokenFromCookie } from '../../../lib/auth';

interface Profile {
  id: number;
  candidate_id: number;
  recruiter_identifier: string;
  email?: string | null;
  phone?: string | null;
  title?: string | null;
  company?: string | null;
  location?: string | null;
  notes?: string | null;
  last_activity_at?: string | null;
  created_at: string;
  updated_at: string;
}

export default function CandidateDetail(){
  const params = useParams();
  const router = useRouter();
  const cid = Number(params?.id);
  const [rid, setRid] = useState<string|null>(null);
  const [profile, setProfile] = useState<Profile|null>(null);
  const [name, setName] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);

  useEffect(()=>{
    const tok = getTokenFromCookie();
    if(!tok){ setError('Auth missing'); setLoading(false); return; }
    try {
      const payload = JSON.parse(atob(tok.split('.')[1]));
      const email = payload?.email; if(!email){ setError('No recruiter email'); setLoading(false); return; }
      setRid(email);
      // fetch candidate name, then profile
      (async ()=>{
        try {
          const headers = { 'Authorization': `Bearer ${tok}` };
          const cResp = await fetch(`/api/recruiter/${encodeURIComponent(email)}/candidates` , { headers });
          if(!cResp.ok) throw new Error('Candidate list failed');
          const list = await cResp.json();
          const item = list.items?.find((x:any)=> x.id === cid);
          if(item) setName(item.name);
          const pResp = await fetch(`/api/recruiter/${encodeURIComponent(email)}/candidates/${cid}/profile`, { headers });
          if(pResp.ok){ setProfile(await pResp.json()); }
          else if(pResp.status===404){ /* lazy created earlier */ }
        } catch(e:any){ setError(e.message||'Load failed'); }
        finally { setLoading(false); }
      })();
    } catch { setError('Token parse error'); setLoading(false); }
  }, [cid]);

  return (
    <main style={{padding:'32px 28px', fontFamily:'system-ui, Segoe UI, Roboto, sans-serif'}}>
      <button onClick={()=> router.push('/recruiter')} style={{marginBottom:18, background:'none', border:'1px solid #d1d5db', padding:'6px 10px', borderRadius:6, cursor:'pointer', fontSize:12}}>← Back</button>
      {loading && <div>Loading...</div>}
      {error && <div style={{color:'#dc2626'}}>{error}</div>}
      {!loading && !error && (
        <div style={{display:'flex', flexDirection:'column', gap:14}}>
          <div style={{display:'flex', alignItems:'center', gap:16}}>
            <div style={{width:70, height:70, borderRadius:12, background:'linear-gradient(135deg,#1e3a8a,#3b82f6)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:30, fontWeight:600}}>{(name||'C').charAt(0).toUpperCase()}</div>
            <div>
              <h1 style={{margin:0, fontSize:28}}>{name || 'Candidate'}</h1>
              <div style={{fontSize:12, opacity:.6}}>ID {cid}</div>
            </div>
          </div>
          <section style={{display:'grid', gap:12, gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))'}}>
            <Field label="Email" value={profile?.email} />
            <Field label="Phone" value={profile?.phone} />
            <Field label="Title" value={profile?.title} />
            <Field label="Company" value={profile?.company} />
            <Field label="Location" value={profile?.location} />
            <Field label="Last Activity" value={profile?.last_activity_at ? new Date(profile.last_activity_at).toLocaleString(): undefined} />
          </section>
          {profile?.notes && (
            <div style={{background:'#f8fafc', padding:'12px 14px', border:'1px solid #e2e8f0', borderRadius:8}}>
              <div style={{fontSize:12, fontWeight:600, marginBottom:4}}>Notes</div>
              <div style={{fontSize:14, lineHeight:1.5, whiteSpace:'pre-wrap'}}>{profile.notes}</div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}

function Field({label, value}:{label:string; value?: string | null}){
  return (
    <div style={{display:'flex', flexDirection:'column', gap:4}}>
      <span style={{fontSize:11, textTransform:'uppercase', opacity:.55, letterSpacing:.5}}>{label}</span>
      <span style={{fontSize:14}}>{value || <span style={{opacity:.4}}>—</span>}</span>
    </div>
  );
}
