"use client";
import React, { useEffect, useState } from 'react';

/**
 * ThemeToggle switches between new (default) and legacy look.
 * Preference persisted in localStorage under 'ui_theme'.
 */
export const ThemeToggle: React.FC = () => {
  const [legacy,setLegacy] = useState(false);
  useEffect(()=>{
    const stored = typeof window!=="undefined" ? localStorage.getItem('ui_theme'):null;
    if(stored==='legacy'){ setLegacy(true); document.body.classList.add('theme-legacy'); }
  },[]);
  const toggle=()=>{
    const next = !legacy;
    setLegacy(next);
    if(next){ document.body.classList.add('theme-legacy'); localStorage.setItem('ui_theme','legacy'); }
    else { document.body.classList.remove('theme-legacy'); localStorage.setItem('ui_theme','modern'); }
  };
  return (
    <button onClick={toggle} className="btn outline" style={{fontSize:'.6rem', padding:'6px 10px'}} title="Toggle legacy theme">
      {legacy? 'Legacy ✓' : 'Legacy'}
    </button>
  );
};
