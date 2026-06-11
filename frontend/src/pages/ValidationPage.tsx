import { useQuery } from '@tanstack/react-query'
import ValidationQueue from '@/components/validation/ValidationQueue'
import ValidationMetrics from '@/components/validation/ValidationMetrics'
import RetrainingBanner from '@/components/validation/RetrainingBanner'
import KpiHeader from '@/components/validation/KpiHeader'
import api from '@/services/api'

export default function ValidationPage() {
  const { data: stats } = useQuery({
    queryKey: ['chatbotStats'],
    queryFn: async () => (await api.get('/validation/chatbot-stats')).data,
    refetchInterval: 15000,
  })

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5 min-h-screen dark:bg-gray-900">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          🧠 Interface d'Entraînement IA
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Validation N3 · Corrections · Calibration automatique
        </p>
      </div>

      {/* AI Quality KPI bar */}
      <KpiHeader />

      {/* Classic validation metrics (5 KPI cards + AI tier distribution) */}
      <ValidationMetrics />

      {/* Retraining banner (shows only when corrections pending) */}
      <RetrainingBanner correctionsPending={stats?.corrections_pending ?? 0} />

      {/* Main queue: AI Training tab + Classic N3 tab */}
      <ValidationQueue />
    </div>
  )
}

