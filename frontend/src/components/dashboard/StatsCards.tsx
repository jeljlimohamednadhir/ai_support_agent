import { TrendingUp, Users, AlertCircle, CheckCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getDashboardStats } from '@/services/api'

export default function StatsCards() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: getDashboardStats,
    refetchInterval: 30000 // Rafraîchir toutes les 30 secondes
  })
  
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 animate-pulse">
            <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        ))}
      </div>
    )
  }
  
  const statsConfig = [
    {
      title: 'Conversations totales',
      value: stats?.total_queries || 0,
      change: stats?.queries_change || 0,
      icon: TrendingUp,
      color: 'blue',
    },
    {
      title: 'Utilisateurs actifs',
      value: stats?.active_users || 0,
      change: stats?.users_change || 0,
      icon: Users,
      color: 'green',
    },
    {
      title: 'Problèmes résolus',
      value: stats?.issues_resolved || 0,
      change: stats?.resolved_change || 0,
      icon: CheckCircle,
      color: 'purple',
    },
    {
      title: 'Validations en attente',
      value: stats?.pending_validations || 0,
      change: stats?.validations_change || 0,
      icon: AlertCircle,
      color: 'orange',
    },
  ]
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {statsConfig.map((stat) => {
        const Icon = stat.icon
        const changeSign = stat.change >= 0 ? '+' : ''
        const changeColor = stat.change >= 0 ? 'text-green-600' : 'text-red-600'
        
        return (
          <div key={stat.title} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{stat.title}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">{stat.value}</p>
                <p className={`text-sm ${changeColor} mt-1`}>
                  {changeSign}{stat.change.toFixed(1)}%
                </p>
              </div>
              <div className={`p-3 bg-${stat.color}-100 rounded-lg`}>
                <Icon className={`w-6 h-6 text-${stat.color}-600`} />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
