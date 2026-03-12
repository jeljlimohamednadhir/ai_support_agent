import { useQuery } from '@tanstack/react-query'
import ValidationQueue from '@/components/validation/ValidationQueue'
import ValidationMetrics from '@/components/validation/ValidationMetrics'
import RetrainingBanner from '@/components/validation/RetrainingBanner'
import api from '@/services/api'

export default function ValidationPage() {
  const { data: stats } = useQuery({
    queryKey: ['chatbotStats'],
    queryFn: async () => (await api.get('/validation/chatbot-stats')).data,
    refetchInterval: 15000,
  })

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6 min-h-screen dark:bg-gray-900">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">🛡️ Validation N3</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Validez les réponses du chatbot pour enrichir la base de connaissances
        </p>
      </div>

      <ValidationMetrics />

      <RetrainingBanner correctionsPending={stats?.corrections_pending ?? 0} />

      <div>
        <ValidationQueue />
      </div>
    </div>
  )
}

