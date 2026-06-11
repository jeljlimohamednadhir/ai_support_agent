import React, { useState, useEffect, useRef } from 'react'
import { Database, FileText, Upload, RefreshCw, CheckCircle, AlertCircle, Loader2, FolderOpen, Plus, Zap, FileSpreadsheet, ScrollText } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { usePageStateStore } from '../stores/pageStateStore'

interface DataSource {
  id: string
  type: 'sql' | 'documents' | 'code'
  name: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  itemsCount: number
  lastUpdated: string
  progress?: number
  error?: string
}

interface KnowledgeStats {
  total_documents?: number
  sql_documents?: number
  doc_documents?: number
  code_documents?: number
  collections?: { name: string; count: number }[]
}

const API_BASE = '/api/v1'

const DEFAULT_DATA_SOURCES: DataSource[] = [
  { id: '1', type: 'sql', name: 'brasil_db.sql', status: 'completed', itemsCount: 424, lastUpdated: new Date().toLocaleDateString('fr-FR') },
  { id: '2', type: 'documents', name: 'Fiches FR (001-999)', status: 'completed', itemsCount: 48, lastUpdated: new Date().toLocaleDateString('fr-FR') },
  { id: '3', type: 'code', name: 'Source Code BRASIL', status: 'pending', itemsCount: 0, lastUpdated: '-' },
]

export default function CollectionPage() {
  const { collection, setCollectionSources, setCollectionStats } = usePageStateStore()

  // Initialise from store on first render; fall back to defaults if store is empty
  const dataSources: DataSource[] = (collection.dataSources.length > 0
    ? collection.dataSources
    : DEFAULT_DATA_SOURCES) as DataSource[]

  const setDataSources = (updater: DataSource[] | ((prev: DataSource[]) => DataSource[])) => {
    const next = typeof updater === 'function' ? updater(dataSources) : updater
    setCollectionSources(next as any)
  }

  const stats = collection.stats as KnowledgeStats
  const setStats = (data: KnowledgeStats) => setCollectionStats(data as any)
  const [loadingStats, setLoadingStats] = useState(false)

  const sqlFileRef = useRef<HTMLInputElement>(null)
  const docFileRef = useRef<HTMLInputElement>(null)
  const codeFileRef = useRef<HTMLInputElement>(null)
  const frRagFileRef = useRef<HTMLInputElement>(null)
  const ticketsRagFileRef = useRef<HTMLInputElement>(null)
  const logsRagFileRef = useRef<HTMLInputElement>(null)

  type RagStatus = 'idle' | 'uploading' | 'indexing' | 'done' | 'error'
  const [ragStatus, setRagStatus] = useState<{ fr: RagStatus; tickets: RagStatus; logs: RagStatus }>(
    { fr: 'idle', tickets: 'idle', logs: 'idle' }
  )
  const [ragCounts, setRagCounts] = useState<{ fr: number; tickets: number; logs: number }>(
    { fr: 0, tickets: 0, logs: 0 }
  )

  const triggerRagIndex = async (source: 'fr' | 'tickets' | 'logs', logFilePath?: string) => {
    setRagStatus(prev => ({ ...prev, [source]: 'indexing' }))
    try {
      const body: Record<string, string> = { source }
      if (logFilePath) body.log_file = logFilePath
      const response = await fetch(`${API_BASE}/classification-ml/index-rag`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' } as HeadersInit,
        body: JSON.stringify(body),
      })
      if (response.ok) {
        const data = await response.json()
        const count = data.indexed ?? data.count ?? 0
        setRagCounts(prev => ({ ...prev, [source]: count }))
        setRagStatus(prev => ({ ...prev, [source]: 'done' }))
        const labels: Record<string, string> = { fr: 'Fiches FR', tickets: 'Tickets', logs: 'Logs' }
        toast.success(`${labels[source]}: ${count} éléments indexés dans le RAG`)
        setTimeout(() => setRagStatus(prev => ({ ...prev, [source]: 'idle' })), 4000)
      } else {
        const err = await response.json()
        setRagStatus(prev => ({ ...prev, [source]: 'error' }))
        toast.error(err.detail || `Erreur indexation ${source}`)
        setTimeout(() => setRagStatus(prev => ({ ...prev, [source]: 'idle' })), 3000)
      }
    } catch {
      setRagStatus(prev => ({ ...prev, [source]: 'error' }))
      toast.error('Connexion impossible')
      setTimeout(() => setRagStatus(prev => ({ ...prev, [source]: 'idle' })), 3000)
    }
  }

  const handleRagFileUpload = async (
    source: 'fr' | 'tickets' | 'logs',
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    // Tickets CSV: handled separately via the existing /upload CSV flow
    if (source === 'tickets') {
      toast('Pour les tickets, utilisez "Importer CSV" en haut puis "Entraîner"', { icon: 'ℹ️' })
      event.target.value = ''
      return
    }

    setRagStatus(prev => ({ ...prev, [source]: 'uploading' }))
    const formData = new FormData()
    Array.from(files).forEach(file => formData.append('files', file))

    try {
      // Step 1: Save files server-side in the correct pipeline folder
      const uploadResp = await fetch(
        `${API_BASE}/classification-ml/upload-source?source=${source}`,
        {
          method: 'POST',
          headers: getAuthHeaders() as HeadersInit,
          body: formData,
        }
      )
      if (!uploadResp.ok) {
        const err = await uploadResp.json().catch(() => ({}))
        setRagStatus(prev => ({ ...prev, [source]: 'error' }))
        toast.error(err.detail || `Erreur upload ${source}`)
        setTimeout(() => setRagStatus(prev => ({ ...prev, [source]: 'idle' })), 3000)
        event.target.value = ''
        return
      }
      const uploadData = await uploadResp.json()
      toast.success(`${uploadData.saved} fichier(s) sauvegardé(s) → indexation en cours...`)

      // Step 2: Trigger the RAG pipeline, passing the first saved file path
      const firstPath: string | undefined = uploadData.paths?.[0]
      await triggerRagIndex(source, firstPath)
    } catch {
      setRagStatus(prev => ({ ...prev, [source]: 'error' }))
      toast.error('Connexion impossible')
      setTimeout(() => setRagStatus(prev => ({ ...prev, [source]: 'idle' })), 3000)
    }
    event.target.value = ''
  }

  useEffect(() => {
    loadStats()
  }, [])

  const getAuthHeaders = () => {
    const token = localStorage.getItem('auth_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  const loadStats = async () => {
    setLoadingStats(true)
    try {
      const response = await fetch(`${API_BASE}/knowledge/stats`, {
        headers: getAuthHeaders() as HeadersInit
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
        // Update source counts from real stats
        setDataSources(dataSources.map(src => {
          if (src.type === 'sql') return { ...src, itemsCount: data.sql_documents ?? data.total_documents ?? src.itemsCount }
          if (src.type === 'documents') return { ...src, itemsCount: data.doc_documents ?? src.itemsCount }
          return src
        }))
      }
    } catch (err) {
      console.error('Failed to load knowledge stats:', err)
    } finally {
      setLoadingStats(false)
    }
  }

  const updateSourceStatus = (id: string, status: DataSource['status'], extra: Partial<DataSource> = {}) => {
    setDataSources(dataSources.map(src => src.id === id ? { ...src, status, ...extra } : src))
  }

  const handleSQLImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    updateSourceStatus('1', 'processing', { name: file.name, progress: 10 })

    const formData = new FormData()
    formData.append('file', file)

    try {
      updateSourceStatus('1', 'processing', { progress: 40 })
      const response = await fetch(`${API_BASE}/collector/sql`, {
        method: 'POST',
        headers: getAuthHeaders() as HeadersInit,
        body: formData
      })
      if (response.ok) {
        const data = await response.json()
        updateSourceStatus('1', 'completed', {
          itemsCount: data.count ?? data.indexed ?? 0,
          lastUpdated: new Date().toISOString(),
          progress: 100
        })
        toast.success(`SQL importé: ${data.count ?? data.indexed ?? 0} éléments indexés`)
        await loadStats()
      } else {
        const err = await response.json()
        updateSourceStatus('1', 'failed', { error: err.detail || 'Erreur import SQL' })
        toast.error(err.detail || 'Erreur lors de l\'import SQL')
      }
    } catch (err) {
      updateSourceStatus('1', 'failed', { error: 'Connexion impossible' })
      toast.error('Impossible de contacter le serveur')
    }
    // Reset input
    event.target.value = ''
  }

  const handleDocImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    const names = Array.from(files).map(f => f.name).join(', ')
    updateSourceStatus('2', 'processing', { name: names.length > 40 ? `${files.length} fichiers` : names, progress: 10 })

    const formData = new FormData()
    Array.from(files).forEach(file => formData.append('files', file))

    try {
      updateSourceStatus('2', 'processing', { progress: 40 })
      const response = await fetch(`${API_BASE}/collector/documents`, {
        method: 'POST',
        headers: getAuthHeaders() as HeadersInit,
        body: formData
      })
      if (response.ok) {
        const data = await response.json()
        updateSourceStatus('2', 'completed', {
          itemsCount: data.count ?? data.indexed ?? files.length,
          lastUpdated: new Date().toISOString(),
          progress: 100
        })
        toast.success(`${files.length} document(s) importé(s) avec succès`)
        await loadStats()
      } else {
        const err = await response.json()
        updateSourceStatus('2', 'failed', { error: err.detail || 'Erreur import documents' })
        toast.error(err.detail || 'Erreur lors de l\'import des documents')
      }
    } catch (err) {
      updateSourceStatus('2', 'failed', { error: 'Connexion impossible' })
      toast.error('Impossible de contacter le serveur')
    }
    event.target.value = ''
  }

  const handleCodeImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    updateSourceStatus('3', 'processing', { name: `${files.length} fichier(s) de code`, progress: 10 })

    const formData = new FormData()
    Array.from(files).forEach(file => formData.append('files', file))

    try {
      updateSourceStatus('3', 'processing', { progress: 40 })
      const response = await fetch(`${API_BASE}/collector/code`, {
        method: 'POST',
        headers: getAuthHeaders() as HeadersInit,
        body: formData
      })
      if (response.ok) {
        const data = await response.json()
        updateSourceStatus('3', 'completed', {
          itemsCount: data.count ?? data.indexed ?? files.length,
          lastUpdated: new Date().toISOString(),
          progress: 100
        })
        toast.success(`Code importé: ${data.count ?? data.indexed ?? files.length} fichiers indexés`)
        await loadStats()
      } else {
        const err = await response.json()
        updateSourceStatus('3', 'failed', { error: err.detail || 'Erreur import code' })
        toast.error(err.detail || 'Erreur lors de l\'import du code')
      }
    } catch (err) {
      updateSourceStatus('3', 'failed', { error: 'Connexion impossible' })
      toast.error('Impossible de contacter le serveur')
    }
    event.target.value = ''
  }

  const handleRefresh = async (sourceId: string) => {
    const source = dataSources.find(s => s.id === sourceId)
    if (!source) return
    updateSourceStatus(sourceId, 'processing', { progress: 50 })
    try {
      const response = await fetch(`${API_BASE}/knowledge/reindex`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' } as HeadersInit,
        body: JSON.stringify({ source_type: source.type })
      })
      if (response.ok) {
        updateSourceStatus(sourceId, 'completed', { lastUpdated: new Date().toISOString(), progress: 100 })
        toast.success('Source réindexée avec succès')
        await loadStats()
      } else {
        updateSourceStatus(sourceId, source.status, { progress: undefined })
        toast.error('Erreur lors de la réindexation')
      }
    } catch {
      updateSourceStatus(sourceId, source.status, { progress: undefined })
      toast.error('Connexion impossible')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-600" />
      default:
        return <AlertCircle className="w-5 h-5 text-gray-400" />
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Complété'
      case 'processing':
        return 'En cours'
      case 'failed':
        return 'Échoué'
      case 'pending':
        return 'En attente'
      default:
        return status
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'sql':
        return <Database className="w-6 h-6 text-blue-600" />
      case 'documents':
        return <FileText className="w-6 h-6 text-purple-600" />
      case 'code':
        return <FolderOpen className="w-6 h-6 text-green-600" />
      default:
        return null
    }
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'sql':
        return 'Base de données SQL'
      case 'documents':
        return 'Documents Word/PDF'
      case 'code':
        return 'Code source'
      default:
        return type
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 p-8">
      {/* Hidden file inputs */}
      <input ref={sqlFileRef} type="file" accept=".sql" className="hidden" onChange={handleSQLImport} />
      <input ref={docFileRef} type="file" accept=".pdf,.doc,.docx,.md,.txt" multiple className="hidden" onChange={handleDocImport} />
      <input ref={codeFileRef} type="file" accept=".py,.js,.ts,.java,.cs,.cpp,.go" multiple className="hidden" onChange={handleCodeImport} />
      {/* RAG source inputs */}
      <input ref={frRagFileRef} type="file" accept=".doc,.docx,.pdf" multiple className="hidden" onChange={(e) => handleRagFileUpload('fr', e)} />
      <input ref={ticketsRagFileRef} type="file" accept=".csv" multiple className="hidden" onChange={(e) => handleRagFileUpload('tickets', e)} />
      <input ref={logsRagFileRef} type="file" accept=".log,.txt,.gz" multiple className="hidden" onChange={(e) => handleRagFileUpload('logs', e)} />

      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Collection de données
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Gérez les sources de données pour l'apprentissage de l'assistant IA
            </p>
          </div>
          <button
            onClick={loadStats}
            disabled={loadingStats}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loadingStats ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Tables SQL</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                  {loadingStats ? '...' : (stats.sql_documents ?? dataSources.find(s => s.type === 'sql')?.itemsCount ?? 0)}
                </p>
              </div>
              <Database className="w-10 h-10 text-blue-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-purple-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Documents</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                  {loadingStats ? '...' : (stats.doc_documents ?? dataSources.find(s => s.type === 'documents')?.itemsCount ?? 0)}
                </p>
              </div>
              <FileText className="w-10 h-10 text-purple-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Fichiers code</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                  {loadingStats ? '...' : (stats.code_documents ?? dataSources.find(s => s.type === 'code')?.itemsCount ?? 0)}
                </p>
              </div>
              <FolderOpen className="w-10 h-10 text-green-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-orange-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total indexés</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                  {loadingStats ? '...' : (stats.total_documents ?? dataSources.reduce((sum, s) => sum + s.itemsCount, 0))}
                </p>
              </div>
              <CheckCircle className="w-10 h-10 text-orange-500 opacity-20" />
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <button
            onClick={() => sqlFileRef.current?.click()}
            className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-4"
          >
            <div className="p-3 bg-white/20 rounded-lg">
              <Database className="w-6 h-6" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-lg">Importer SQL</p>
              <p className="text-sm text-blue-100">Fichier .sql — schémas et tables</p>
            </div>
            <Upload className="w-5 h-5 ml-auto opacity-60" />
          </button>

          <button
            onClick={() => docFileRef.current?.click()}
            className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-4"
          >
            <div className="p-3 bg-white/20 rounded-lg">
              <FileText className="w-6 h-6" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-lg">Importer documents</p>
              <p className="text-sm text-purple-100">Word, PDF, Markdown, TXT</p>
            </div>
            <Upload className="w-5 h-5 ml-auto opacity-60" />
          </button>

          <button
            onClick={() => codeFileRef.current?.click()}
            className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-4"
          >
            <div className="p-3 bg-white/20 rounded-lg">
              <FolderOpen className="w-6 h-6" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-lg">Importer code</p>
              <p className="text-sm text-green-100">Python, JS, Java, TypeScript</p>
            </div>
            <Upload className="w-5 h-5 ml-auto opacity-60" />
          </button>
        </div>

        {/* Data Sources List */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Sources de données
              </h2>
              <button
                onClick={() => docFileRef.current?.click()}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Ajouter des fichiers
              </button>
            </div>
          </div>

          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {dataSources.map((source) => (
              <div
                key={source.id}
                className="p-6 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
                      {getTypeIcon(source.type)}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                        {source.name}
                      </h3>
                      <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                        <span>{getTypeLabel(source.type)}</span>
                        <span>•</span>
                        <span>{source.itemsCount} éléments</span>
                        <span>•</span>
                        <span>
                          {source.lastUpdated !== '-'
                            ? new Date(source.lastUpdated).toLocaleString('fr-FR')
                            : 'Non collecté'}
                        </span>
                      </div>
                      {source.error && (
                        <p className="text-xs text-red-500 dark:text-red-400 mt-1">{source.error}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(source.status)}
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {getStatusLabel(source.status)}
                      </span>
                    </div>
                    <button
                      onClick={() => handleRefresh(source.id)}
                      disabled={source.status === 'processing'}
                      title="Réindexer cette source"
                      className="p-2 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-40"
                    >
                      <RefreshCw className={`w-5 h-5 text-gray-600 dark:text-gray-400 ${source.status === 'processing' ? 'animate-spin' : ''}`} />
                    </button>
                    <button
                      onClick={() => {
                        if (source.type === 'sql') sqlFileRef.current?.click()
                        else if (source.type === 'documents') docFileRef.current?.click()
                        else codeFileRef.current?.click()
                      }}
                      title="Importer de nouveaux fichiers"
                      className="p-2 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                    >
                      <Upload className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    </button>
                  </div>
                </div>

                {/* Progress bar for processing */}
                {source.status === 'processing' && (
                  <div className="mt-4">
                    <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-600 rounded-full transition-all duration-500"
                        style={{ width: `${source.progress ?? 50}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Traitement en cours... {source.progress ?? 50}%
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* RAG Sources Injection */}
        <div className="mt-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center gap-3">
            <Zap className="w-5 h-5 text-amber-500" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Injection RAG — Sources métier</h2>
            <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">Indexez vos données dans le moteur de recherche vectoriel</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-6">

            {/* FR Card */}
            {(() => {
              const s = ragStatus.fr
              const isActive = s === 'uploading' || s === 'indexing'
              return (
                <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-5 flex flex-col gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                      <FileText className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-white">Fiches de Résolution (FR)</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">.docx / .pdf</p>
                    </div>
                  </div>
                  {ragCounts.fr > 0 && (
                    <p className="text-xs text-green-600 dark:text-green-400">{ragCounts.fr} éléments indexés</p>
                  )}
                  <div className="flex gap-2 mt-auto">
                    <button
                      onClick={() => frRagFileRef.current?.click()}
                      disabled={isActive}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-purple-300 dark:border-purple-700 text-purple-700 dark:text-purple-300 rounded-lg hover:bg-purple-50 dark:hover:bg-purple-900/20 disabled:opacity-40 text-sm transition-colors"
                    >
                      <Upload className="w-4 h-4" />
                      {s === 'uploading' ? 'Upload...' : 'Ajouter fichiers'}
                    </button>
                    <button
                      onClick={() => triggerRagIndex('fr')}
                      disabled={isActive}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg disabled:opacity-40 text-sm transition-colors"
                    >
                      {s === 'indexing' ? <Loader2 className="w-4 h-4 animate-spin" /> : s === 'done' ? <CheckCircle className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
                      {s === 'indexing' ? 'Indexation...' : s === 'done' ? 'Indexé ✓' : 'Indexer dans RAG'}
                    </button>
                  </div>
                </div>
              )
            })()}

            {/* Tickets CSV Card */}
            {(() => {
              const s = ragStatus.tickets
              const isActive = s === 'uploading' || s === 'indexing'
              return (
                <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-5 flex flex-col gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                      <FileSpreadsheet className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-white">Tickets CSV</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">.csv — tickets d'incidents</p>
                    </div>
                  </div>
                  {ragCounts.tickets > 0 && (
                    <p className="text-xs text-green-600 dark:text-green-400">{ragCounts.tickets} tickets indexés</p>
                  )}
                  <div className="flex gap-2 mt-auto">
                    <button
                      onClick={() => ticketsRagFileRef.current?.click()}
                      disabled={isActive}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-40 text-sm transition-colors"
                    >
                      <Upload className="w-4 h-4" />
                      {s === 'uploading' ? 'Upload...' : 'Ajouter fichiers'}
                    </button>
                    <button
                      onClick={() => triggerRagIndex('tickets')}
                      disabled={isActive}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-40 text-sm transition-colors"
                    >
                      {s === 'indexing' ? <Loader2 className="w-4 h-4 animate-spin" /> : s === 'done' ? <CheckCircle className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
                      {s === 'indexing' ? 'Indexation...' : s === 'done' ? 'Indexé ✓' : 'Indexer dans RAG'}
                    </button>
                  </div>
                </div>
              )
            })()}

            {/* Logs Card */}
            {(() => {
              const s = ragStatus.logs
              const isActive = s === 'uploading' || s === 'indexing'
              return (
                <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-5 flex flex-col gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                      <ScrollText className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-white">Logs applicatifs</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">.log / .txt — traces BRASIL</p>
                    </div>
                  </div>
                  {ragCounts.logs > 0 && (
                    <p className="text-xs text-green-600 dark:text-green-400">{ragCounts.logs} patterns indexés</p>
                  )}
                  <div className="flex gap-2 mt-auto">
                    <button
                      onClick={() => logsRagFileRef.current?.click()}
                      disabled={isActive}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-orange-300 dark:border-orange-700 text-orange-700 dark:text-orange-300 rounded-lg hover:bg-orange-50 dark:hover:bg-orange-900/20 disabled:opacity-40 text-sm transition-colors"
                    >
                      <Upload className="w-4 h-4" />
                      {s === 'uploading' ? 'Upload...' : 'Ajouter fichiers'}
                    </button>
                    <button
                      onClick={() => triggerRagIndex('logs')}
                      disabled={isActive}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg disabled:opacity-40 text-sm transition-colors"
                    >
                      {s === 'indexing' ? <Loader2 className="w-4 h-4 animate-spin" /> : s === 'done' ? <CheckCircle className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
                      {s === 'indexing' ? 'Indexation...' : s === 'done' ? 'Indexé ✓' : 'Indexer dans RAG'}
                    </button>
                  </div>
                </div>
              )
            })()}

          </div>
        </div>

        {/* Info Box */}
        <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <AlertCircle className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h3 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">
                À propos de la collection de données
              </h3>
              <p className="text-sm text-blue-800 dark:text-blue-300 mb-3">
                Les données collectées sont utilisées pour entraîner l'assistant IA et améliorer
                ses réponses. Chaque source est analysée et indexée dans le système RAG (Retrieval-Augmented Generation).
              </p>
              <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1 list-disc list-inside">
                <li>Les fichiers SQL sont parsés pour extraire les schémas de tables</li>
                <li>Les documents sont convertis en texte et segmentés</li>
                <li>Le code source est analysé pour extraire les fonctions et classes</li>
                <li>Toutes les données sont vectorisées avec des embeddings multilingues</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
