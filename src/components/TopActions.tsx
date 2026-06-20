import type { HeroAction } from '../types/dashboard'

interface TopActionsProps {
  actions: HeroAction[]
}

const variantStyles = {
  primary: 'bg-violet-500 text-white',
  secondary: 'border border-slate-800 bg-slate-900 text-slate-100',
}

export default function TopActions({ actions }: TopActionsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {actions.map((action) => (
        <div
          key={action.id}
          className="rounded-3xl border border-slate-800 bg-slate-950/95 p-6 shadow-xl shadow-slate-950/30"
        >
          <div className="flex items-center justify-between gap-4 text-sm text-slate-400">
            <span className="uppercase tracking-[0.24em] text-slate-500">Project</span>
            <span className="rounded-full bg-slate-900 px-3 py-1 text-xs uppercase tracking-[0.2em]">
              {action.variant === 'primary' ? 'New' : 'Restore'}
            </span>
          </div>
          <h2 className="mt-4 text-2xl font-semibold text-white">{action.title}</h2>
          <p className="mt-2 text-slate-400">{action.description}</p>
          <button
            type="button"
            className={`mt-8 inline-flex items-center justify-center rounded-2xl px-5 py-3 text-sm font-semibold transition ${variantStyles[action.variant]}`}
          >
            {action.cta}
          </button>
        </div>
      ))}
    </div>
  )
}
