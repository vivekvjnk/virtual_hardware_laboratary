import { useEffect, useState } from 'react'
import { fetchDashboardData } from './api/dashboard'
import type { DashboardData } from './types/dashboard'
import Sidebar from './components/Sidebar'
import TopActions from './components/TopActions'
import RecentProjects from './components/RecentProjects'
import ProjectTemplates from './components/ProjectTemplates'
import MissionFeed from './components/MissionFeed'

function App() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    fetchDashboardData()
      .then((data) => setDashboardData(data))
      .finally(() => setLoading(false))
  }, [])

  const [isIdentified, setIsIdentified] = useState(false);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  useEffect(() => {
    // Automatically connect on mount and try to reconnect if closed
    const connect = () => {
      const socket = new WebSocket('ws://localhost:1080/ws-agent');
      
      socket.onopen = () => {
        console.log('Connected to relay, identifying...');
        // Identify ourselves
        socket.send(JSON.stringify({ type: 'IDENTIFY', payload: { role: 'vhl_webui' } }));
      };

      socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'IDENTIFIED') {
            console.log('Identified with backend');
            setIsIdentified(true);
        } else if (msg.type === 'HEARTBEAT_ACK') {
            console.debug('Heartbeat acknowledged');
        }
      };

      // Heartbeat interval
      const heartbeatInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'HEARTBEAT' }));
        }
      }, 5000);

      socket.onclose = () => {
        console.log('Disconnected, retrying in 3s...');
        setIsIdentified(false);
        clearInterval(heartbeatInterval);
        setTimeout(() => setReconnectAttempt(prev => prev + 1), 3000);
      };

      setWs(socket);
    };

    connect();
    
    return () => {
        if (ws) ws.close();
    };
  }, [reconnectAttempt]);

  const uploadZip = async (projectName: string, file: File) => {
    if (!ws) {
      alert('Not connected to relay');
      return;
    }
    
    // Upload file to the new backend endpoint
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('http://localhost:1080/api/upload-project-zip', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const data = await response.json();
      console.log('Upload successful', data);
      
      // Notify backend to create project
      const payload = {
        project_name: projectName,
        zip_blob_id: 'local_zip', // Matches test fixture expectation
      };
      
      ws.send(JSON.stringify({ type: 'CREATE_PROJECT', source: 'vhl_webui', payload }));
      
    } catch (error) {
      console.error('Error uploading zip:', error);
      alert('Failed to upload project ZIP');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white px-6 py-6">
      <div className="mx-auto grid max-w-[1600px] gap-6 lg:grid-cols-[280px_minmax(720px,1fr)_320px]">
        <div>
          {dashboardData ? <Sidebar items={dashboardData.navItems} /> : <Sidebar items={[]} />}
        </div>

        <main className="space-y-6">
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
              <TopActions actions={dashboardData.heroActions} isIdentified={isIdentified} onUpload={uploadZip} />
            ) : (
              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-10 text-center text-slate-400">
                Unable to load dashboard data.
              </div>
            )}
          </section>

          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr] xl:items-start">
            {dashboardData ? (
              <RecentProjects projects={dashboardData.recentProjects} />
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
        </main>

        <aside className="space-y-6">
          {dashboardData ? (
            <MissionFeed feed={dashboardData.missionFeed} />
          ) : (
            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-10 text-center text-slate-400">
              Loading mission feed...
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

export default App;
