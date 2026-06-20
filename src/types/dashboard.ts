export interface NavItem {
  id: string
  label: string
  icon: string
  active?: boolean
  badge?: string
}

export interface HeroAction {
  id: string
  title: string
  description: string
  cta: string
  variant: 'primary' | 'secondary'
}

export interface RecentProject {
  id: string
  name: string
  modules: number
  lastOpened: string
  progress: number
  status: string
}

export interface TemplateCard {
  id: string
  name: string
  description: string
  modules: number
}

export interface MissionFeedItem {
  id: string
  title: string
  workflow: string
  status: string
  notes: string[]
  timestamp: string
}

export interface DashboardData {
  navItems: NavItem[]
  heroActions: HeroAction[]
  recentProjects: RecentProject[]
  templates: TemplateCard[]
  missionFeed: MissionFeedItem[]
}
