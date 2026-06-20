import dashboardData from '../data/mockDashboardData'
import type { DashboardData } from '../types/dashboard'

// Replace these hooks with real backend API calls when the developer API is available.
export async function fetchDashboardData(): Promise<DashboardData> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(dashboardData), 150)
  })
}

export async function fetchSidebarItems() {
  return fetchDashboardData().then((data) => data.navItems)
}
