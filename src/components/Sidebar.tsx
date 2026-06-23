import type { NavItem } from '../types/dashboard'

interface SidebarProps {
  items: NavItem[]
  onNavigate: (view: 'dashboard' | 'editor') => void
}

export default function Sidebar({ items, onNavigate }: SidebarProps) {
  return (
    <aside className="rounded-3xl border border-slate-800 bg-slate-950/90 p-5 shadow-xl shadow-slate-950/30">
      <div className="mb-8 flex items-center justify-between gap-2">
        <div>
          <p className="text-sm uppercase tracking-[0.4em] text-slate-500">VHL</p>
          <h1 className="text-2xl font-semibold">Virtual Hardware Lab</h1>
        </div>
      </div>

      <nav className="space-y-2">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => item.label === 'Dashboard' ? onNavigate('dashboard') : onNavigate('editor')}
            className={`flex w-full items-center justify-between rounded-3xl px-4 py-3 text-left transition ${
              item.active
                ? 'bg-violet-500/10 text-white shadow-sm shadow-violet-500/10'
                : 'text-slate-300 hover:bg-slate-900/80'
            }`}
          >
            <span className="flex items-center gap-3 text-sm font-medium">
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </span>
            {item.badge ? (
              <span className="rounded-full bg-slate-800 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-400">
                {item.badge}
              </span>
            ) : null}
          </button>
        ))}
      </nav>

      <div className="mt-10 rounded-3xl border border-slate-800 bg-slate-900/60 p-4">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Administrator</p>
        <div className="mt-4 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-500/15 text-2xl">JD</div>
          <div>
            <p className="font-semibold">John Doe</p>
            <p className="text-sm text-slate-400">Runtime Online</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
