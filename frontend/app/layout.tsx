import React from 'react'
import { ThemeToggle } from './components/ThemeToggle'
import './globals.css'
import { LayoutGrid, Briefcase, Users2, BarChart3, Settings, Rocket } from 'lucide-react'
import SupabaseBadge from './components/status/SupabaseBadge'
import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'ScholarIT Job Recruitment', description: 'ScholarIT Job Recruitment Platform' }

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutGrid },
  { href: '/jobs', label: 'Jobs', icon: Briefcase },
  { href: '/candidates', label: 'Candidates', icon: Users2 },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/settings', label: 'Settings', icon: Settings }
]

function Nav() {
  const path = typeof window !== 'undefined' ? window.location.pathname : ''
  return (
    <nav className="nav">
      {navItems.map(item => {
        const Icon = item.icon
        const active = path === item.href
        return (
          <a key={item.href} href={item.href} className={`nav-link ${active ? 'active' : ''}`}> <Icon /> <span>{item.label}</span></a>
        )
      })}
    </nav>
  )
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="app-shell" suppressHydrationWarning>
        <aside className="sidebar">
          <div className="sidebar-head" style={{display:'flex', alignItems:'center', gap:8}}>
            <Rocket size={18} /> ScholarIT Job Recruitment
          </div>
          <Nav />
          <div className="sidebar-footer">v1.0.0</div>
        </aside>
        <div className="main-panel">
          <header className="topbar" style={{display:'flex', alignItems:'center', gap:16}}>
            <div style={{flex:1, display:'flex', flexDirection:'column'}}>
              <div className="topbar-title">ScholarIT Job Recruitment</div>
              <div className="topbar-sub">AI Recruitment Console</div>
            </div>
            <SupabaseBadge />
            <ThemeToggle />
          </header>
          <main className="page">{children}</main>
        </div>
      </body>
    </html>
  )
}
