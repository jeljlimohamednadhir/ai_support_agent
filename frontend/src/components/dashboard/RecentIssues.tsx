import { useQuery } from '@tanstack/react-query'
import { getRecentIssues } from '@/services/api'

// Fonction simple pour formater les dates sans dépendance
const formatTimeAgo = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  
  if (seconds < 60) return 'il y a quelques secondes'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `il y a ${minutes} minute${minutes > 1 ? 's' : ''}`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `il y a ${hours} heure${hours > 1 ? 's' : ''}`
  const days = Math.floor(hours / 24)
  if (days < 30) return `il y a ${days} jour${days > 1 ? 's' : ''}`
  const months = Math.floor(days / 30)
  return `il y a ${months} mois`
}

export default function RecentIssues() {
  const { data: issues = [], isLoading } = useQuery({
    queryKey: ['recentIssues'],
    queryFn: () => getRecentIssues(10),
    refetchInterval: 30000
  })
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
      case 'rejected':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    }
  }
  
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'approved':
        return 'Approuvé'
      case 'completed':
        return 'Terminé'
      case 'rejected':
        return 'Rejeté'
      case 'pending':
        return 'En attente'
      default:
        return status
    }
  }
  
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Problèmes récents</h3>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }
  
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Problèmes récents</h3>
      <div className="space-y-3">
        {issues.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 text-center py-4">Aucun problème récent</p>
        ) : (
          issues.map((issue: any) => (
            <div key={issue.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition cursor-pointer">
              <div className="flex-1">
                <p className="font-medium text-gray-900 dark:text-white">{issue.title}</p>
                <p className="text-sm text-gray-500">
                  {issue.created_at ? formatTimeAgo(issue.created_at) : 'Date inconnue'}
                </p>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(issue.status)}`}>
                {getStatusLabel(issue.status)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
