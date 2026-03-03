import StatsCards from '@/components/dashboard/StatsCards'
import ActivityChart from '@/components/dashboard/ActivityChart'
import RecentIssues from '@/components/dashboard/RecentIssues'

export default function DashboardPage() {
  return (
    <div className="p-8 dark:bg-gray-900">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">Tableau de bord</h1>
      
      <StatsCards />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
        <ActivityChart />
        <RecentIssues />
      </div>
    </div>
  )
}
