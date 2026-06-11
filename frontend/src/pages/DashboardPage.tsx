import { useState, useEffect } from 'react'
import { MessageSquare, Activity, TrendingUp, Database, Bot, Loader2, CheckCircle } from 'lucide-react'
import { chatService } from '@/services/chatService'
import { useAuth } from '@/contexts/AuthContext'
import { Link } from 'react-router-dom'

interface UserStats {
  conversationsCount: number
  totalMessages: number
  lastActivity: string | null
  recentConversations: { id: number; title: string; updated_at: string }[]
}

interface SystemStats {
  jiraTickets: number | null
  jiraProjects: number | null
  knowledgeDocs: number | null
  pendingValidations: number | null
}

const formatTimeAgo = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (seconds < 60) return 'il y a quelques secondes'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `il y a ${minutes}min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `il y a ${hours}h`
  const days = Math.floor(hours / 24)
  return `il y a ${days}j`
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [userStats, setUserStats] = useState<UserStats>({ conversationsCount: 0, totalMessages: 0, lastActivity: null, recentConversations: [] })
  const [systemStats, setSystemStats] = useState<SystemStats>({ jiraTickets: null, jiraProjects: null, knowledgeDocs: null, pendingValidations: null })
  const [loadingUser, setLoadingUser] = useState(true)
  const [loadingSystem, setLoadingSystem] = useState(true)

  useEffect(() => {
    loadUserStats()
    loadSystemStats()
  }, [])

  const loadUserStats = async () => {
    setLoadingUser(true)
    try {
      const conversations = await chatService.listConversations(0, 100)
      const sorted = [...conversations].sort((a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      const lastActivity = sorted.length > 0 ? sorted[0].updated_at : null
      // Count messages across recent conversations (first 5)
      let totalMessages = 0
      for (const conv of sorted.slice(0, 5)) {
        try {
          const msgs = await chatService.listMessages(conv.id)
          totalMessages += msgs.length
        } catch {}
      }
      setUserStats({
        conversationsCount: conversations.length,
        totalMessages,
        lastActivity,
        recentConversations: sorted.slice(0, 5).map(c => ({ id: c.id, title: c.title || `Conversation #${c.id}`, updated_at: c.updated_at }))
      })
    } catch (err) {
      console.error('Failed to load user stats:', err)
    } finally {
      setLoadingUser(false)
    }
  }

  const loadSystemStats = async () => {
    setLoadingSystem(true)
    const token = localStorage.getItem('auth_token')
    const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {}
    try {
      const [jiraRes, knowledgeRes, validationRes] = await Promise.allSettled([
        fetch('/api/v1/jira/stats', { headers }),
        fetch('/api/v1/knowledge/stats', { headers }),
        fetch('/api/v1/validation/pending-count', { headers })
      ])
      const jiraData = jiraRes.status === 'fulfilled' && jiraRes.value.ok ? await jiraRes.value.json() : null
      const knowledgeData = knowledgeRes.status === 'fulfilled' && knowledgeRes.value.ok ? await knowledgeRes.value.json() : null
      const validationData = validationRes.status === 'fulfilled' && validationRes.value.ok ? await validationRes.value.json() : null
      setSystemStats({
        jiraTickets: jiraData?.total_issues ?? null,
        jiraProjects: jiraData?.total_projects ?? null,
        knowledgeDocs: knowledgeData?.total_documents ?? null,
        pendingValidations: validationData?.count ?? null,
      })
    } catch {}
    setLoadingSystem(false)
  }

  const statCards = [
    { label: 'Mes conversations', value: userStats.conversationsCount, icon: MessageSquare, color: 'blue', sub: userStats.lastActivity ? `Dernière: ${formatTimeAgo(userStats.lastActivity)}` : 'Aucune conversation' },
    { label: 'Messages échangés', value: userStats.totalMessages, icon: Bot, color: 'purple', sub: '5 dernières conversations' },
    { label: 'Tickets Jira', value: systemStats.jiraTickets ?? '—', icon: Activity, color: 'orange', sub: systemStats.jiraTickets !== null ? 'Total dans la base' : 'Non disponible' },
    { label: 'Docs indexés', value: systemStats.knowledgeDocs ?? '—', icon: Database, color: 'green', sub: systemStats.knowledgeDocs !== null ? 'Dans la base RAG' : 'Non disponible' },
  ]

  const colorMap: Record<string, string> = {
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
    green: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
  }

  return (
    <div className="p-8 min-h-screen dark:bg-gray-900">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Bonjour, {user?.full_name || user?.username || 'utilisateur'} 👋
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Voici un résumé de votre activité et de l'état du système.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{card.label}</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
                    {(loadingUser && ['Mes conversations', 'Messages échangés'].includes(card.label)) || (loadingSystem && ['Tickets Jira', 'Docs indexés'].includes(card.label))
                      ? <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                      : card.value}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{card.sub}</p>
                </div>
                <div className={`p-3 rounded-lg ${colorMap[card.color]}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Conversations */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-blue-500" />
              Conversations récentes
            </h2>
            <Link to="/chat" className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
              Nouvelle conversation →
            </Link>
          </div>
          {loadingUser ? (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-12 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />)}
            </div>
          ) : userStats.recentConversations.length === 0 ? (
            <div className="text-center py-8">
              <Bot className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
              <p className="text-gray-500 dark:text-gray-400">Aucune conversation pour le moment</p>
              <Link to="/chat" className="mt-3 inline-block px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
                Commencer à chatter
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {userStats.recentConversations.map(conv => (
                <Link
                  key={conv.id}
                  to={`/chat?conversation=${conv.id}`}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <MessageSquare className="w-4 h-4 text-blue-500 flex-shrink-0" />
                    <span className="text-sm text-gray-700 dark:text-gray-300 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400">
                      {conv.title}
                    </span>
                  </div>
                  <span className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0 ml-2">
                    {formatTimeAgo(conv.updated_at)}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-green-500" />
            Actions rapides
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { to: '/chat', icon: Bot, label: 'Chat IA', sub: 'Poser une question', color: 'blue' },
              { to: '/jira', icon: Activity, label: 'Jira', sub: 'Voir les tickets', color: 'orange' },
              { to: '/classification-ml', icon: TrendingUp, label: 'Classification ML', sub: 'Analyser des tickets', color: 'purple' },
              { to: '/knowledge', icon: Database, label: 'Base de données', sub: 'Gérer les données', color: 'green' },
            ].map(item => {
              const Icon = item.icon
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors group"
                >
                  <div className={`p-2 rounded-lg ${colorMap[item.color]}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200 group-hover:text-blue-600 dark:group-hover:text-blue-400">{item.label}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{item.sub}</p>
                  </div>
                </Link>
              )
            })}
          </div>

          {/* System Status */}
          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-1">
              <CheckCircle className="w-4 h-4 text-green-500" />
              État du système
            </p>
            <div className="space-y-2 text-sm">
              {[
                { label: 'Assistant IA', ok: true },
                { label: 'Base de connaissances', ok: systemStats.knowledgeDocs !== null },
                { label: 'Intégration Jira', ok: systemStats.jiraTickets !== null },
                { label: 'Validations', ok: systemStats.pendingValidations !== null },
              ].map(item => (
                <div key={item.label} className="flex items-center justify-between">
                  <span className="text-gray-600 dark:text-gray-400">{item.label}</span>
                  <span className={`flex items-center gap-1 text-xs font-medium ${item.ok ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`}>
                    <div className={`w-2 h-2 rounded-full ${item.ok ? 'bg-green-500' : 'bg-gray-400'}`} />
                    {item.ok ? 'Opérationnel' : 'Non disponible'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
