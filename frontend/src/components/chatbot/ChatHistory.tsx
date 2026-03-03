import { MessageSquare, Plus, Clock, Calendar, Trash2 } from 'lucide-react'
import { useState } from 'react'

interface ChatHistoryProps {
  selectedConversation: string | null
  onSelectConversation: (id: string) => void
  onNewConversation: () => void
  visible: boolean
  onToggle: () => void
}

export default function ChatHistory({ 
  selectedConversation, 
  onSelectConversation, 
  onNewConversation,
  visible,
  onToggle
}: ChatHistoryProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  
  const conversations = [
    { id: '1', title: 'Erreur BRASIL 1002 - Champ NIFolderID obligatoire', date: '2026-01-09', preview: 'Comment résoudre l\'erreur BRASIL 1002 ?' },
    { id: '2', title: 'Table t_ports - Structure et utilisation', date: '2026-01-09', preview: 'Qu\'est-ce que la table t_ports ?' },
    { id: '3', title: 'Compteurs DSLAM à 100% - FR 1583', date: '2026-01-08', preview: 'Quelles tables sont concernées par les compteurs DSLAM ?' },
    { id: '4', title: 'Migration base de données PostgreSQL', date: '2026-01-08', preview: 'Comment migrer la base brasil_db ?' },
    { id: '5', title: 'Recherche de broche en échec', date: '2026-01-07', preview: 'Que faire en cas de recherche de broche en échec ?' },
  ]
  
  if (!visible) {
    return (
      <button
        onClick={onToggle}
        className="absolute left-0 top-0 z-10 m-4 bg-white border border-gray-200 rounded-lg p-2 shadow-md hover:shadow-lg transition-all duration-200 hover:scale-105"
        title="Afficher l'historique"
      >
        <Clock className="w-5 h-5 text-gray-600" />
      </button>
    )
  }
  
  return (
    <div className="w-80 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col shadow-lg">
      {/* Header with New Chat Button */}
      <div className="p-4 border-b border-gray-100 dark:border-gray-700 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Conversations</h2>
          <button
            onClick={onToggle}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            title="Masquer l'historique"
          >
            <Clock className="w-5 h-5" />
          </button>
        </div>
        
        <button 
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-primary-600 to-blue-600 text-white rounded-lg hover:shadow-md transition-all duration-200 hover:scale-[1.02] font-medium"
        >
          <Plus className="w-4 h-4" />
          Nouvelle conversation
        </button>
      </div>
      
      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {conversations.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">Aucune conversation</p>
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              onMouseEnter={() => setHoveredId(conv.id)}
              onMouseLeave={() => setHoveredId(null)}
              className="relative group"
            >
              <button
                onClick={() => onSelectConversation(conv.id)}
                className={`w-full text-left p-3 rounded-lg transition-all duration-200 ${
                  selectedConversation === conv.id
                    ? 'bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/20 dark:to-blue-900/20 border-2 border-primary-500 dark:border-primary-400 shadow-sm'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700 border-2 border-transparent hover:border-gray-200 dark:hover:border-gray-600'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-1 ${selectedConversation === conv.id ? 'text-primary-600' : 'text-gray-400'}`}>
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium truncate mb-1 ${
                      selectedConversation === conv.id ? 'text-primary-900 dark:text-primary-100' : 'text-gray-900 dark:text-gray-100'
                    }`}>
                      {conv.title}
                    </p>
                    <p className="text-xs text-gray-500 truncate mb-1">
                      {conv.preview}
                    </p>
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                      <Calendar className="w-3 h-3" />
                      {conv.date}
                    </div>
                  </div>
                </div>
              </button>
              
              {/* Delete button on hover */}
              {hoveredId === conv.id && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    // Handle delete
                  }}
                  className="absolute right-2 top-2 p-1.5 bg-red-50 text-red-600 rounded-md hover:bg-red-100 transition-colors opacity-0 group-hover:opacity-100"
                  title="Supprimer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ))
        )}
      </div>
      
      {/* Footer Stats */}
      <div className="p-4 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
          {conversations.length} conversation{conversations.length > 1 ? 's' : ''}
        </div>
      </div>
    </div>
  )
}
