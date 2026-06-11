import { MessageSquare, Plus, Clock, Calendar, Trash2, Pencil, Check, X } from 'lucide-react'
import { useState, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { chatService } from '@/services/chatService'

interface ChatHistoryProps {
  selectedConversation: string | null
  onSelectConversation: (id: string) => void
  onNewConversation: () => void
  onDeleteConversation: (id: number) => void
  visible: boolean
  onToggle: () => void
}

export default function ChatHistory({ 
  selectedConversation, 
  onSelectConversation, 
  onNewConversation,
  onDeleteConversation,
  visible,
  onToggle
}: ChatHistoryProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const editInputRef = useRef<HTMLInputElement>(null)
  const { conversations, updateConversation } = useChatStore()

  const startEdit = (id: number, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingId(id)
    setEditTitle(currentTitle)
    setTimeout(() => editInputRef.current?.select(), 30)
  }

  const saveEdit = async (id: number) => {
    const trimmed = editTitle.trim()
    if (trimmed && trimmed !== conversations.find(c => c.id === id)?.title) {
      try {
        await chatService.updateTitle(id, trimmed)
        updateConversation(id, { title: trimmed })
      } catch (e) {
        console.warn('Title update failed:', e)
      }
    }
    setEditingId(null)
  }

  const cancelEdit = () => setEditingId(null)
  
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
              onMouseEnter={() => setHoveredId(String(conv.id))}
              onMouseLeave={() => setHoveredId(null)}
              className="relative group"
            >
              <button
                onClick={() => onSelectConversation(String(conv.id))}
                className={`w-full text-left p-3 rounded-lg transition-all duration-200 ${
                  selectedConversation === String(conv.id)
                    ? 'bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/20 dark:to-blue-900/20 border-2 border-primary-500 dark:border-primary-400 shadow-sm'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700 border-2 border-transparent hover:border-gray-200 dark:hover:border-gray-600'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-1 ${selectedConversation === String(conv.id) ? 'text-primary-600' : 'text-gray-400'}`}>
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    {editingId === conv.id ? (
                      <div className="flex items-center gap-1 mb-1" onClick={e => e.stopPropagation()}>
                        <input
                          ref={editInputRef}
                          value={editTitle}
                          onChange={e => setEditTitle(e.target.value)}
                          onKeyDown={e => {
                            if (e.key === 'Enter') saveEdit(conv.id)
                            if (e.key === 'Escape') cancelEdit()
                          }}
                          onBlur={() => saveEdit(conv.id)}
                          className="flex-1 text-sm px-1.5 py-0.5 rounded border border-primary-400 dark:border-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-primary-500 min-w-0"
                          autoFocus
                        />
                        <button onClick={() => saveEdit(conv.id)} className="text-green-600 hover:text-green-700 flex-shrink-0"><Check className="w-3.5 h-3.5" /></button>
                        <button onClick={cancelEdit} className="text-gray-400 hover:text-gray-600 flex-shrink-0"><X className="w-3.5 h-3.5" /></button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 mb-1 group/title">
                        <p className={`text-sm font-medium truncate ${
                          selectedConversation === String(conv.id) ? 'text-primary-900 dark:text-primary-100' : 'text-gray-900 dark:text-gray-100'
                        }`}>
                          {conv.title}
                        </p>
                        {hoveredId === String(conv.id) && (
                          <button
                            onClick={e => startEdit(conv.id, conv.title, e)}
                            className="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 opacity-0 group-hover/title:opacity-100 transition-opacity"
                            title="Renommer"
                          >
                            <Pencil className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    )}
                    {conv.message_count !== undefined && (
                      <p className="text-xs text-gray-500 truncate mb-1">
                        {conv.message_count} message{conv.message_count !== 1 ? 's' : ''}
                      </p>
                    )}
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                      <Calendar className="w-3 h-3" />
                      {new Date(conv.updated_at || conv.created_at).toLocaleDateString('fr-FR')}
                    </div>
                  </div>
                </div>
              </button>
              
              {/* Delete button on hover */}
              {hoveredId === String(conv.id) && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteConversation(conv.id)
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
