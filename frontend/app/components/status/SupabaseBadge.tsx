"use client";
import React, { useEffect, useState } from 'react';

interface HealthSupabase {
  db: boolean;
  storage: boolean;
}

interface HealthResponse {
  supabase?: HealthSupabase;
}

export const SupabaseBadge: React.FC = () => {
  const [supabase, setSupabase] = useState<HealthSupabase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    async function fetchHealth() {
      try {
        setLoading(true);
        const res = await fetch('/health');
        if(!res.ok) throw new Error('health fetch failed');
        const data: HealthResponse = await res.json();
        if(alive) setSupabase(data.supabase || null);
      } catch (e:any) {
        if(alive) setError(e.message);
      } finally {
        if(alive) setLoading(false);
      }
    }
    fetchHealth();
    const id = setInterval(fetchHealth, 15000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if(loading) return <span className="inline-flex items-center gap-1 text-xs text-gray-500">Supabase <span className="animate-pulse">…</span></span>;
  if(error) return <span className="inline-flex items-center gap-1 text-xs text-red-600">Supabase err</span>;
  if(!supabase) return <span className="inline-flex items-center gap-1 text-xs text-gray-400">Supabase off</span>;

  const clsBase = 'px-2 py-0.5 rounded text-xs font-medium border';
  const ok = (b:boolean) => b ? 'bg-green-100 text-green-700 border-green-300' : 'bg-gray-200 text-gray-600 border-gray-300';
  return (
    <div className="flex gap-2 items-center" title="Supabase integration status">
      <span className={`${clsBase} ${ok(supabase.db)}`}>DB {supabase.db ? 'ON' : 'OFF'}</span>
      <span className={`${clsBase} ${ok(supabase.storage)}`}>Storage {supabase.storage ? 'ON' : 'OFF'}</span>
    </div>
  );
};

export default SupabaseBadge;
