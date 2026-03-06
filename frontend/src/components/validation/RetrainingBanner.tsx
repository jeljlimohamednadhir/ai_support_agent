import { useState } from 'react'
import { Brain, Play, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

interface Props {
  correctionsPending: number
}

type Status = 'idle' | 'running' | 'done' | 'error'

interface RetrainResult {
  corrections_applied:    number
  kb_chunks_updated:      number
  trust_scores_updated:   number
  new_procedures_drafted: number
  duration_seconds:       number
}

export default function RetrainingBanner({ correctionsPending }: Props) {
  const queryClient = useQueryClient()
  const [status, setStatus]   = useState<Status>('idle')
  const [progress, setProgress] = useState(0)
  const [result, setResult]   = useState<RetrainResult | null>(null)
  const [errorMsg, setErrorMsg] = useState('')

  if (correctionsPending === 0 && status === 'idle') return null

  const run = async () => {
    setStatus('running')
    setProgress(0)
    setResult(null)
    setErrorMsg('')

    // Animate progress while waiting for API
    const steps = [15, 30, 50, 65, 80, 90]
    let i = 0
    const iv = setInterval(() => {
      if (i < steps.length) setProgress(steps[i++])
      else clearInterval(iv)
    }, 600)

    try {
      const res = await api.post('/validation/retrain', { triggered_by: 'n3_dashboard' })
      clearInterval(iv)
      setProgress(100)
      setResult(res.data)
      setStatus('done')
      queryClient.invalidateQueries({ queryKey: ['chatbotStats'] })
    } catch (e: any) {
      clearInterval(iv)
      setErrorMsg(e?.response?.data?.detail || 'Erreur inconnue')
      setStatus('error')
    }
  }

  const bannerColor =
    status === 'done'    ? 'bg-green-50 border-green-300' :
    status === 'error'   ? 'bg-red-50 border-red-300'     :
    status === 'running' ? 'bg-blue-50 border-blue-300'   :
                           'bg-indigo-50 border-indigo-300'

  const iconColor =
    status === 'done'    ? 'text-green-600'                      :
    status === 'error'   ? 'text-red-600'                        :
    status === 'running' ? 'text-blue-600 animate-pulse'         :
                           'text-indigo-600'

  const iconBg =
    status === 'done'    ? 'bg-green-100'  :
    status === 'error'   ? 'bg-red-100'    :
    status === 'running' ? 'bg-blue-100'   :
                           'bg-indigo-100'

  return (
    <div className={`rounded-xl border p-4 transition-all ${bannerColor}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${iconBg}`}>
            <Brain size={18} className={iconColor} />
          </div>
          <div>
            {status === 'idle' && (
              <>
                <p className="font-semibold text-indigo-800 text-sm">
                  {correctionsPending} correction(s) N3 prête(s) pour le réapprentissage
                </p>
                <p className="text-xs text-indigo-600 mt-0.5">
                  Le pipeline va intégrer les corrections validées dans la base de connaissances RAG.
                  Le LLM lui-même n'est pas modifié — seul le contexte fourni change.
                </p>
              </>
            )}
            {status === 'running' && (
              <>
                <p className="font-semibold text-blue-800 text-sm">Réapprentissage en cours...</p>
                <div className="mt-2 w-64 h-2 bg-blue-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-700"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs text-blue-500 mt-1">{progress}% complété</p>
              </>
            )}
            {status === 'done' && result && (
              <>
                <p className="font-semibold text-green-800 text-sm">
                  ✅ Réapprentissage terminé en {result.duration_seconds}s
                </p>
                <div className="grid grid-cols-2 gap-x-6 mt-2 text-xs text-green-700">
                  <span>• {result.corrections_applied} correction(s) appliquée(s)</span>
                  <span>• {result.kb_chunks_updated} chunks KB mis à jour</span>
                  <span>• {result.trust_scores_updated} trust scores recalculés</span>
                  <span>• {result.new_procedures_drafted} procédures générées</span>
                </div>
              </>
            )}
            {status === 'error' && (
              <>
                <p className="font-semibold text-red-800 text-sm">❌ Erreur lors du réapprentissage</p>
                <p className="text-xs text-red-600 mt-0.5">{errorMsg || 'Vérifiez les logs backend.'}</p>
              </>
            )}
          </div>
        </div>

        <div className="shrink-0">
          {(status === 'idle' || status === 'error') && (
            <button
              onClick={run}
              className="flex items-center gap-1.5 px-4 py-2 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition font-medium shadow-sm"
            >
              <Play size={12} /> Lancer le réapprentissage
            </button>
          )}
          {status === 'running' && (
            <div className="flex items-center gap-2 text-xs text-blue-600 px-3">
              <RefreshCw size={13} className="animate-spin" /> En cours...
            </div>
          )}
          {status === 'done' && (
            <button
              onClick={() => { setStatus('idle'); setResult(null) }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white border border-green-300 text-green-700 rounded-lg hover:bg-green-50 transition"
            >
              <RefreshCw size={12} /> Relancer
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
