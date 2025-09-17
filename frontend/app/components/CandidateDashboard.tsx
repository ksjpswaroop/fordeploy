"use client";
import React from 'react';
import DashboardPage from '../dashboard/page';

export default function CandidateDashboard(){
  return (
    <div style={{padding:"24px 24px 48px"}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:24}}>
        <div style={{display:'flex', gap:12, flexWrap:'wrap', alignItems:'center'}}>
          <a href="/" className="badge-link">ADMIN</a>
          <span style={{fontSize:'.6rem', opacity:.5}}>›</span>
          <a href="/admin/recruiter" className="badge-link">RECRUITER</a>
          <span style={{fontSize:'.6rem', opacity:.5}}>›</span>
          <span className="pill blue" style={{fontSize:'.6rem'}}>CANDIDATE</span>
        </div>
        <a href="/dashboard" className="mini-btn" title="Direct /dashboard route">Legacy View</a>
      </div>
      <DashboardPage />
    </div>
  );
}
