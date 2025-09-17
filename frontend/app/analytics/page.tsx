"use client";
import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { getAuthHeaders } from '../lib/auth';
import { getApiBase } from '../lib/apiBase';
// Reverted: removed gradient color imports for plain style

interface TrackedMessage { id: string; to_email: string; subject: string; created_at: string; events: number; provider_msgid?: string|null }
interface TrackedEvent { id: string; msg_id: string; event: string; email?: string; url?: string|null; reason?: string|null; timestamp: string | number }

// Color tokens (aligned with admin page gradients)
const PALETTE = {
  blue: ['#5d92ff','#9ec2ff'],
  indigo: ['#6366f1','#a5b4fc'],
  cyan: ['#06b6d4','#67e8f9'],
  emerald: ['#10b981','#6ee7b7'],
  violet: ['#8b5cf6','#c4b5fd'],
  amber: ['#f59e0b','#fbbf24'],
  rose: ['#f43f5e','#fb7185']
};

function timeAgo(input: string){ const d=new Date(input); const diff=(Date.now()-d.getTime())/1000; if(isNaN(diff)) return input; if(diff<60) return `${Math.floor(diff)}s`; if(diff<3600) return `${Math.floor(diff/60)}m`; if(diff<86400) return `${Math.floor(diff/3600)}h`; const days=Math.floor(diff/86400); if(days<7) return `${days}d`; return d.toLocaleDateString(); }

export default function AnalyticsPage(){
  const API_BASE = getApiBase();
  const headers = getAuthHeaders() as Record<string,string>;
  const [tracked, setTracked] = useState<TrackedMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string|null>(null);
  const [selected, setSelected] = useState<TrackedMessage | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [query, setQuery] = useState("");
  const [prefetching, setPrefetching] = useState(false);
  const [eventsCache, setEventsCache] = useState<Record<string, TrackedEvent[]>>({});
  const [eventsLoading, setEventsLoading] = useState<Record<string, boolean>>({});
  const [eventsError, setEventsError] = useState<Record<string, string>>({});
  const [focusCarousel, setFocusCarousel] = useState<string>('Recent');
  const carouselRefs = useRef<Record<string, HTMLDivElement|null>>({});

  const updateEventsLoading=(id:string,val:boolean)=> setEventsLoading(s=>({...s,[id]:val}));
  const updateEventsError=(id:string,val:string|undefined)=> setEventsError(s=>({...s,[id]:val||''}));

  const fetchEvents = useCallback(async (msg: TrackedMessage, force=false)=>{
    if(!force && eventsCache[msg.id]) return;
    updateEventsLoading(msg.id,true); updateEventsError(msg.id, undefined);
    try {
      const r = await fetch(`${API_BASE}/emails/tracked/${encodeURIComponent(msg.id)}`, { headers });
      if(r.ok){ const data: TrackedEvent[] = await r.json(); setEventsCache(c=>({...c,[msg.id]:data})); }
      else updateEventsError(msg.id, `Failed (${r.status})`);
    } catch { updateEventsError(msg.id,'Network'); } finally { updateEventsLoading(msg.id,false); }
  },[API_BASE, headers, eventsCache]);

  async function refreshTracked(){
    setLoading(true); setError(null);
    try { const r=await fetch(`${API_BASE}/emails/tracked`, { headers }); if(r.ok){ const data:TrackedMessage[] = await r.json(); setTracked(data);} else setError(`Failed (${r.status})`);} catch { setError('Network error'); } finally { setLoading(false);} }

  useEffect(()=>{ refreshTracked(); },[]);
  useEffect(()=>{ if(!autoRefresh) return; const t=setInterval(refreshTracked,15000); return ()=> clearInterval(t); },[autoRefresh]);

  // Prefetch first 16 messages lazily
  useEffect(()=>{ if(!tracked.length) return; let cancel=false; (async()=>{ setPrefetching(true); for(const m of tracked.slice(0,16)){ if(cancel) break; await fetchEvents(m,false);} setPrefetching(false); })(); return ()=>{ cancel=true; }; },[tracked, fetchEvents]);

  const aggregates = useMemo(()=>{ const all=Object.values(eventsCache).flat(); const counts:Record<string,number>={}; for(const e of all){ counts[e.event]=(counts[e.event]||0)+1;} const replied=(counts['inbound_reply']||0)+(counts['imap_reply']||0)+(counts['zoho_reply']||0); return { totalMessages: tracked.length, totalEvents: all.length, delivered: counts['delivered']||0, opened: counts['open']||0, clicked: counts['click']||0, replied, bounced: counts['bounce']||0, spam: counts['spamreport']||0 }; },[eventsCache, tracked]);

  const filtered = useMemo(()=> tracked.filter(m=> !query || (m.subject?.toLowerCase().includes(query.toLowerCase()) || m.to_email.toLowerCase().includes(query.toLowerCase()))),[tracked, query]);

  const recent = filtered.slice(0,18);
  function engagementScore(ev:TrackedEvent[]){ const c:Record<string,number>={}; ev.forEach(e=> c[e.event]=(c[e.event]||0)+1); return (c['open']||0)*2 + (c['click']||0)*4 + ((c['inbound_reply']||0)+(c['imap_reply']||0)+(c['zoho_reply']||0))*10 + (c['delivered']?1:0) - (c['bounce']||0)*3; }
  const engaged = [...filtered].sort((a,b)=> engagementScore(eventsCache[b.id]||[]) - engagementScore(eventsCache[a.id]||[])).slice(0,18);
  const replies = filtered.filter(m => (eventsCache[m.id]||[]).some(e=> ['inbound_reply','imap_reply','zoho_reply'].includes(e.event))).slice(0,18);
  const issues = filtered.filter(m => (eventsCache[m.id]||[]).some(e=> ['bounce','spamreport','dropped'].includes(e.event))).slice(0,18);

  function openDrawer(m:TrackedMessage){ setSelected(m); setDrawerOpen(true); fetchEvents(m); }

  // Keyboard navigation across focused carousel (arrow left/right)
  useEffect(()=>{ function onKey(e:KeyboardEvent){ if(!['ArrowLeft','ArrowRight'].includes(e.key)) return; const ref=carouselRefs.current[focusCarousel]; if(!ref) return; const amt = ref.clientWidth * 0.8; ref.scrollBy({left: e.key==='ArrowRight'? amt : -amt, behavior:'smooth'});} window.addEventListener('keydown', onKey); return ()=> window.removeEventListener('keydown', onKey); },[focusCarousel]);

  return (
    <div className="flex flex-col gap-10 pb-24 relative">
      <BackgroundFlares />
      {/* Plain Hero */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 flex flex-col gap-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
          <div className="flex-1 flex flex-col gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-800">Tracked Emails</h1>
            <p className="text-sm text-slate-500 max-w-2xl">Live status of outbound messages with engagement signals (opens, clicks, replies, bounces).</p>
            <MetricsGrid a={aggregates} prefetching={prefetching} />
          </div>
          <div className="w-full max-w-xs flex flex-col gap-3">
            <div className="flex gap-2 flex-wrap">
              <button onClick={refreshTracked} className="text-xs px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50">{loading? 'Refreshing…':'Refresh'}</button>
              <button onClick={()=> setAutoRefresh(a=>!a)} className={`text-xs px-3 py-1.5 rounded-md border ${autoRefresh? 'border-indigo-400 bg-indigo-50 text-indigo-700':'border-slate-300 bg-white hover:bg-slate-50'}`}>{autoRefresh? 'Auto On':'Auto Off'}</button>
              <button onClick={()=> { setEventsCache({}); setPrefetching(false); }} className="text-xs px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50">Clear Cache</button>
            </div>
            <div className="relative">
              <input value={query} onChange={e=> setQuery(e.target.value)} placeholder="Search subject or recipient" className="w-full bg-white border border-slate-300 text-slate-700 text-sm rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
              {query && <button onClick={()=> setQuery("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs hover:text-slate-600">✕</button>}
            </div>
            <div className="text-[11px] text-slate-500 flex gap-4"><span>Prefetched {Object.keys(eventsCache).length}</span>{prefetching && <span className="animate-pulse">warming…</span>}</div>
          </div>
        </div>
      </div>
      <Carousel label="Recent" items={recent} eventsCache={eventsCache} loading={loading} onOpen={openDrawer} focusKey={focusCarousel} setFocus={setFocusCarousel} innerRef={el=> carouselRefs.current['Recent']=el} />
      <Carousel label="Most Engaged" items={engaged} eventsCache={eventsCache} loading={loading} onOpen={openDrawer} highlight="engagement" focusKey={focusCarousel} setFocus={setFocusCarousel} innerRef={el=> carouselRefs.current['Most Engaged']=el} />
      <Carousel label="Replies" items={replies} eventsCache={eventsCache} loading={loading} onOpen={openDrawer} emptyHint="No replies yet." focusKey={focusCarousel} setFocus={setFocusCarousel} innerRef={el=> carouselRefs.current['Replies']=el} />
      <Carousel label="Issues" items={issues} eventsCache={eventsCache} loading={loading} onOpen={openDrawer} emptyHint="No delivery issues." focusKey={focusCarousel} setFocus={setFocusCarousel} innerRef={el=> carouselRefs.current['Issues']=el} />
      {error && <div className="text-xs text-rose-500">{error}</div>}
      {drawerOpen && selected && (
        <MessageDrawer message={selected} close={()=> setDrawerOpen(false)} fetchEvents={fetchEvents} events={eventsCache[selected.id]||[]} loading={eventsLoading[selected.id]} error={eventsError[selected.id]} />
      )}
  {/* Palette preview removed */}
    </div>
  );
}

/* ---------- Components ---------- */
function BackgroundFlares(){
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute -top-32 -left-24 w-[520px] h-[520px] bg-gradient-to-br from-indigo-600/30 to-cyan-400/20 rounded-full blur-[110px] animate-pulse" />
      <div className="absolute top-40 -right-32 w-[480px] h-[480px] bg-gradient-to-br from-violet-600/25 to-rose-400/25 rounded-full blur-[120px] animate-[pulse_8s_ease-in-out_infinite_alternate]" />
    </div>
  );
}

// Removed GradientHero / PalettePreview components

function MetricsGrid({a,prefetching}:{a:any; prefetching:boolean}){
  const data=[
    {label:'Messages', value:a.totalMessages, accent:'from-indigo-300 to-indigo-100'},
    {label:'Events', value:a.totalEvents, accent:'from-slate-200 to-white'},
    {label:'Opened', value:a.opened, accent:'from-blue-300 to-cyan-100'},
    {label:'Clicked', value:a.clicked, accent:'from-cyan-300 to-emerald-100'},
    {label:'Replied', value:a.replied, accent:'from-violet-300 to-pink-100'},
    {label:'Bounced', value:a.bounced, accent:'from-rose-300 to-amber-100'},
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {data.map(m => <HeroMetric key={m.label} {...m} subtle={m.value===0} />)}
      {prefetching && <div className="col-span-2 sm:col-span-3 lg:col-span-6 text-[11px] text-white/40">Prefetching events…</div>}
    </div>
  );
}

function HeroMetric({label,value,accent,subtle}:{label:string; value:number; accent:string; subtle?:boolean}){
  return (
    <div className={`group relative rounded-xl p-3 border backdrop-blur bg-white/5 border-white/10 hover:border-white/30 transition flex flex-col items-center gap-1 ${subtle? 'opacity-60 hover:opacity-90':''}`}> 
      <div className={`text-lg font-semibold bg-gradient-to-br ${accent} bg-clip-text text-transparent`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-white/60 font-medium">{label}</div>
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 bg-gradient-to-br from-white/5 to-white/0 rounded-xl transition" />
    </div>
  );
}

function ActionButton({label,onClick,active}:{label:string; onClick:()=>void; active?:boolean}){
  return <button onClick={onClick} className={`text-xs px-3 py-1.5 rounded-md border border-white/15 backdrop-blur bg-white/10 hover:bg-white/20 transition ${active? 'ring-1 ring-cyan-300/50 shadow-inner':''}`}>{label}</button>;
}

function Carousel({label, items, eventsCache, loading, onOpen, highlight, emptyHint, focusKey, setFocus, innerRef}:{label:string; items:TrackedMessage[]; eventsCache:Record<string,TrackedEvent[]>; loading:boolean; onOpen:(m:TrackedMessage)=>void; highlight?:string; emptyHint?:string; focusKey:string; setFocus:(k:string)=>void; innerRef:(el:HTMLDivElement|null)=>void; }){
  return (
    <div className="flex flex-col gap-2" onMouseEnter={()=> setFocus(label)}>
      <div className="flex items-center justify-between pl-1 pr-2">
        <h2 className={`text-sm font-semibold tracking-wide uppercase ${focusKey===label? 'text-indigo-600':'text-slate-600'}`}>{label}</h2>
        <div className="h-px flex-1 mx-4 bg-gradient-to-r from-slate-300/50 to-transparent" />
      </div>
      <div ref={innerRef} className="relative flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory scroll-smooth group/carousel">
        {items.map(m => <MessageCard key={m.id} msg={m} events={eventsCache[m.id]||[]} onClick={()=> onOpen(m)} highlight={highlight} />)}
        {!loading && items.length===0 && <div className="text-xs text-slate-500 px-2 py-4">{emptyHint||'Nothing yet.'}</div>}
        {loading && items.length===0 && <SkeletonRow />}
      </div>
    </div>
  );
}

function SkeletonRow(){
  return (
    <div className="flex gap-4">
      {Array.from({length:5}).map((_,i)=>(
        <div key={i} className="w-64 h-40 rounded-xl bg-gradient-to-br from-slate-200 to-slate-100 animate-pulse border border-slate-200 shadow-inner" />
      ))}
    </div>
  );
}

function summarizeForCard(events: TrackedEvent[]){ const c:Record<string,number>={}; events.forEach(e=> c[e.event]=(c[e.event]||0)+1); const reply=(c['inbound_reply']||0)+(c['imap_reply']||0)+(c['zoho_reply']||0); return { open:c['open']||0, click:c['click']||0, reply, bounce:c['bounce']||0 }; }
function MessageCard({msg, events, onClick, highlight}:{msg:TrackedMessage; events:TrackedEvent[]; onClick:()=>void; highlight?:string; }){
  const s=summarizeForCard(events); const score = (s.open*2)+(s.click*4)+(s.reply*10)+(events.length?1:0)-(s.bounce*3);
  return (
    <button onClick={onClick} className="w-64 shrink-0 snap-start rounded-lg border border-slate-200 bg-white shadow-sm hover:shadow-md transition focus:outline-none focus:ring-2 focus:ring-indigo-400/50 p-4 flex flex-col gap-3 text-left">
      <div className="text-xs font-semibold line-clamp-2 text-slate-800" title={msg.subject||'—'}>{msg.subject||'—'}</div>
      <div className="flex items-center justify-between text-[11px] text-slate-500"><span className="truncate" title={msg.to_email}>{msg.to_email}</span><span>{timeAgo(msg.created_at)}</span></div>
      <div className="flex flex-wrap gap-1 mt-1">
        {s.open>0 && <Pill color="bg-blue-600">O {s.open}</Pill>}
        {s.click>0 && <Pill color="bg-cyan-600">C {s.click}</Pill>}
        {s.reply>0 && <Pill color="bg-violet-600">R {s.reply}</Pill>}
        {s.bounce>0 && <Pill color="bg-rose-600">B {s.bounce}</Pill>}
      </div>
      {highlight==='engagement' && <div className="mt-1 text-[10px] text-indigo-600 font-medium">Score {score}</div>}
    </button>
  );
}
function Pill({children,color}:{children:React.ReactNode;color:string}){ return <span className={`text-[10px] text-white px-2 py-0.5 rounded-full font-medium ${color}`}>{children}</span>; }

function MessageDrawer({message, close, fetchEvents, events, loading, error}:{message:TrackedMessage; close:()=>void; fetchEvents:(m:TrackedMessage, force?:boolean)=>Promise<void>; events:TrackedEvent[]; loading?:boolean; error?:string; }){
  const summary = summarize(events);
  useEffect(()=>{ fetchEvents(message); },[message, fetchEvents]);
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={close} />
      <div className="absolute right-0 top-0 h-full w-[520px] bg-gradient-to-br from-white via-white to-slate-50 shadow-2xl flex flex-col border-l border-slate-200 animate-[slideIn_.4s_cubic-bezier(.4,.14,.3,1)]">
        <div className="p-5 border-b bg-white/60 backdrop-blur flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1 max-w-[360px]">
            <h3 className="text-sm font-semibold leading-tight break-words">{message.subject||'—'}</h3>
            <div className="text-[11px] text-slate-500 truncate" title={message.to_email}>{message.to_email}</div>
            <div className="text-[10px] text-slate-400">Sent {timeAgo(message.created_at)} • {new Date(message.created_at).toLocaleString()}</div>
          </div>
          <button onClick={close} className="text-[11px] px-2 py-1 rounded-md bg-slate-100 hover:bg-slate-200 border border-slate-200">Close</button>
        </div>
        <div className="p-4 flex flex-wrap gap-2 text-[10px] border-b bg-slate-50/70">
          <MetricPill label="Delivered" value={summary.delivered} color="bg-emerald-600" />
          <MetricPill label="Opened" value={summary.opened} color="bg-blue-600" />
            <MetricPill label="Clicked" value={summary.clicked} color="bg-cyan-600" />
            <MetricPill label="Replied" value={summary.replied} color="bg-violet-600" />
            <MetricPill label="Bounced" value={summary.bounced} color="bg-rose-600" />
            <MetricPill label="Spam" value={summary.spam} color="bg-amber-600" />
            <MetricPill label="Unsub" value={summary.unsub} color="bg-slate-600" />
            <MetricPill label="Deferred" value={summary.deferred} color="bg-amber-500" />
            <MetricPill label="Dropped" value={summary.dropped} color="bg-gray-600" />
        </div>
        <div className="flex-1 overflow-auto p-5 space-y-3">
          {loading && <div className="text-xs text-slate-500">Loading events…</div>}
          {!loading && error && <div className="text-xs text-rose-600">{error}</div>}
          {!loading && !error && events.map(e => (
            <div key={e.id} className="rounded-xl border border-slate-200 bg-white/70 backdrop-blur-sm p-4 text-[11px] space-y-1 hover:border-indigo-300 transition">
              <div className="flex items-center justify-between font-medium text-slate-800">
                <span className="capitalize">{displayEventName(e.event)}</span>
                <span className="text-[10px] text-slate-400 whitespace-nowrap">{formatTs(e.timestamp)}</span>
              </div>
              {e.email && <div className="text-slate-500">{e.email}</div>}
              {e.url && <div className="text-indigo-600 truncate" title={e.url}>{e.url}</div>}
              {e.reason && <div className="text-amber-600">{e.reason}</div>}
            </div>
          ))}
          {!loading && !error && events.length===0 && <div className="text-xs text-slate-500">No events yet.</div>}
        </div>
        <div className="p-4 border-t bg-slate-50/70 text-[10px] text-slate-500 flex justify-between items-center">
          <span>ID: {message.id.slice(0,12)}… {message.provider_msgid && <span className="ml-1">SG:{message.provider_msgid.slice(0,8)}</span>}</span>
          <button onClick={()=> fetchEvents(message,true)} className="text-[10px] px-2 py-1 rounded-md bg-white border border-slate-200 hover:bg-slate-100">Force Reload</button>
        </div>
      </div>
    </div>
  );
}

function MetricPill({label,value,color}:{label:string; value:number; color:string}){ if(!value) return null; return <span className={`px-2 py-0.5 rounded-full text-white ${color}`}>{label} {value}</span>; }
function summarize(events: TrackedEvent[]){ const counts: Record<string, number>={}; for(const e of events){ counts[e.event]=(counts[e.event]||0)+1; } const replied=(counts['inbound_reply']||0)+(counts['imap_reply']||0)+(counts['zoho_reply']||0); return { delivered:counts['delivered']||0, opened:counts['open']||0, clicked:counts['click']||0, bounced:counts['bounce']||0, spam:counts['spamreport']||0, unsub:counts['unsubscribe']||0, deferred:counts['deferred']||0, processed:counts['processed']||0, dropped:counts['dropped']||0, replied }; }
function displayEventName(ev:string){ const map:Record<string,string>={ open:'opened', click:'clicked', delivered:'delivered', bounce:'bounced', spamreport:'spam report', unsubscribe:'unsubscribed', deferred:'deferred', processed:'processed', dropped:'dropped', inbound_reply:'replied (inbound)', imap_reply:'replied (imap)', zoho_reply:'replied (zoho)' }; return map[ev]||ev; }
function formatTs(ts:string|number){ const d= typeof ts==='number'? new Date((Number(ts)||0)*1000): new Date(ts); return isNaN(d.getTime())? String(ts): d.toLocaleString(); }
