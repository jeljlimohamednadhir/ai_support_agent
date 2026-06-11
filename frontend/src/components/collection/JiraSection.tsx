import { useState, useEffect, useMemo, useRef } from 'react'
import { Activity, AlertCircle, CheckCircle2, RefreshCw, Loader2, Settings, Download, ExternalLink, Search, X, Calendar, User, Tag, Clock, FileText, TrendingUp, BarChart3, Sparkles } from 'lucide-react'
import { usePageStateStore } from '../../stores/pageStateStore'

interface JiraStats {
  total_issues: number
  open_issues: number
  in_progress_issues: number
  resolved_issues: number
  closed_issues: number
  total_projects: number
  last_sync: string | null
  status_breakdown?: Record<string, number>
}

interface JiraProject {
  id: string
  key: string
  name: string
  description: string | null
  lead: string | null
  issue_count: number
}

interface JiraTicket {
  id: string
  key: string
  summary: string
  description: string | null
  status: string
  priority: string | null
  issue_type: string
  assignee: string | null
  project_key: string
  project_name: string
  created: string | null
}

export default function JiraSection() {
  const [stats, setStats] = useState<JiraStats | null>(null)
  const [projects, setProjects] = useState<JiraProject[]>([])
  const [recentTickets, setRecentTickets] = useState<JiraTicket[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [loading, setLoading] = useState(true)
  
  const [config, setConfig] = useState({
    jira_url: '',
    email: '',
    api_token: ''
  })
  
  const [usePAT, setUsePAT] = useState(true) // Personal Access Token par défaut
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]) // Projets sélectionnés pour la sync

  // Persisted state — survives navigation
  const { jira, setJiraSearchQuery, setJiraSelectedProject, setJiraPage } = usePageStateStore()
  const searchQuery = jira.searchQuery
  const setSearchQuery = setJiraSearchQuery
  const currentPage = jira.currentPage
  const [selectedProject, setSelectedProjectLocal] = useState<JiraProject | null>(null) // Projet sélectionné pour voir les tickets
  const [projectTickets, setProjectTickets] = useState<JiraTicket[]>([]) // Tickets du projet sélectionné
  const [loadingTickets, setLoadingTickets] = useState(false) // Chargement des tickets
  const [totalTickets, setTotalTickets] = useState(0) // Total de tickets
  const ticketsPerPage = 20 // Tickets par page
  const [selectedTicket, setSelectedTicket] = useState<JiraTicket | null>(null) // Ticket sélectionné pour les détails
  const [showTicketModal, setShowTicketModal] = useState(false) // Modal de détails du ticket
  const [aiPopupTicketId, setAiPopupTicketId] = useState<string | null>(null) // AI popup ticket id
  const [aiText, setAiText] = useState('') // Full AI response text
  const [aiDisplayed, setAiDisplayed] = useState('') // Typewriter displayed text
  const [aiLoading, setAiLoading] = useState(false) // AI loading state
  const [aiPopupTicket, setAiPopupTicket] = useState<JiraTicket | null>(null) // Ticket being analysed
  const aiAbortRef = useRef<AbortController | null>(null)
  const aiTypewriterRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    loadJiraData()
  }, [])

  // Typewriter effect: animate aiDisplayed char-by-char as aiText grows
  useEffect(() => {
    if (!aiText) { setAiDisplayed(''); return }
    if (aiTypewriterRef.current) clearTimeout(aiTypewriterRef.current)
    let i = aiDisplayed.length
    const type = () => {
      if (i < aiText.length) {
        setAiDisplayed(aiText.slice(0, i + 1))
        i++
        aiTypewriterRef.current = setTimeout(type, 12)
      }
    }
    type()
    return () => { if (aiTypewriterRef.current) clearTimeout(aiTypewriterRef.current) }
  }, [aiText])

  // Restore selected project when projects list loads
  useEffect(() => {
    if (jira.selectedProjectKey && projects.length > 0 && !selectedProject) {
      const found = projects.find(p => p.key === jira.selectedProjectKey)
      if (found) loadProjectTickets(found, jira.currentPage)
    }
  }, [projects])

  // Filtrer les projets selon la recherche
  const filteredProjects = useMemo(() => {
    if (!searchQuery.trim()) {
      // Sans recherche, prioriser le projet BRASIL
      const brasilProject = projects.find(p => p.key.toUpperCase() === 'BRASIL')
      const otherProjects = projects.filter(p => p.key.toUpperCase() !== 'BRASIL')
      return brasilProject ? [brasilProject, ...otherProjects] : projects
    }
    
    const query = searchQuery.toLowerCase()
    return projects.filter(project => 
      project.key.toLowerCase().includes(query) ||
      project.name.toLowerCase().includes(query) ||
      (project.description && project.description.toLowerCase().includes(query)) ||
      (project.lead && project.lead.toLowerCase().includes(query))
    )
  }, [projects, searchQuery])

  const loadJiraData = async () => {
    try {
      setLoading(true)
      
      // Load stats
      const token = localStorage.getItem('auth_token')
      const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}
      const statsRes = await fetch('/api/v1/jira/stats', { headers: authHeaders })
      if (statsRes.ok) {
        const statsData = await statsRes.json()
        setStats(statsData)
        // Connexion réussie si on reçoit des stats (même à 0)
        setIsConnected(true)
      } else {
        setIsConnected(false)
      }
      
      // Load projects
      const projectsRes = await fetch('/api/v1/jira/projects', { headers: authHeaders })
      if (projectsRes.ok) {
        const projectsData = await projectsRes.json()
        setProjects(projectsData)
      }
    } catch (error) {
      console.error('Erreur chargement Jira:', error)
      setIsConnected(false)
    } finally {
      setLoading(false)
    }
  }

  const testConnection = async () => {
    // Validation selon le mode
    if (usePAT) {
      if (!config.jira_url || !config.api_token) {
        alert('⚠️ Veuillez remplir l\'URL Jira et le Personal Access Token')
        return
      }
    } else {
      if (!config.jira_url || !config.email || !config.api_token) {
        alert('⚠️ Veuillez remplir tous les champs')
        return
      }
    }

    try {
      setLoading(true)
      const payload = usePAT 
        ? { jira_url: config.jira_url, email: '', api_token: config.api_token }
        : config
      
      const response = await fetch('/api/v1/jira/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      
      const result = await response.json()
      
      if (result.success) {
        alert(`✅ Connexion réussie!\n${result.message}\n${result.projects_count} projets trouvés`)
        setIsConnected(true)
        setShowConfig(false)
        loadJiraData()
      } else {
        alert(`❌ Échec: ${result.message}`)
      }
    } catch (error) {
      alert(`❌ Erreur: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  const syncJira = async () => {
    // Utiliser les projets sélectionnés ou demander confirmation
    let projectsToSync: string[] = []
    
    if (selectedProjects.length > 0) {
      // Utiliser la sélection de l'utilisateur
      projectsToSync = selectedProjects
    } else {
      // Demander si filtrage BRASIL
      const projectFilter = window.confirm(
        '🔍 Filtrer par projet BRASIL ?\n\n' +
        'OUI = Uniquement les tickets BRASIL\n' +
        'NON = Tous les tickets accessibles'
      )
      
      if (projectFilter) {
        projectsToSync = ['BRASIL']
      }
    }
    
    try {
      setIsSyncing(true)
      const payload: any = {
        max_results: 100,
        include_resolved: true
      }
      
      if (projectsToSync.length > 0) {
        payload.project_keys = projectsToSync
      }
      
      const response = await fetch('/api/v1/jira/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      
      const result = await response.json()
      
      if (result.success) {
        const projectInfo = projectsToSync.length > 0 
          ? `des projets ${projectsToSync.join(', ')}` 
          : 'accessibles'
        alert(`✅ Synchronisation réussie!\n${result.issues_indexed} tickets ${projectInfo} indexés\nDurée: ${result.duration_seconds.toFixed(1)}s`)
        loadJiraData()
      } else {
        alert(`❌ Échec: ${result.errors.join(', ')}`)
      }
    } catch (error) {
      alert(`❌ Erreur: ${error}`)
    } finally {
      setIsSyncing(false)
    }
  }

  const loadProjectTickets = async (project: JiraProject, page: number = 0) => {
    setSelectedProjectLocal(project)
    setJiraSelectedProject(project.key)
    setJiraPage(page)
    setLoadingTickets(true)
    
    try {
      const startAt = page * ticketsPerPage
      const response = await fetch('/api/v1/jira/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: '',
          project_keys: [project.key],
          max_results: ticketsPerPage,
          start_at: startAt
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setProjectTickets(data.issues || [])
        setTotalTickets(data.total || 0)
      } else {
        console.error('Erreur chargement tickets')
        setProjectTickets([])
      }
    } catch (error) {
      console.error('Erreur:', error)
      setProjectTickets([])
    } finally {
      setLoadingTickets(false)
    }
  }

  const closeProjectView = () => {
    setSelectedProjectLocal(null)
    setJiraSelectedProject(null)
    setProjectTickets([])
    setJiraPage(0)
    setTotalTickets(0)
  }

  const nextPage = () => {
    if (selectedProject && (currentPage + 1) * ticketsPerPage < totalTickets) {
      loadProjectTickets(selectedProject, currentPage + 1)
    }
  }

  const prevPage = () => {
    if (currentPage > 0 && selectedProject) {
      loadProjectTickets(selectedProject, currentPage - 1)
    }
  }

  const getPriorityColor = (priority: string | null) => {
    if (!priority) return 'gray'
    const p = priority.toLowerCase()
    if (p.includes('highest') || p.includes('critical')) return 'red'
    if (p.includes('high')) return 'orange'
    if (p.includes('medium')) return 'yellow'
    if (p.includes('low')) return 'green'
    return 'gray'
  }

  const getStatusColor = (status: string) => {
    const s = status.toLowerCase()
    if (s.includes('done') || s.includes('resolved') || s.includes('closed')) return 'green'
    if (s.includes('progress') || s.includes('review')) return 'blue'
    if (s.includes('todo') || s.includes('open') || s.includes('new')) return 'gray'
    return 'purple'
  }

  const analyzeTicketWithAI = async (ticket: JiraTicket, e: React.MouseEvent) => {
    e.stopPropagation() // Don't open ticket modal
    if (aiPopupTicketId === ticket.id) {
      // Close popup if already open for this ticket
      aiAbortRef.current?.abort()
      setAiPopupTicketId(null)
      setAiPopupTicket(null)
      setAiText('')
      setAiDisplayed('')
      return
    }
    // Abort any previous request
    aiAbortRef.current?.abort()
    const controller = new AbortController()
    aiAbortRef.current = controller

    setAiPopupTicketId(ticket.id)
    setAiPopupTicket(ticket)
    setAiText('')
    setAiDisplayed('')
    setAiLoading(true)

    const prompt = `Analyse ce ticket Jira et donne une synthèse concise en 3-4 phrases (causes probables, impact, suggestions de résolution):\n\nTicket: ${ticket.key}\nTitre: ${ticket.summary}\nStatut: ${ticket.status}\nPriorité: ${ticket.priority || 'Non définie'}\nType: ${ticket.issue_type}\nDescription: ${ticket.description || 'Aucune description'}`

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch('/api/v1/chatbot/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ content: prompt }),
        signal: controller.signal
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => null)
        setAiText(`❌ Impossible d'obtenir une analyse IA. (${response.status}${errData?.detail ? ': ' + errData.detail : ''})`)
        setAiLoading(false)
        return
      }

      const data = await response.json()
      const text = data.message || data.response || data.content || 'Réponse reçue.'
      setAiDisplayed('')
      setAiText(text)
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setAiText('❌ Erreur lors de l\'analyse IA.')
      }
    } finally {
      setAiLoading(false)
    }
  }

  // Compute status distribution from actual ticket data
  const statusDistribution = useMemo(() => {
    const allTickets = [...recentTickets, ...projectTickets]
    if (allTickets.length === 0) return []
    const counts: Record<string, number> = {}
    for (const t of allTickets) {
      const s = t.status || 'Unknown'
      counts[s] = (counts[s] || 0) + 1
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
  }, [recentTickets, projectTickets])

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Activity className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Jira Integration
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {isConnected ? '✅ Connecté' : '⚠️ Non configuré'}
            </p>
          </div>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <Settings className="w-4 h-4" />
            Configuration
          </button>
          
          {isConnected && (
            <>
              {/* Sélecteur de projets */}
              <select
                multiple
                value={selectedProjects}
                onChange={(e) => {
                  const selected = Array.from(e.target.selectedOptions, option => option.value)
                  setSelectedProjects(selected)
                }}
                className="px-4 py-2 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:border-primary-500 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 transition-colors"
                style={{ minWidth: '200px' }}
              >
                <option value="">Tous les projets</option>
                {projects.map(project => (
                  <option key={project.key} value={project.key}>
                    {project.key} - {project.name}
                  </option>
                ))}
              </select>
              
              <button
                onClick={syncJira}
                disabled={isSyncing}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                {isSyncing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4" />
                )}
                Synchroniser
                {selectedProjects.length > 0 && (
                  <span className="ml-1 px-2 py-0.5 bg-white/20 rounded-full text-xs">
                    {selectedProjects.length}
                  </span>
                )}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Configuration Modal */}
      {showConfig && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Configuration Jira
          </h3>
          
          {/* Toggle PAT / Email+Token */}
          <div className="mb-6 flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <button
              onClick={() => setUsePAT(true)}
              className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                usePAT
                  ? 'bg-primary-600 text-white'
                  : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600'
              }`}
            >
              🔑 Personal Access Token
            </button>
            <button
              onClick={() => setUsePAT(false)}
              className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                !usePAT
                  ? 'bg-primary-600 text-white'
                  : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600'
              }`}
            >
              📧 Email + API Token
            </button>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                URL Jira <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={config.jira_url}
                onChange={(e) => setConfig({ ...config, jira_url: e.target.value })}
                placeholder="https://portail.agir.orange.com"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                URL de base uniquement, sans /projects ou /browse
              </p>
            </div>
            
            {!usePAT && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  value={config.email}
                  onChange={(e) => setConfig({ ...config, email: e.target.value })}
                  placeholder="votre-email@example.com"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {usePAT ? 'Personal Access Token' : 'API Token'} <span className="text-red-500">*</span>
              </label>
              <input
                type="password"
                value={config.api_token}
                onChange={(e) => setConfig({ ...config, api_token: e.target.value })}
                placeholder={usePAT ? "Votre Personal Access Token" : "Votre API Token"}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {usePAT ? (
                  <>
                    <strong>Pour créer un PAT :</strong><br/>
                    1. Allez dans votre profil Jira → Personal Access Tokens<br/>
                    2. Créez un nouveau token avec les permissions nécessaires<br/>
                    3. Copiez et collez-le ici
                  </>
                ) : (
                  <>Créez un token sur: https://id.atlassian.com/manage-profile/security/api-tokens</>
                )}
              </p>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={testConnection}
                disabled={loading}
                className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Test...' : 'Tester la connexion'}
              </button>
              <button
                onClick={() => setShowConfig(false)}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      {stats && isConnected && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Total</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total_issues}</p>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <p className="text-xs text-purple-600 dark:text-purple-400 mb-1">Projets</p>
            <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{stats.total_projects}</p>
          </div>

          {/* Dynamic status cards from real ticket data */}
          {statusDistribution.length > 0 ? (
            statusDistribution.map(([status, count]) => {
              const color = getStatusColor(status)
              const colorMap: Record<string, string> = {
                green: 'text-green-600 dark:text-green-400',
                blue: 'text-blue-600 dark:text-blue-400',
                gray: 'text-gray-600 dark:text-gray-400',
                yellow: 'text-yellow-600 dark:text-yellow-400',
                orange: 'text-orange-600 dark:text-orange-400',
                red: 'text-red-600 dark:text-red-400',
                purple: 'text-purple-600 dark:text-purple-400',
              }
              const textColor = colorMap[color] ?? 'text-gray-600 dark:text-gray-400'
              return (
                <div key={status} className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                  <p className={`text-xs mb-1 ${textColor}`}>{status}</p>
                  <p className={`text-2xl font-bold ${textColor}`}>{count}</p>
                </div>
              )
            })
          ) : stats?.status_breakdown && Object.keys(stats.status_breakdown).length > 0 ? (
            // Real status breakdown from Jira
            Object.entries(stats.status_breakdown).slice(0, 4).map(([status, count]) => {
              const color = getStatusColor(status)
              const colorMap: Record<string, string> = {
                green: 'text-green-600 dark:text-green-400',
                blue: 'text-blue-600 dark:text-blue-400',
                gray: 'text-gray-600 dark:text-gray-400',
                yellow: 'text-yellow-600 dark:text-yellow-400',
                orange: 'text-orange-600 dark:text-orange-400',
                red: 'text-red-600 dark:text-red-400',
                purple: 'text-purple-600 dark:text-purple-400',
              }
              const textColor = colorMap[color] ?? 'text-gray-600 dark:text-gray-400'
              return (
                <div key={status} className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                  <p className={`text-xs mb-1 ${textColor}`}>{status}</p>
                  <p className={`text-2xl font-bold ${textColor}`}>{count}</p>
                </div>
              )
            })
          ) : (
            // Generic fallback when no breakdown available
            <>
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <p className="text-xs text-blue-600 dark:text-blue-400 mb-1">Ouverts</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats?.open_issues ?? 0}</p>
              </div>
            </>
          )}
        </div>
      )}

      {/* Projects List */}
      {projects.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              Projets Jira ({projects.length})
            </h3>
            
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Rechercher par clé, nom, description ou responsable..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            
            {searchQuery && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                {filteredProjects.length} projet(s) trouvé(s)
              </p>
            )}
          </div>
          
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {filteredProjects.slice(0, 5).map((project) => (
              <div
                key={project.id}
                onClick={() => loadProjectTickets(project)}
                className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-mono rounded">
                        {project.key}
                      </span>
                      <h4 className="font-semibold text-gray-900 dark:text-white">
                        {project.name}
                      </h4>
                    </div>
                    {project.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-1">
                        {project.description}
                      </p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
                      {project.lead && <span>👤 {project.lead}</span>}
                      <span>🎫 {project.issue_count} tickets</span>
                    </div>
                  </div>
                  
                  <ExternalLink className="w-4 h-4 text-gray-400" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Project Tickets View */}
      {selectedProject && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <button
                    onClick={closeProjectView}
                    className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                  >
                    ← Retour
                  </button>
                  <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-mono rounded">
                    {selectedProject.key}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {selectedProject.name}
                </h3>
                {selectedProject.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {selectedProject.description}
                  </p>
                )}
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {projectTickets.length}
                </p>
                <p className="text-xs text-gray-600 dark:text-gray-400">tickets</p>
              </div>
            </div>
          </div>

          {loadingTickets ? (
            <div className="p-8 text-center">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-2" />
              <p className="text-gray-600 dark:text-gray-400">Chargement des tickets...</p>
            </div>
          ) : projectTickets.length === 0 ? (
            <div className="p-8 text-center">
              <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-2" />
              <p className="text-gray-600 dark:text-gray-400">Aucun ticket trouvé pour ce projet</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[600px] overflow-y-auto">
              {projectTickets.map((ticket) => (
                <div key={ticket.id}>
                <div
                  onClick={() => {
                    setSelectedTicket(ticket)
                    setShowTicketModal(true)
                  }}
                  className="p-4 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all cursor-pointer group border-l-4 border-transparent hover:border-blue-500"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-mono rounded font-semibold">
                          {ticket.key}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded font-medium ${
                          ticket.status.toLowerCase().includes('done') || ticket.status.toLowerCase().includes('resolved') 
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                            : ticket.status.toLowerCase().includes('progress')
                            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                        }`}>
                          {ticket.status}
                        </span>
                        {ticket.priority && (
                          <span className={`px-2 py-1 text-xs rounded font-medium ${
                            ticket.priority.toLowerCase().includes('high') || ticket.priority.toLowerCase().includes('critical')
                              ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                              : ticket.priority.toLowerCase().includes('medium')
                              ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                              : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                          }`}>
                            {ticket.priority}
                          </span>
                        )}
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 text-xs rounded">
                          {ticket.issue_type}
                        </span>
                      </div>
                      <h4 className="font-semibold text-gray-900 dark:text-white mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {ticket.summary}
                      </h4>
                      {ticket.description && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-2">
                          {ticket.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                        {ticket.assignee && (
                          <div className="flex items-center gap-1">
                            <User className="w-3 h-3" />
                            <span>{ticket.assignee}</span>
                          </div>
                        )}
                        {ticket.created && (
                          <div className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            <span>{new Date(ticket.created).toLocaleDateString('fr-FR')}</span>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0 mt-1">
                      <button
                        onClick={(e) => analyzeTicketWithAI(ticket, e)}
                        title="Analyse IA de ce ticket"
                        className={`p-1.5 rounded-lg transition-colors ${
                          aiPopupTicketId === ticket.id
                            ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400'
                            : 'text-gray-400 hover:text-purple-500 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                        }`}
                      >
                        <Sparkles className="w-4 h-4" />
                      </button>
                      <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-blue-500 transition-colors" />
                    </div>
                  </div>
                </div>
                {/* AI analysis modal — rendered once globally below */}
                </div>
              ))}
            </div>
          )}
          
          {/* Pagination Controls */}
          {!loadingTickets && projectTickets.length > 0 && (
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Page {currentPage + 1} / {Math.ceil(totalTickets / ticketsPerPage)}
                  <span className="mx-2">•</span>
                  {currentPage * ticketsPerPage + 1} - {Math.min((currentPage + 1) * ticketsPerPage, totalTickets)} sur {totalTickets} tickets
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={prevPage}
                    disabled={currentPage === 0}
                    className="px-3 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  >
                    ← Précédent
                  </button>
                  <button
                    onClick={nextPage}
                    disabled={(currentPage + 1) * ticketsPerPage >= totalTickets}
                    className="px-3 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  >
                    Suivant →
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Info Box */}
      {!isConnected && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
          <div className="flex gap-4">
            <AlertCircle className="w-6 h-6 text-blue-600 dark:text-blue-400 flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">
                Intégration Jira
              </h3>
              <p className="text-sm text-blue-800 dark:text-blue-300 mb-3">
                Connectez votre instance Jira pour synchroniser automatiquement les tickets 
                dans la base de connaissances BRASIL. Le chatbot pourra utiliser ces informations 
                pour répondre aux questions sur les incidents et problèmes connus.
              </p>
              <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1 list-disc list-inside">
                <li>Synchronisation automatique des tickets</li>
                <li>Recherche sémantique dans les descriptions</li>
                <li>Corrélation avec les tables et fiches FR</li>
                <li>Historique des résolutions de problèmes</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* ── AI Analysis Modal ── */}
      {aiPopupTicketId && aiPopupTicket && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          onClick={() => { aiAbortRef.current?.abort(); setAiPopupTicketId(null); setAiPopupTicket(null); setAiText(''); setAiDisplayed('') }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

          {/* Panel */}
          <div
            className="relative bg-gray-900 dark:bg-gray-950 border border-purple-500/40 rounded-2xl shadow-2xl w-full max-w-xl flex flex-col overflow-hidden"
            style={{ maxHeight: '80vh' }}
            onClick={e => e.stopPropagation()}
          >
            {/* Header bar */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-purple-500/30 bg-gradient-to-r from-purple-900/60 to-indigo-900/60">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 bg-purple-500/20 rounded-lg">
                  <Sparkles className="w-4 h-4 text-purple-300" />
                </div>
                <div>
                  <span className="text-xs font-mono font-bold text-purple-300 tracking-widest uppercase">Analyse IA</span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="px-2 py-0.5 bg-blue-600/80 text-white text-xs font-mono rounded font-bold">{aiPopupTicket.key}</span>
                    <span className="text-gray-400 text-xs truncate max-w-[200px]">{aiPopupTicket.summary}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => { aiAbortRef.current?.abort(); setAiPopupTicketId(null); setAiPopupTicket(null); setAiText(''); setAiDisplayed('') }}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 min-h-[120px]">
              {aiLoading ? (
                <div className="flex flex-col items-center justify-center py-10 gap-3">
                  <div className="flex gap-1.5">
                    {[0, 1, 2].map(i => (
                      <div
                        key={i}
                        className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-bounce"
                        style={{ animationDelay: `${i * 0.2}s` }}
                      />
                    ))}
                  </div>
                  <span className="text-sm text-purple-300 font-mono tracking-wide">Analyse en cours...</span>
                </div>
              ) : (
                <div className="font-mono text-sm leading-relaxed">
                  <p className="text-green-300 whitespace-pre-wrap break-words">
                    {aiDisplayed}
                    {aiDisplayed.length < aiText.length && (
                      <span className="inline-block w-2 h-4 bg-green-400 ml-0.5 align-middle animate-pulse" />
                    )}
                  </p>
                  {!aiText && !aiLoading && (
                    <span className="text-gray-500 italic text-xs">En attente de réponse...</span>
                  )}
                </div>
              )}
            </div>

            {/* Footer status bar */}
            <div className="px-5 py-2 border-t border-purple-500/20 bg-black/30 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${aiLoading ? 'bg-yellow-400 animate-pulse' : aiText ? 'bg-green-400' : 'bg-gray-500'}`} />
                <span className="text-xs text-gray-500 font-mono">
                  {aiLoading ? 'Requête en cours...' : aiText ? `${aiText.length} car.` : 'En attente'}
                </span>
              </div>
              <span className="text-xs text-gray-600 font-mono">BRASIL AI · Groq</span>
            </div>
          </div>
        </div>
      )}

      {/* Ticket Detail Modal */}
      {showTicketModal && selectedTicket && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-3 py-1 bg-blue-600 text-white text-sm font-mono rounded-lg font-bold">
                      {selectedTicket.key}
                    </span>
                    <span className={`px-3 py-1 text-sm rounded-lg font-semibold ${
                      selectedTicket.status.toLowerCase().includes('done') || selectedTicket.status.toLowerCase().includes('resolved') 
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                        : selectedTicket.status.toLowerCase().includes('progress')
                        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
                        : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                    }`}>
                      {selectedTicket.status}
                    </span>
                  </div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                    {selectedTicket.summary}
                  </h2>
                  <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                    <div className="flex items-center gap-1">
                      <Tag className="w-4 h-4" />
                      <span>{selectedTicket.issue_type}</span>
                    </div>
                    {selectedTicket.priority && (
                      <div className="flex items-center gap-1">
                        <TrendingUp className="w-4 h-4" />
                        <span className={selectedTicket.priority.toLowerCase().includes('high') ? 'text-red-600 dark:text-red-400 font-semibold' : ''}>
                          {selectedTicket.priority}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setShowTicketModal(false)}
                  className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Description */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="w-5 h-5 text-gray-500" />
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Description</h3>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                  {selectedTicket.description ? (
                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {selectedTicket.description}
                    </p>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400 italic">Aucune description disponible</p>
                  )}
                </div>
              </div>

              {/* Details Grid */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Détails</h3>
                <div className="grid grid-cols-2 gap-4">
                  {/* Assignee */}
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <User className="w-4 h-4 text-gray-500" />
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Assigné à</span>
                    </div>
                    <p className="text-gray-900 dark:text-white font-medium">
                      {selectedTicket.assignee || 'Non assigné'}
                    </p>
                  </div>

                  {/* Created Date */}
                  {selectedTicket.created && (
                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Calendar className="w-4 h-4 text-gray-500" />
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Créé le</span>
                      </div>
                      <p className="text-gray-900 dark:text-white font-medium">
                        {new Date(selectedTicket.created).toLocaleDateString('fr-FR', {
                          day: 'numeric',
                          month: 'long',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </p>
                    </div>
                  )}

                  {/* Project */}
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart3 className="w-4 h-4 text-gray-500" />
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Projet</span>
                    </div>
                    <p className="text-gray-900 dark:text-white font-medium">
                      {selectedTicket.project_name} ({selectedTicket.project_key})
                    </p>
                  </div>

                  {/* Priority */}
                  {selectedTicket.priority && (
                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <TrendingUp className="w-4 h-4 text-gray-500" />
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Priorité</span>
                      </div>
                      <p className={`font-bold ${
                        selectedTicket.priority.toLowerCase().includes('high') || selectedTicket.priority.toLowerCase().includes('critical')
                          ? 'text-red-600 dark:text-red-400'
                          : selectedTicket.priority.toLowerCase().includes('medium')
                          ? 'text-orange-600 dark:text-orange-400'
                          : 'text-gray-900 dark:text-white'
                      }`}>
                        {selectedTicket.priority}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
              <div className="flex items-center justify-between">
                <a
                  href={`${config.jira_url}/browse/${selectedTicket.key}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                  Voir dans Jira
                </a>
                <button
                  onClick={() => setShowTicketModal(false)}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                >
                  Fermer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
