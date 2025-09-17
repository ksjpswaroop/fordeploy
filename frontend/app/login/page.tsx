"use client";
import React, { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { login } from '../lib/auth';

export default function LoginPage(){
  const router = useRouter();
  const search = useSearchParams();
  const next = search?.get('next') || '/';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string|null>(null);

  async function onSubmit(e: React.FormEvent){
    e.preventDefault(); setError(null); setLoading(true);
    const normalizedEmail = email.trim().toLowerCase();
    try {
      const { must_change_password, role } = await login(normalizedEmail, password);
      if (role === 'candidate') {
        router.push('/candidate');
      } else if (role === 'recruiter') {
        router.push('/recruiter');
      } else if (role === 'admin') {
        router.push(next || '/');
      } else {
        router.push('/');
      }
    } catch (e:any) {
      const msg = e?.message || '';
      if (/incorrect email or password/i.test(msg)) {
        setError('Incorrect email or password');
      } else if (/network error/i.test(msg)) {
        setError('Cannot reach API server. Check that backend is running.');
      } else if (/login response not json/i.test(msg)) {
        setError('Unexpected server response (not JSON). Is API base correct?');
      } else {
        setError(msg || 'Login failed');
      }
    } finally { setLoading(false); }
  }

  return (
    <main style={{minHeight:'100vh', display:'grid', placeItems:'center', background:'#ffffff', color:'#333333'}}>
      <form onSubmit={onSubmit} style={{width:'min(92vw, 380px)', background:'#ffffff', border:'1px solid #e5e7eb', borderRadius:8, padding:'22px 20px'}}>
        {/* Added product title */}
        <div style={{textAlign:'center', marginBottom:10}}>
          <div style={{fontSize:38, fontWeight:800, letterSpacing:'.5px', background:'linear-gradient(90deg,#111827,#4b5563)', WebkitBackgroundClip:'text', color:'transparent', fontFamily:'system-ui, Segoe UI, Roboto, sans-serif'}}>ScholarIT</div>
        </div>
        <h1 style={{margin:'2px 0 12px', fontSize:22, color:'#333'}}>Sign in</h1>
        <div style={{display:'grid', gap:10}}>
          <label style={{fontSize:12, opacity:.8}}>Email</label>
          <input type="email" value={email} onChange={e=> setEmail(e.target.value)} required placeholder="you@example.com" style={inputStyle} autoComplete="username" />
          <label style={{fontSize:12, opacity:.8}}>Password</label>
          <input type="password" value={password} onChange={e=> setPassword(e.target.value)} required placeholder="••••••••" style={inputStyle} autoComplete="current-password" />
          {error && <div style={{color:'#f87171', fontSize:12}}>{error}</div>}
          <button type="submit" disabled={loading} style={btnPrimary}>{loading? 'Signing in…':'Sign in'}</button>
        </div>
        <div style={{marginTop:12, fontSize:12, opacity:.7}}>No account? Use /auth/register via API for now.</div>
      </form>
    </main>
  );
}

const inputStyle: React.CSSProperties = { padding:'10px 12px', background:'#ffffff', border:'1px solid #d1d5db', borderRadius:6, fontSize:14, color:'#333', outline:'none' };
const btnPrimary: React.CSSProperties = { marginTop:8, padding:'10px 12px', background:'#e5e7eb', border:'1px solid #d1d5db', borderRadius:6, color:'#333', fontWeight:600, fontSize:14, cursor:'pointer' };
