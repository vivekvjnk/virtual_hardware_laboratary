import type { RecentProject } from '../types/dashboard'

interface RecentProjectsProps {
  projects: RecentProject[]
  onSelect: (id: string) => void
}

function badgeColor(progress: number) {
  if (progress >= 90) return 'bg-emerald-500/10 text-emerald-300'
  if (progress >= 60) return 'bg-sky-500/10 text-sky-300'
  if (progress >= 30) return 'bg-amber-500/10 text-amber-300'
  return 'bg-rose-500/10 text-rose-300'
}

export default function RecentProjects({ projects, onSelect }: RecentProjectsProps) {
  return (
    <div className="space-y-4 rounded-3xl border border-slate-800 bg-slate-950/95 p-6 shadow-xl shadow-slate-950/30">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.32em] text-slate-500">Recent Projects</p>
          <h2 className="text-xl font-semibold text-white">Overview</h2>
        </div>
        <span className="rounded-full bg-violet-500/10 px-3 py-1 text-xs uppercase tracking-[0.24em] text-violet-300">Active</span>
      </div>

      <div className="space-y-3">
        {projects.map((project) => (
          <div 
            key={project.id} 
            className="rounded-3xl border border-slate-800 bg-slate-900 p-4 hover:border-violet-500/50 hover:bg-slate-800/80 cursor-pointer transition-all"
            onClick={() => onSelect(project.id)}
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-semibold text-white">{project.name}</p>
                <p className="text-sm text-slate-400">
                  {project.modules} Modules · Last opened {project.lastOpened}
                </p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] ${badgeColor(project.progress)}`}>
                {project.progress}%
              </span>
            </div>
            <p className="mt-3 text-sm text-slate-400">{project.status}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
