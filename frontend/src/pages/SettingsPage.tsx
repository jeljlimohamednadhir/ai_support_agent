import { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import { usePageStateStore } from '../stores/pageStateStore'

interface LLMConfig {
  provider: string
  model: string
  api_key?: string
  temperature: number
  max_tokens: number
}

interface DatabaseConfig {
  neo4j_uri: string
  neo4j_user: string
  neo4j_password?: string
  qdrant_host: string
  qdrant_port: number
  postgres_uri?: string
}

interface UIPreferences {
  theme: string
  language: string
  items_per_page: number
  enable_notifications: boolean
}

interface SystemConfiguration {
  llm: LLMConfig
  database: DatabaseConfig
  ui_preferences: UIPreferences
}

export default function SettingsPage() {
  const [config, setConfig] = useState<SystemConfiguration>({
    llm: {
      provider: 'groq',
      model: 'llama-3.3-70b-versatile',
      temperature: 0.7,
      max_tokens: 2000
    },
    database: {
      neo4j_uri: 'bolt://localhost:7687',
      neo4j_user: 'neo4j',
      qdrant_host: 'localhost',
      qdrant_port: 6333
    },
    ui_preferences: {
      theme: 'light',
      language: 'fr',
      items_per_page: 20,
      enable_notifications: true
    }
  })
  
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // Persisted tab state — survives navigation
  const { settings, setSettingsActiveTab } = usePageStateStore()
  const activeTab = settings.activeTab
  const setActiveTab = setSettingsActiveTab

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/config/')
      if (response.ok) {
        const data = await response.json()
        setConfig(data)
      } else {
        toast.error('Erreur lors du chargement de la configuration')
      }
    } catch (error) {
      console.error('Error loading config:', error)
      toast.error('Impossible de charger la configuration')
    } finally {
      setLoading(false)
    }
  }

  const saveConfig = async () => {
    setSaving(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/config/bulk', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
      })
      
      if (response.ok) {
        toast.success('Configuration enregistrée avec succès')
      } else {
        const error = await response.json()
        toast.error(`Erreur: ${error.detail || 'Échec de l\'enregistrement'}`)
      }
    } catch (error) {
      console.error('Error saving config:', error)
      toast.error('Impossible d\'enregistrer la configuration')
    } finally {
      setSaving(false)
    }
  }

  const resetConfig = async () => {
    if (!confirm('Êtes-vous sûr de vouloir réinitialiser la configuration ?')) {
      return
    }
    
    setSaving(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/config/reset', {
        method: 'POST'
      })
      
      if (response.ok) {
        toast.success('Configuration réinitialisée')
        await loadConfig()
      } else {
        toast.error('Erreur lors de la réinitialisation')
      }
    } catch (error) {
      console.error('Error resetting config:', error)
      toast.error('Impossible de réinitialiser la configuration')
    } finally {
      setSaving(false)
    }
  }

  const updateLLMConfig = (field: keyof LLMConfig, value: any) => {
    setConfig(prev => ({
      ...prev,
      llm: { ...prev.llm, [field]: value }
    }))
  }

  const updateDatabaseConfig = (field: keyof DatabaseConfig, value: any) => {
    setConfig(prev => ({
      ...prev,
      database: { ...prev.database, [field]: value }
    }))
  }

  const updateUIPreferences = (field: keyof UIPreferences, value: any) => {
    setConfig(prev => ({
      ...prev,
      ui_preferences: { ...prev.ui_preferences, [field]: value }
    }))
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="text-gray-500">Chargement de la configuration...</div>
      </div>
    )
  }

  return (
    <div className="p-8 min-h-screen dark:bg-gray-900">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Paramètres</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">Gérez la configuration du système</p>
      </div>
      
      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('llm')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'llm'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300'
            }`}
          >
            LLM & IA
          </button>
          <button
            onClick={() => setActiveTab('database')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'database'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Bases de données
          </button>
          <button
            onClick={() => setActiveTab('ui')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'ui'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Interface utilisateur
          </button>
        </nav>
      </div>

      <div className="max-w-3xl">
        {/* LLM Configuration */}
        {activeTab === 'llm' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
            <div>
              <h2 className="text-xl font-semibold dark:text-white mb-4">Configuration LLM</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Configurez le fournisseur et le modèle de langage utilisé par l'assistant IA
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Fournisseur LLM
                </label>
                <select
                  value={config.llm.provider}
                  onChange={(e) => updateLLMConfig('provider', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="groq">Groq</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Modèle
                </label>
                <select
                  value={config.llm.model}
                  onChange={(e) => updateLLMConfig('model', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {config.llm.provider === 'groq' && (
                    <>
                      <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
                      <option value="mixtral-8x7b-32768">Mixtral 8x7B</option>
                    </>
                  )}
                  {config.llm.provider === 'openai' && (
                    <>
                      <option value="gpt-4-turbo">GPT-4 Turbo</option>
                      <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                    </>
                  )}
                  {config.llm.provider === 'anthropic' && (
                    <>
                      <option value="claude-3-opus">Claude 3 Opus</option>
                      <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                    </>
                  )}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Clé API (optionnel)
                </label>
                <input
                  type="password"
                  value={config.llm.api_key || ''}
                  onChange={(e) => updateLLMConfig('api_key', e.target.value)}
                  placeholder="Laisser vide pour utiliser les variables d'environnement"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Température: {config.llm.temperature}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={config.llm.temperature}
                  onChange={(e) => updateLLMConfig('temperature', parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                  <span>Précis (0)</span>
                  <span>Créatif (2)</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Tokens maximum
                </label>
                <input
                  type="number"
                  min="100"
                  max="32000"
                  value={config.llm.max_tokens}
                  onChange={(e) => updateLLMConfig('max_tokens', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Database Configuration */}
        {activeTab === 'database' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
            <div>
              <h2 className="text-xl font-semibold dark:text-white mb-4">Configuration des bases de données</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Configurez les connexions à Neo4j, Qdrant et PostgreSQL
              </p>
            </div>

            <div className="space-y-6">
              {/* Neo4j */}
              <div className="border-l-4 border-primary-500 pl-4">
                <h3 className="font-medium text-gray-900 dark:text-white mb-3">Neo4j (Knowledge Graph)</h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">URI</label>
                    <input
                      type="text"
                      value={config.database.neo4j_uri}
                      onChange={(e) => updateDatabaseConfig('neo4j_uri', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Utilisateur</label>
                    <input
                      type="text"
                      value={config.database.neo4j_user}
                      onChange={(e) => updateDatabaseConfig('neo4j_user', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mot de passe</label>
                    <input
                      type="password"
                      value={config.database.neo4j_password || ''}
                      onChange={(e) => updateDatabaseConfig('neo4j_password', e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>
              </div>

              {/* Qdrant */}
              <div className="border-l-4 border-green-500 pl-4">
                <h3 className="font-medium text-gray-900 dark:text-white mb-3">Qdrant (Vector Store)</h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Hôte</label>
                    <input
                      type="text"
                      value={config.database.qdrant_host}
                      onChange={(e) => updateDatabaseConfig('qdrant_host', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Port</label>
                    <input
                      type="number"
                      value={config.database.qdrant_port}
                      onChange={(e) => updateDatabaseConfig('qdrant_port', parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>
              </div>

              {/* PostgreSQL */}
              <div className="border-l-4 border-blue-500 pl-4">
                <h3 className="font-medium text-gray-900 dark:text-white mb-3">PostgreSQL (Optionnel)</h3>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">URI de connexion</label>
                  <input
                    type="text"
                    value={config.database.postgres_uri || ''}
                    onChange={(e) => updateDatabaseConfig('postgres_uri', e.target.value)}
                    placeholder="postgresql://user:password@localhost:5432/dbname"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* UI Preferences */}
        {activeTab === 'ui' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
            <div>
              <h2 className="text-xl font-semibold dark:text-white mb-4">Préférences d'interface</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Personnalisez l'apparence et le comportement de l'interface
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Thème
                </label>
                <select
                  value={config.ui_preferences.theme}
                  onChange={(e) => updateUIPreferences('theme', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="light">Clair</option>
                  <option value="dark">Sombre</option>
                  <option value="auto">Automatique</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Langue
                </label>
                <select
                  value={config.ui_preferences.language}
                  onChange={(e) => updateUIPreferences('language', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="fr">Français</option>
                  <option value="en">English</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Éléments par page
                </label>
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={config.ui_preferences.items_per_page}
                  onChange={(e) => updateUIPreferences('items_per_page', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="notifications"
                  checked={config.ui_preferences.enable_notifications}
                  onChange={(e) => updateUIPreferences('enable_notifications', e.target.checked)}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="notifications" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                  Activer les notifications
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="mt-6 flex gap-3">
          <button
            onClick={saveConfig}
            disabled={saving}
            className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {saving ? 'Enregistrement...' : 'Enregistrer les modifications'}
          </button>
          <button
            onClick={resetConfig}
            disabled={saving}
            className="px-6 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            Réinitialiser
          </button>
        </div>
      </div>
    </div>
  )
}
