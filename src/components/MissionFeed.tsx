import type { MissionFeedItem } from '../types/dashboard'

interface MissionFeedProps {
  feed: MissionFeedItem[]
}

const statusClasses: Record<string, string> = {
  'In Progress': 'bg-sky-500/10 text-sky-300',
  Initialized: 'bg-emerald-500/10 text-emerald-300',
  'Needs Attention': 'bg-amber-500/10 text-amber-300',
}

export default function MissionFeed({ feed }: MissionFeedProps) {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-950/95 p-6 shadow-xl shadow-slate-950/30">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.32em] text-slate-500">Mission Feed</p>
          <h2 className="text-xl font-semibold text-white">Active Missions</h2>
        </div>
        <button className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800">
          View All
        </button>
      </div>

      <div className="mt-5 space-y-4">
        {feed.map((item) => (
          <div key={item.id} className="rounded-3xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-semibold text-white">{item.title}</p>
                <p className="mt-1 text-sm text-slate-400">Workflow: {item.workflow}</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${statusClasses[item.status] ?? 'bg-slate-800 text-slate-300'}`}>
                {item.status}
              </span>
            </div>
            <ul className="mt-3 space-y-2 text-sm text-slate-400">
              {item.notes.map((note, index) => (
                <li key={index} className="flex gap-2">
                  <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-violet-400" />
                  <span>{note}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs uppercase tracking-[0.2em] text-slate-500">{item.timestamp}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
