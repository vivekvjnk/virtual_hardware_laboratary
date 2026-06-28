import dashboardData from '../data/mockDashboardData'
import type { DashboardData } from '../types/dashboard'

// Replace these hooks with real backend API calls.
export async function fetchDashboardData(): Promise<DashboardData> {
  try {
    const response = await fetch('http://localhost:3022/api/dashboard');
    if (!response.ok) {
      throw new Error('Failed to fetch dashboard data');
    }
    return await response.json();
  } catch (err) {
    console.error('Error fetching dashboard data:', err);
    // Fallback to mock data if API is not available
    return dashboardData;
  }
}

export async function fetchSidebarItems() {
  return fetchDashboardData().then((data) => data.navItems)
}
