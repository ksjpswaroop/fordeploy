"use client";
import { useRouter } from 'next/navigation';
import { getAuthHeaders, logout as clientLogout } from '../../lib/auth';

export default function SettingsPage() {
  const router = useRouter();

  async function handleLogout() {
    try {
      // Best-effort backend logout to deactivate sessions
      await fetch('/auth/logout', {
        method: 'POST',
        headers: getAuthHeaders(),
      });
    } catch (e) {
      // ignore network errors; client logout still proceeds
    } finally {
      clientLogout();
      router.push('/login');
    }
  }

  return (
    <div className="card" style={{maxWidth:640}}>
      <div className="section-title">Account</div>
      <div style={{display:'flex', gap:12, alignItems:'center'}}>
        <button className="btn outline" onClick={handleLogout}>Log out</button>
      </div>
    </div>
  );
}
