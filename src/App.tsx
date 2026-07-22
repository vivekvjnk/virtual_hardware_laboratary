import { useEffect, useState } from 'react'
import { fetchDashboardData } from './api/dashboard'
import type { DashboardData } from './types/dashboard'
import Sidebar from './components/Sidebar'
import TopActions from './components/TopActions'
import RecentProjects from './components/RecentProjects'
import ProjectTemplates from './components/ProjectTemplates'
import MissionFeed from './components/MissionFeed'
import MissionDashboard from './components/MissionDashboard'
import ModuleDetailView from './components/ModuleDetailView'

import EditorView from './components/EditorView'

function App() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  const [view, setView] = useState<'dashboard' | 'editor' | 'mission' | 'module_detail'>('dashboard');
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeModuleName, setActiveModuleName] = useState<string | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [showMissionFeed, setShowMissionFeed] = useState(true);

  useEffect(() => {
    fetchDashboardData()
      .then((data) => setDashboardData(data))
      .finally(() => setLoading(false))

    // Initialize activeProjectId from current runtime state
    fetch('http://localhost:3022/api/project-state')
      .then(res => res.json())
      .then(state => {
        if (state && state.project_id) {
          setActiveProjectId(state.project_id);
        }
      })
      .catch(err => console.error('Failed to fetch project state:', err));
  }, [])

  const [isIdentified, setIsIdentified] = useState(false);

  useEffect(() => {
    // Identify ourselves to the backend server
    fetch('http://localhost:3022/api/identify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'vhl_webui' })
    }).then(res => {
        if (res.ok) setIsIdentified(true);
    });

    // Heartbeat interval
    const heartbeatInterval = setInterval(() => {
        fetch('http://localhost:3022/api/heartbeat', { method: 'POST' });
    }, 5000);
    
    return () => {
        clearInterval(heartbeatInterval);
    };
  }, []);

  useEffect(() => {
    if (view === 'mission') {
      const targets = [document.body, document.documentElement];
      targets.forEach((el) => {
        if (el) {
          el.style.filter = '';
          (el.style as any).webkitFilter = '';
          el.classList.remove('grayscale');
        }
      });
      const runframeStyle = document.querySelector('style[data-styles="tscircuit-runframe"]');
      if (runframeStyle) {
        runframeStyle.remove();
      }
    }
  }, [view]);

  const uploadZip = async (projectName: string, file: File) => {
    // Upload file and create project through the new backend endpoint
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_name', projectName);
    
    try {
      const response = await fetch('http://localhost:3022/api/create-project', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const data = await response.json();
      console.log('Upload successful', data);
      
      if (data.project_id) {
        setActiveProjectId(data.project_id);
        setView('mission');
      }
    } catch (error) {
      console.error('Error uploading zip:', error);
      alert('Failed to upload project ZIP');
    }
  };

  const isModuleDetail = view === 'module_detail';

  return (
    <div className={`min-h-screen bg-slate-950 text-white ${isModuleDetail ? 'p-4' : 'px-6 py-6'}`}>
      <div className={`mx-auto grid ${isModuleDetail ? 'w-full' : 'max-w-[1600px]'} gap-6 ${
        !isModuleDetail && showSidebar && showMissionFeed ? 'grid-cols-[280px_minmax(720px,1fr)_320px]' :
        !isModuleDetail && showSidebar ? 'grid-cols-[280px_minmax(720px,1fr)]' :
        !isModuleDetail && showMissionFeed ? 'grid-cols-[minmax(720px,1fr)_320px]' :
        'grid-cols-[1fr]'
      }`}>
        {!isModuleDetail && showSidebar && (
          <div>
            {dashboardData ? <Sidebar items={dashboardData.navItems} onNavigate={setView} /> : <Sidebar items={[]} onNavigate={setView} />}
          </div>
        )}

        <main className={isModuleDetail ? "h-[calc(100vh-2rem)]" : "space-y-6"}>
          {view === 'mission' ? (
            activeProjectId ? (
              <MissionDashboard 
                projectId={activeProjectId} 
                onOpenModuleDetail={(moduleName) => {
                  setActiveModuleName(moduleName);
                  setView('module_detail');
                }}
              />
            ) : (
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-10 text-center text-slate-400">
                Please select or create a project to view the mission dashboard.
              </div>
            )
          ) : view === 'module_detail' ? (
            activeProjectId && activeModuleName ? (
              <ModuleDetailView 
                projectId={activeProjectId}
                moduleName={activeModuleName}
                setView={setView}
                showSidebar={showSidebar}
                setShowSidebar={setShowSidebar}
                showMissionFeed={showMissionFeed}
                setShowMissionFeed={setShowMissionFeed}
              />
            ) : (
              <div className="text-white">Invalid module or project</div>
            )
          ) : view === 'dashboard' ? (
            <>
              <section className="rounded-3xl border border-slate-800 bg-slate-950/95 p-6 shadow-xl shadow-slate-950/30">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-2xl">
                <p className="text-sm uppercase tracking-[0.32em] text-slate-500">Welcome to VHL</p>
                <h1 className="mt-4 text-4xl font-semibold text-white sm:text-5xl">
                  Virtual Hardware Laboratory
                </h1>
                <p className="mt-4 max-w-2xl text-base leading-7 text-slate-400">
                  From intent to verified hardware. AI-powered agents that design, validate,
                  and refine complex electronic systems.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5 text-center">
                  <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Recent Projects</p>
                  <p className="mt-3 text-3xl font-semibold text-white">4</p>
                </div>
                <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5 text-center">
                  <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Active Missions</p>
                  <p className="mt-3 text-3xl font-semibold text-white">3</p>
                </div>
              </div>
            </div>
            <div className="mt-8 grid gap-4 md:grid-cols-2">
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
                <h2 className="text-lg font-semibold text-white">Mission Snapshot</h2>
                <p className="mt-2 text-slate-400">Track progress, review workflows, and launch new hardware projects with confidence.</p>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
                <h2 className="text-lg font-semibold text-white">Sync Status</h2>
                <p className="mt-2 text-slate-400">Backend data hooks are ready. This dashboard will sync live once the API is connected.</p>
              </div>
            </div>
          </section>

          <section>
            {loading ? (
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-10 text-center text-slate-400">
                Loading dashboard...
              </div>
            ) : dashboardData ? (
              <TopActions 
                actions={dashboardData.heroActions} 
                isIdentified={isIdentified} 
                onUpload={uploadZip} 
                projectId={activeProjectId}
                onModuleCreated={() => {
                  // Maybe refresh something or show a message
                  console.log('Module created successfully via TopActions');
                }}
              />
            ) : (
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-10 text-center text-slate-400">
                Unable to load dashboard data.
              </div>
            )}
          </section>

          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr] xl:items-start">
            {dashboardData ? (
              <RecentProjects 
                projects={dashboardData.recentProjects} 
                onSelect={(id) => {
                  setActiveProjectId(id);
                  setView('mission');
                  // Notify runtime to load the project
                  fetch('http://localhost:3022/api/load-project', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_id: id })
                  }).catch(err => console.error('Failed to load project:', err));
                }} 
              />
            ) : (
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-10 text-center text-slate-400">
                Loading recent projects...
              </div>
            )}

            {dashboardData ? (
              <ProjectTemplates templates={dashboardData.templates} />
            ) : (
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-10 text-center text-slate-400">
                Loading templates...
              </div>
            )}
          </div>
            </>
          ) : (
            <EditorView 
              setView={setView} 
              showSidebar={showSidebar}
              setShowSidebar={setShowSidebar}
              showMissionFeed={showMissionFeed}
              setShowMissionFeed={setShowMissionFeed}
            />
          )}
        </main>

        {!isModuleDetail && showMissionFeed && (
          <aside className="space-y-6">
            {dashboardData ? (
              <MissionFeed feed={dashboardData.missionFeed} />
            ) : (
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-10 text-center text-slate-400">
                Loading mission feed...
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  )
}

export default App;
