import { useState, useEffect } from 'react'
import { AlertCircle, ExternalLink, RefreshCw } from 'lucide-react'

export default function ClassificationPage() {
  const [streamlitAvailable, setStreamlitAvailable] = useState(false)
  const [checking, setChecking] = useState(true)

  const checkStreamlit = async () => {
    try {
      const response = await fetch('http://localhost:8501/healthz', {
        signal: AbortSignal.timeout(2000)
      })
      setStreamlitAvailable(response.ok)
    } catch (err) {
      setStreamlitAvailable(false)
    } finally {
      setChecking(false)
    }
  }

  useEffect(() => {
    checkStreamlit()
  }, [])

  if (checking) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Vérification de Streamlit...</p>
        </div>
      </div>
    )
  }

  if (!streamlitAvailable) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="max-w-md p-6 bg-card border border-border rounded-lg shadow-sm">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold mb-2">Interface Streamlit non disponible</h3>
              <p className="text-sm text-muted-foreground mb-4">
                L'interface de classification ML n'est pas accessible. Assurez-vous que Streamlit est démarré.
              </p>
              <div className="bg-muted p-3 rounded text-xs font-mono mb-4">
                <p># Terminal séparé :</p>
                <p>cd try1</p>
                <p>.\scripts\start_ui.ps1</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={checkStreamlit}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90 transition-colors flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Réessayer
                </button>
                <a
                  href="http://localhost:8501"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 border border-border rounded-md text-sm hover:bg-accent transition-colors flex items-center gap-2"
                >
                  <ExternalLink className="w-4 h-4" />
                  Ouvrir dans un nouvel onglet
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full w-full flex flex-col">
      {/* Header avec info */}
      <div className="bg-card border-b border-border px-6 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Classification ML & Gestion</h1>
            <p className="text-sm text-muted-foreground">
              Interface GenIQ : Classification automatique, entraînement du modèle, synchronisation SharePoint
            </p>
          </div>
          <a
            href="http://localhost:8501"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-md hover:bg-accent transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            Ouvrir en plein écran
          </a>
        </div>
      </div>

      {/* Iframe Streamlit */}
      <div className="flex-1 relative">
        <iframe
          src="http://localhost:8501?embed=true"
          className="absolute inset-0 w-full h-full border-0"
          title="Interface Classification ML"
          allow="camera; microphone; clipboard-read; clipboard-write"
        />
      </div>
    </div>
  )
}
