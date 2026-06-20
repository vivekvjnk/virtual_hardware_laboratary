import type { TemplateCard } from '../types/dashboard'

interface ProjectTemplatesProps {
  templates: TemplateCard[]
}

export default function ProjectTemplates({ templates }: ProjectTemplatesProps) {
  return (
    <div className="space-y-4 rounded-3xl border border-slate-800 bg-slate-950/95 p-6 shadow-xl shadow-slate-950/30">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.32em] text-slate-500">Project Templates</p>
          <h2 className="text-xl font-semibold text-white">Reference Designs</h2>
        </div>
      </div>

      <div className="grid gap-3">
        {templates.map((template) => (
          <div key={template.id} className="rounded-3xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-semibold text-white">{template.name}</p>
                <p className="mt-1 text-sm text-slate-400">{template.description}</p>
              </div>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs uppercase tracking-[0.18em] text-slate-400">
                {template.modules} Modules
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
