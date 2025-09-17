"use client";
import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { getTokenFromCookie } from '../lib/auth';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  useEffect(()=>{
    try {
      const tok = getTokenFromCookie();
      if (!tok) return; // no token yet, let auth flow handle redirect elsewhere
      const parts = tok.split('.');
      if (parts.length===3){
        const payload = JSON.parse(atob(parts[1].replace(/-/g,'+').replace(/_/g,'/')));
        if (payload.role === 'candidate') {
          // candidate should not stay inside /admin area
            router.replace('/candidate');
        }
      }
    } catch(e){ /* ignore */ }
  }, [pathname]);
  return <>{children}</>;
}
