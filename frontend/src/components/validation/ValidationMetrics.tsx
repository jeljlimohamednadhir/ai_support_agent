import { useQuery } from '@tanstack/react-query'
import { TrendingUp, Clock, CheckCircle, Edit3, Brain } from 'lucide-react'
import api from '@/services/api'
import { fetchCorrectionStats } from '@/services/correctionService'

interface ChatbotStats {
  total: number
  pending: number
  validated: number
  rejected: number
  high_priority_pending: number
  corrections_pending: number
  validation_rate: number
}

const TierDistributionBar = ({
  high, medium, low,
}: { high: number; medium: number; low: number }) => {
  const total = high + medium + low
  if (total === 0) return <p className="text-xs text-gray-400 mt-1">Aucune donnée</p>
  const pHigh   = Math.round((high   / total) * 100)
  const pMedium = Math.round((medium / total) * 100)
  const pLow    = Math.round((low    / total) * 100)
  return (
    <div className="mt-2 space-y-1">
      <div className="flex items-center gap-1.5">
        <div className="w-2 h-2 rounded-full bg-green-500 shrink-0" />
        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full bg-green-500 rounded-full" style={{ width: `${pHigh}%` }} />
        </div>
        <span className="text-xs font-mono text-gray-500 w-10 text-right">{pHigh}%</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="w-2 h-2 rounded-full bg-yellow-500 shrink-0" />
        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full bg-yellow-500 rounded-full" style={{ width: `${pMedium}%` }} />
        </div>
        <span className="text-xs font-mono text-gray-500 w-10 text-right">{pMedium}%</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full bg-red-500 rounded-full" style={{ width: `${pLow}%` }} />
        </div>
        <span className="text-xs font-mono text-gray-500 w-10 text-right">{pLow}%</span>
      </div>
    </div>
  )
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

  const { data: corrStats } = useQuery({
    queryKey: ['correctionStats'],
    queryFn: fetchCorrectionStats,
    refetchInterval: 15000,
  })

  const dist = corrStats?.tier_distribution ?? { HIGH: 0, MEDIUM: 0, LOW: 0 }

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
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {metrics.map((m) => (
        <div key={m.label} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-4 flex items-start gap-3">
          <div className={`p-2 rounded-lg ${m.bg}`}>{m.icon}</div>
          <div className="min-w-0">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{m.value}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">{m.label}</p>
            {m.sub && <p className="text-xs text-gray-400 mt-0.5">{m.sub}</p>}
          </div>
        </div>
      ))}

      {/* AI Tier Distribution card */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-4">
        <div className="flex items-center gap-2 mb-1">
          <div className="p-2 rounded-lg bg-indigo-50">
            <Brain size={20} className="text-indigo-600" />
          </div>
          <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">Qualité IA</p>
        </div>
        <TierDistributionBar
          high={dist.HIGH ?? 0}
          medium={dist.MEDIUM ?? 0}
          low={dist.LOW ?? 0}
        />
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-xs text-green-600 font-medium">HIGH</span>
          <span className="text-xs text-yellow-600 font-medium">MED</span>
          <span className="text-xs text-red-600 font-medium">LOW</span>
        </div>
      </div>
    </div>
  )
}

