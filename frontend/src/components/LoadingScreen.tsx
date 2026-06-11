import { useEffect, useState } from 'react'
import { Loader2, CheckCircle2, XCircle, Clock, Bot } from 'lucide-react'

interface ServiceStatus {
  app: boolean
  qdrant: boolean
  jira: boolean
  neo4j: boolean
}

interface ReadyResponse {
  ready: boolean
  services: ServiceStatus
  message: string
}

export default function LoadingScreen({ onReady }: { onReady: () => void }) {
  const [status, setStatus] = useState<ReadyResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [robotExpression, setRobotExpression] = useState(0)

  useEffect(() => {
    const startTime = Date.now()
    
    // Timer pour afficher le temps écoulé
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000))
    }, 1000)
    
    // Animation du robot - change d'expression toutes les 2 secondes
    const expressionTimer = setInterval(() => {
      setRobotExpression(prev => (prev + 1) % 4)
    }, 2000)
    
    // Polling pour vérifier si l'app est prête
    const checkReady = async () => {
      try {
        const response = await fetch('/ready', {
          signal: AbortSignal.timeout(3000)
        })
        const data: ReadyResponse = await response.json()
        setStatus(data)
        setError(null)
        
        if (data.ready) {
          clearInterval(checkInterval)
          clearInterval(timer)
          onReady()
        }
      } catch (err) {
        setError(null)
        console.log('Backend not ready yet, retrying...')
      }
    }

    // Vérifier immédiatement puis toutes les 2 secondes
    checkReady()
    const checkInterval = setInterval(checkReady, 2000)

    return () => {
      clearInterval(checkInterval)
      clearInterval(timer)
      clearInterval(expressionTimer)
    }
  }, [onReady])

  const getServiceIcon = (ready: boolean) => {
    if (ready) return <CheckCircle2 className="w-5 h-5 text-green-500" />
    return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
  }

  const getServiceLabel = (service: keyof ServiceStatus) => {
    const labels = {
      app: 'Application Backend',
      qdrant: 'Base Vectorielle (Qdrant)',
      jira: 'Connexion Jira',
      neo4j: 'Graphe de Connaissance (Neo4j)'
    }
    return labels[service]
  }

  // Robot animé avec expressions (design BRASIL AI)
  const RobotFace = () => {
    const expressions = [
      // Normal - yeux ouverts rectangulaires
      { leftX: 32, rightX: 58, eyeWidth: 10, eyeHeight: 12, wink: false },
      // Wink - œil gauche fermé
      { leftX: 32, rightX: 58, eyeWidth: 10, eyeHeight: 2, wink: true },
      // Regarde à gauche
      { leftX: 28, rightX: 54, eyeWidth: 10, eyeHeight: 12, wink: false },
      // Regarde à droite
      { leftX: 36, rightX: 62, eyeWidth: 10, eyeHeight: 12, wink: false }
    ]

    const expr = expressions[robotExpression]

    return (
      <svg viewBox="0 0 120 120" className="w-20 h-20">
        {/* Tête du robot - forme carrée arrondie */}
        <rect x="30" y="45" width="60" height="50" rx="10" 
              fill="none" stroke="currentColor" strokeWidth="4" 
              className="text-blue-500" />
        
        {/* Antenne avec boule */}
        <line x1="60" y1="45" x2="60" y2="25" 
              stroke="currentColor" strokeWidth="4" 
              className="text-blue-500" />
        <circle cx="60" cy="25" r="5" 
                fill="currentColor" 
                className="text-blue-500" />
        
        {/* Œil gauche */}
        <rect 
          x={expr.leftX} 
          y={expr.wink ? 63 : 58} 
          width={expr.eyeWidth} 
          height={expr.wink ? expr.eyeHeight : expr.eyeHeight} 
          rx="2" 
          fill="currentColor" 
          className="text-blue-500 transition-all duration-300" 
        />
        
        {/* Œil droit */}
        <rect 
          x={expr.rightX} 
          y={58} 
          width={expr.eyeWidth} 
          height={expr.eyeHeight} 
          rx="2" 
          fill="currentColor" 
          className="text-blue-500 transition-all duration-300" 
        />
        
        {/* Bouche - ligne horizontale */}
        <line x1="40" y1="80" x2="80" y2="80" 
              stroke="currentColor" strokeWidth="3" 
              strokeLinecap="round"
              className="text-blue-500" />
      </svg>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8">
        {/* Header avec Robot */}
        <div className="text-center mb-8">
          <div className="relative inline-flex items-center justify-center w-32 h-32 mb-4">
            {/* Cercle qui tourne en arrière-plan */}
            <div className="absolute inset-0 border-4 border-transparent border-t-blue-500 border-r-purple-500 rounded-full animate-spin"></div>
            {/* Robot animé au centre */}
            <div className="z-10">
              <RobotFace />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            BRASIL AI Assistant
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Initialisation des services...
          </p>
        </div>

        {/* Services Status */}
        {status ? (
          <div className="space-y-3 mb-6">
            {(Object.keys(status.services) as Array<keyof ServiceStatus>).map((service) => (
              <div
                key={service}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
              >
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {getServiceLabel(service)}
                </span>
                {getServiceIcon(status.services[service])}
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3 mb-6">
            <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Connexion au backend...
              </span>
              <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-4">
            <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* Progress Message */}
        {!status ? (
          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              En attente du démarrage du backend...
            </p>
            <div className="flex items-center justify-center gap-2 text-xs text-gray-500 dark:text-gray-500">
              <Clock className="w-4 h-4" />
              <span>{elapsed}s écoulées</span>
            </div>
          </div>
        ) : status && !status.ready ? (
          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              {status.message}
            </p>
            <div className="flex items-center justify-center gap-2 text-xs text-gray-500 dark:text-gray-500">
              <Clock className="w-4 h-4" />
              <span>{elapsed}s écoulées</span>
            </div>
          </div>
        ) : null}

        {/* Ready State */}
        {status && status.ready && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
              <span className="text-sm font-medium text-green-700 dark:text-green-400">
                Tous les services sont prêts !
              </span>
            </div>
          </div>
        )}

        {/* Info Footer */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-center text-gray-500 dark:text-gray-500">
            Cette étape peut prendre jusqu'à 3 minutes lors du premier démarrage
            en raison de l'initialisation de la base vectorielle Qdrant.
          </p>
        </div>
      </div>
    </div>
  )
}
