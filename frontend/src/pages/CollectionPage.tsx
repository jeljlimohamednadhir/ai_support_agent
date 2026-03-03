import { useState } from 'react'
import { Database, FileText, Upload, RefreshCw, CheckCircle, AlertCircle, Loader2, FolderOpen, Plus } from 'lucide-react'

interface DataSource {
  id: string
  type: 'sql' | 'documents' | 'code'
  name: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  itemsCount: number
  lastUpdated: string
}

export default function CollectionPage() {
  const dataSources: DataSource[] = [
    {
      id: '1',
      type: 'sql',
      name: 'brasil_db.sql',
      status: 'completed',
      itemsCount: 128,
      lastUpdated: '2026-01-09T10:30:00'
    },
    {
      id: '2',
      type: 'documents',
      name: 'Fiches FR (001-999)',
      status: 'completed',
      itemsCount: 51,
      lastUpdated: '2026-01-09T10:35:00'
    },
    {
      id: '3',
      type: 'code',
      name: 'Source Code BRASIL',
      status: 'pending',
      itemsCount: 0,
      lastUpdated: '-'
    }
  ]

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
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Collection de données
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Gérez les sources de données pour l'apprentissage de l'assistant IA
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Tables SQL</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">128</p>
              </div>
              <Database className="w-10 h-10 text-blue-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-purple-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Documents</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">51</p>
              </div>
              <FileText className="w-10 h-10 text-purple-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Fichiers code</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">0</p>
              </div>
              <FolderOpen className="w-10 h-10 text-green-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-orange-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total documents</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">179</p>
              </div>
              <CheckCircle className="w-10 h-10 text-orange-500 opacity-20" />
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <button className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-lg">
              <Database className="w-6 h-6" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-lg">Importer SQL</p>
              <p className="text-sm text-blue-100">Schémas et tables</p>
            </div>
          </button>

          <button className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-lg">
              <FileText className="w-6 h-6" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-lg">Importer documents</p>
              <p className="text-sm text-purple-100">Word, PDF, Markdown</p>
            </div>
          </button>

          <button className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-lg">
              <FolderOpen className="w-6 h-6" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-lg">Importer code</p>
              <p className="text-sm text-green-100">Python, JavaScript, Java</p>
            </div>
          </button>
        </div>

        {/* Data Sources List */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Sources de données
              </h2>
              <button className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
                <Plus className="w-4 h-4" />
                Nouvelle source
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
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(source.status)}
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {getStatusLabel(source.status)}
                      </span>
                    </div>
                    <button className="p-2 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors">
                      <RefreshCw className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    </button>
                  </div>
                </div>

                {/* Progress bar for processing */}
                {source.status === 'processing' && (
                  <div className="mt-4">
                    <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-600 rounded-full animate-pulse" style={{ width: '65%' }}></div>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Traitement en cours... 65%
                    </p>
                  </div>
                )}
              </div>
            ))}
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
