"use client";
import React, { useEffect, useState } from 'react';

interface DirRec { id:number; recruiter_identifier:string; display_name:string; }
interface DirList { items: DirRec[]; total:number; }
interface Candidate { id:number; name:string; recruiter_identifier:string; }
interface CandidateList { items: Candidate[]; total:number; }

function getToken(){
  const m = document.cookie.match(/access_token=([^;]+)/); return m? decodeURIComponent(m[1]): null;
}
function authHeaders(){ const t=getToken(); return t? { 'Authorization': 'Bearer '+t, 'Content-Type':'application/json'}: {'Content-Type':'application/json'}; }

export default function AdminRecruitersPage(){
  const [dir,setDir]=useState<DirList|null>(null);
  const [loading,setLoading]=useState(true);
  const [err,setErr]=useState<string|null>(null);
  const [email,setEmail]=useState('');
  const [name,setName]=useState('');
  const [submitting,setSubmitting]=useState(false);
  const [selected,setSelected]=useState<string|null>(null);
  const [cands,setCands]=useState<CandidateList|null>(null);
  const [newCandidate,setNewCandidate]=useState('');
  const [candSubmitting,setCandSubmitting]=useState(false);

  function fetchDirectory(){
    setLoading(true);
    fetch('/api/admin/recruiters',{headers:authHeaders()})
      .then(r=>r.ok?r.json():Promise.reject(r))
      .then(setDir)
      .catch(async r=>{try{const j=await r.json(); setErr(j.detail||'Failed');}catch{setErr('Failed');}})
      .finally(()=>setLoading(false));
  }
  useEffect(()=>{fetchDirectory();},[]);

  function createRecruiter(e:React.FormEvent){
    e.preventDefault(); if(!email.trim()||!name.trim()) return; setSubmitting(true);
    fetch('/api/admin/recruiters',{method:'POST',headers:authHeaders(),body:JSON.stringify({recruiter_identifier:email.trim(), display_name:name.trim()})})
      .then(r=> r.ok? r.json(): Promise.reject(r))
      .then(obj=> { setDir(d=> d? { ...d, items:[...d.items, obj], total:d.total+1}: {items:[obj], total:1}); setEmail(''); setName(''); })
      .catch(async r=>{ try{ const j=await r.json(); setErr(j.detail||'Create failed'); } catch{ setErr('Create failed'); } })
      .finally(()=> setSubmitting(false));
  }

  function selectRecruiter(rid:string){ setSelected(rid); setCands(null); fetch(`/api/recruiter/${encodeURIComponent(rid)}/candidates`,{headers:authHeaders()})
      .then(r=> r.ok? r.json(): Promise.reject(r))
      .then(setCands)
      .catch(async r=> { try{ const j=await r.json(); setErr(j.detail||'Load candidates failed'); } catch{ setErr('Load candidates failed'); } }); }

  function addCandidate(e:React.FormEvent){ e.preventDefault(); if(!selected||!newCandidate.trim()) return; setCandSubmitting(true);
    fetch(`/api/recruiter/${encodeURIComponent(selected)}/candidates`,{method:'POST', headers:authHeaders(), body:JSON.stringify({name:newCandidate.trim()})})
      .then(r=> r.ok? r.json(): Promise.reject(r))
      .then(obj=> { setCands(prev=> prev? {...prev, items:[obj,...prev.items], total:prev.total+1}: {items:[obj], total:1}); setNewCandidate(''); })
      .catch(async r=> { try{ const j=await r.json(); setErr(j.detail||'Add candidate failed'); } catch{ setErr('Add candidate failed'); } })
      .finally(()=> setCandSubmitting(false)); }

  return <main style={{padding:'32px 40px', fontFamily:'system-ui, Segoe UI, Roboto, sans-serif'}}>
    <h1 style={{fontSize:30,fontWeight:600, marginBottom:4}}>Recruiters</h1>
    <p style={{opacity:.7, marginBottom:20}}>Manage recruiter directory and assign candidate names.</p>
    {err && <div style={{color:'#dc2626', marginBottom:12}}>{err}</div>}
    <section style={{marginBottom:30}}>
      <h2 style={{fontSize:18, fontWeight:600, marginBottom:8}}>Add Recruiter</h2>
      <form onSubmit={createRecruiter} style={{display:'flex', gap:8, flexWrap:'wrap'}}>
        <input value={email} onChange={e=> setEmail(e.target.value)} placeholder="email" type="email" required style={inputStyle} />
        <input value={name} onChange={e=> setName(e.target.value)} placeholder="display name" required style={inputStyle} />
        <button disabled={submitting} style={btn}>{submitting? 'Saving...':'Add'}</button>
      </form>
    </section>
    <div style={{display:'flex', gap:40, alignItems:'flex-start'}}>
      <div style={{flex:1}}>
        <h2 style={{fontSize:18,fontWeight:600, marginBottom:8}}>Directory</h2>
        {loading && <div>Loading...</div>}
        {!loading && <ul style={{listStyle:'none', padding:0, margin:0, display:'grid', gap:8}}>
          {dir?.items.map(r=> <li key={r.id} style={{border:'1px solid #e5e7eb', borderRadius:6, padding:'10px 12px', background:selected===r.recruiter_identifier?'#f3f4f6':'#fff', cursor:'pointer'}} onClick={()=> selectRecruiter(r.recruiter_identifier)}>
            <div style={{fontWeight:600}}>{r.display_name}</div>
            <div style={{fontSize:12, opacity:.6}}>{r.recruiter_identifier}</div>
          </li>)}
          {!dir?.items.length && <li style={{opacity:.7}}>No recruiters yet.</li>}
        </ul>}
      </div>
      <div style={{flex:2}}>
        {selected ? <div>
          <h2 style={{fontSize:18,fontWeight:600, marginBottom:12}}>Candidates for {selected}</h2>
          <form onSubmit={addCandidate} style={{display:'flex', gap:8, marginBottom:16}}>
            <input value={newCandidate} onChange={e=> setNewCandidate(e.target.value)} placeholder="New candidate name" style={inputStyle} />
            <button disabled={candSubmitting} style={btn}>{candSubmitting? 'Adding...':'Add'}</button>
          </form>
          <div style={{display:'grid', gap:6}}>
            {cands?.items.map(c=> <div key={c.id} style={{border:'1px solid #e5e7eb', borderRadius:6, padding:'10px 12px', background:'#fff'}}>
              <div style={{fontWeight:600}}>{c.name}</div>
              <div style={{fontSize:12, opacity:.6}}>ID {c.id}</div>
            </div>)}
            {!cands?.items.length && <div style={{opacity:.7}}>No candidates for this recruiter.</div>}
          </div>
        </div> : <div style={{opacity:.7}}>Select a recruiter to manage candidates.</div>}
      </div>
    </div>
  </main>;
}

const inputStyle: React.CSSProperties = { padding:'8px 10px', border:'1px solid #d1d5db', borderRadius:6, fontSize:14, flex:'1 1 160px'};
const btn: React.CSSProperties = { padding:'8px 18px', border:'1px solid #d1d5db', background:'#e5e7eb', borderRadius:6, fontWeight:600, cursor:'pointer'};
