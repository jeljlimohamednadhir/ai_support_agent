import { useQuery } from '@tanstack/react-query'
import { TrendingUp, Clock, CheckCircle, Edit3, AlertTriangle } from 'lucide-react'
import api from '@/services/api'

interface ChatbotStats {
  total: number
  pending: number
  validated: number
  rejected: number
  high_priority_pending: number
  corrections_pending: number
  validation_rate: number
}

export default function ValidationMetrics() {
  const { data: stats, isLoading } = useQuery<ChatbotStats>({
    queryKey: ['chatbotStats'],
    queryFn: async () => {
      const res = await api.get('/validation/chatbot-stats')
      return res.data
    },
    refetchInterval: 15000,
  })

  const metrics = [
    {
      label: 'En attente',
      value: isLoading ? '…' : stats?.pending ?? 0,
      sub: stats?.high_priority_pending ? `dont ${stats.high_priority_pending} haute priorité` : undefined,
      icon: <Clock size={20} className="text-yellow-600" />,
      bg: 'bg-yellow-50',
    },
    {
      label: 'Validées',
      value: isLoading ? '…' : stats?.validated ?? 0,
      icon: <CheckCircle size={20} className="text-green-600" />,
      bg: 'bg-green-50',
    },
    {
      label: 'Corrections KB',
      value: isLoading ? '…' : stats?.corrections_pending ?? 0,
      sub: 'prêtes pour réapprentissage',
      icon: <Edit3 size={20} className="text-blue-600" />,
      bg: 'bg-blue-50',
    },
    {
      label: 'Taux de validation',
      value: isLoading ? '…' : `${stats?.validation_rate ?? 0}%`,
      icon: <TrendingUp size={20} className="text-purple-600" />,
      bg: 'bg-purple-50',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {metrics.map((m) => (
        <div key={m.label} className="bg-white rounded-xl border shadow-sm p-4 flex items-start gap-3">
          <div className={`p-2 rounded-lg ${m.bg}`}>{m.icon}</div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{m.value}</p>
            <p className="text-sm text-gray-500">{m.label}</p>
            {m.sub && <p className="text-xs text-gray-400 mt-0.5">{m.sub}</p>}
          </div>
        </div>
      ))}
    </div>
  )
}

