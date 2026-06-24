import type { DashboardData } from '../types/dashboard'

const dashboardData: DashboardData = {
  navItems: [
    { id: 'home', label: 'Home', icon: '🏠', active: true },
    { id: 'mission-dashboard', label: 'Missions', icon: '📊' },
    { id: 'agents', label: 'Agents', icon: '🤖' },
    { id: 'workflows', label: 'Workflows', icon: '🧭' },
    { id: 'artifacts', label: 'Artifacts', icon: '📦' },
    { id: 'observatory', label: 'Observatory', icon: '🔭' },
    { id: 'authority-console', label: 'Authority Console', icon: '🛡️' },
    { id: 'workspace', label: 'Workspace', icon: '🗂️', badge: 'Active' },
  ],
  heroActions: [
    {
      id: 'create-project',
      title: 'Create New Project',
      description: 'Start a new mission from scratch',
      cta: 'Create Project',
      variant: 'primary',
    },
    {
      id: 'load-project',
      title: 'Load Existing Project',
      description: 'Open a saved workspace or restore from archive',
      cta: 'Load Project',
      variant: 'secondary',
    },
  ],
  recentProjects: [
    { id: 'project-alpha', name: 'Project Alpha', modules: 5, lastOpened: '2 hours ago', progress: 65, status: 'In Progress' },
    { id: 'project-beta', name: 'Project Beta', modules: 3, lastOpened: 'Yesterday', progress: 40, status: 'In Progress' },
    { id: 'project-gamma', name: 'Project Gamma', modules: 4, lastOpened: '2 days ago', progress: 25, status: 'Needs Attention' },
    { id: 'project-delta', name: 'Project Delta', modules: 3, lastOpened: '4 days ago', progress: 100, status: 'Complete' },
  ],
  templates: [
    { id: 'template-bms', name: 'Battery Management System', description: 'Complete BMS reference design with protection and monitoring', modules: 5 },
    { id: 'template-power', name: 'Power Supply', description: 'AC-DC / DC-DC power supply designs', modules: 3 },
    { id: 'template-motor', name: 'Motor Controller', description: 'BLDC / PMSM motor control reference design', modules: 4 },
    { id: 'template-inverter', name: 'Inverter', description: 'DC-AC inverter topologies and reference designs', modules: 3 },
  ],
  missionFeed: [
    {
      id: 'feed-alpha',
      title: 'Project Alpha',
      workflow: 'Bootstrap → Archy → Librarian → ANA',
      status: 'In Progress',
      notes: ['ANA iteration 5 accepted', 'Librarian imported 12 components', 'Current sensing module validated'],
      timestamp: '2 hours ago',
    },
    {
      id: 'feed-beta',
      title: 'Project Beta',
      workflow: 'Bootstrap → Archy → Librarian',
      status: 'In Progress',
      notes: ['Archy generated SCUD', 'Workflow entered Librarian stage'],
      timestamp: '6 hours ago',
    },
    {
      id: 'feed-gamma',
      title: 'Project Gamma',
      workflow: 'Bootstrap',
      status: 'Initialized',
      notes: ['Project initialized', 'Resources indexed'],
      timestamp: 'Yesterday',
    },
    {
      id: 'feed-delta',
      title: 'Project Delta',
      workflow: 'Bootstrap → Archy → Librarian → ANA',
      status: 'Needs Attention',
      notes: ['ANA iteration 3 rejected', 'Review required'],
      timestamp: 'Yesterday',
    },
  ],
}

export default dashboardData
