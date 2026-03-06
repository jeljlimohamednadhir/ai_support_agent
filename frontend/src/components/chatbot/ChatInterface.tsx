import { useState, useRef, useEffect } from 'react'
import { Send, BookOpen, X, Sparkles, Bot, User, FileText, Database, Clock, ThumbsDown, Quote } from 'lucide-react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { sendMessage } from '@/services/api'
import { chatService } from '@/services/chatService'
import { useChatStore } from '@/stores/chatStore'
import ReactMarkdown from 'react-markdown'

interface ChatInterfaceProps {
  conversationId: string | null
  onToggleHistory: () => void
  historyVisible: boolean
}

export default function ChatInterface({ conversationId, onToggleHistory, historyVisible }: ChatInterfaceProps) {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<any[]>([])
  const [selectedSources, setSelectedSources] = useState<any[]>([])
  const [sourcesQuestion, setSourcesQuestion] = useState<string>('')
  const [showSources, setShowSources] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [dismissedSources, setDismissedSources] = useState<Set<string>>(new Set())
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { activeConversationId, updateConversation } = useChatStore()

  // Build a stable key for a source in the context of the current question
  const sourceKey = (sourceName: string, question: string) => `${sourceName}||${question}`

  const handleDismissSource = async (source: any, question: string) => {
    const key = sourceKey(source.name || source.file_path || '', question)
    setDismissedSources(prev => new Set(prev).add(key))
    try {
      await chatService.reportIrrelevantSource({
        source_name: source.name || source.file_path || 'unknown',
        source_type: source.type || 'unknown',
        question,
        conversation_id: conversationId,
      })
    } catch (err) {
      console.warn('Source feedback failed:', err)
    }
  }

  const handleCiteSource = (source: any) => {
    const frNums = source.source_fr_numbers?.length
      ? `FR ${source.source_fr_numbers.join(', FR ')}`
      : null
    const label = frNums || source.name || source.title || 'cette source'
    setMessage(prev => (prev ? prev + ' ' : '') + `Donne-moi plus de détails sur ${label}`)
    inputRef.current?.focus()
  }
  
  // Load messages from backend when conversation changes
  useEffect(() => {
    const loadMessages = async () => {
      if (activeConversationId) {
        setIsLoading(true)
        try {
          const loadedMessages = await chatService.listMessages(activeConversationId, 0, 100)
          setMessages(loadedMessages.map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            sources: []
          })))
        } catch (error) {
          console.error('Failed to load messages:', error)
        } finally {
          setIsLoading(false)
        }
      } else {
        setMessages([])
      }
    }
    
    loadMessages()
  }, [activeConversationId])
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }
  
  useEffect(() => {
    scrollToBottom()
  }, [messages])
  
  const mutation = useMutation({
    mutationFn: sendMessage,
    onSuccess: async (data) => {
      const assistantMsg = { 
        role: 'assistant', 
        content: data.message, 
        sources: data.sources || [], 
        timestamp: new Date() 
      }
      setMessages(prev => [...prev, assistantMsg])
      
      // Save both user and assistant messages to backend
      if (activeConversationId) {
        try {
          await chatService.addMessage(activeConversationId, {
            role: 'user',
            content: message
          })
          await chatService.addMessage(activeConversationId, {
            role: 'assistant',
            content: data.message
          })

          // Generate AI title after the very first exchange (messages was empty before user sent)
          if (messages.length === 0) {
            try {
              const updatedConv = await chatService.generateTitle(activeConversationId)
              updateConversation(activeConversationId, { title: updatedConv.title, updated_at: new Date().toISOString() })
            } catch (titleError) {
              console.warn('Title generation failed:', titleError)
            }
          } else {
            // Update timestamp so conversation bubbles to top of list
            updateConversation(activeConversationId, { updated_at: new Date().toISOString() })
          }
        } catch (error) {
          console.error('Failed to save messages:', error)
        }
      }
      
      if (data.sources && data.sources.length > 0) {
        setSelectedSources(data.sources)
        setSourcesQuestion(message)
        setShowSources(true)
      }
      setMessage('')
    },
  })
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || mutation.isPending) return
    
    const userMsg = { role: 'user', content: message, timestamp: new Date() }
    const isFirstMessage = messages.length === 0
    setMessages(prev => [...prev, userMsg])

    // Construire l'historique local pour la mémoire conversationnelle (6 derniers échanges)
    const localHistory = messages
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .slice(-12)
      .map(m => ({ role: m.role as string, content: m.content as string }))

    mutation.mutate({ message, conversation_id: conversationId, conversation_history: localHistory })
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }
  
  const suggestedQuestions = [
    "Comment résoudre l'erreur BRASIL 1002 ?",
    "Qu'est-ce que la table t_ports ?",
    "Quelles fiches FR concernent les compteurs DSLAM ?",
    "Comment corriger l'erreur B4002 ?",
  ]
  
  return (
    <div className="flex-1 flex h-full bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800">
      {/* Main Chat Panel */}
      <div className="flex-1 flex flex-col max-w-5xl mx-auto w-full">
        {/* Header */}
        <div className="border-b border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm px-6 py-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {!historyVisible && (
                <button
                  onClick={onToggleHistory}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Afficher l'historique"
                >
                  <Clock className="w-5 h-5 text-gray-600" />
                </button>
              )}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-blue-600 rounded-lg flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Assistant BRASIL</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Expert base de données & résolution d'incidents</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-green-50 text-green-700 text-xs font-medium rounded-full flex items-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                En ligne
              </span>
            </div>
          </div>
        </div>
        
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
          {messages.length === 0 && (
            <div className="max-w-3xl mx-auto text-center py-12">
              <div className="w-16 h-16 bg-gradient-to-br from-primary-100 to-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Bot className="w-8 h-8 text-primary-600" />
              </div>
              <h3 className="text-2xl font-semibold text-gray-900 dark:text-white mb-3">
                Bienvenue sur l'Assistant BRASIL
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-8">
                Posez vos questions sur la base de données, les fiches de résolution ou les procédures
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-6">
                {suggestedQuestions.map((question, idx) => (
                  <button
                    key={idx}
                    onClick={() => setMessage(question)}
                    className="p-4 text-left bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-primary-300 dark:hover:border-primary-500 hover:shadow-md transition-all duration-200 group"
                  >
                    <div className="flex items-start gap-3">
                      <Sparkles className="w-4 h-4 text-primary-600 mt-0.5 group-hover:scale-110 transition-transform" />
                      <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-primary-700 dark:group-hover:text-primary-400">{question}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className="space-y-3">
              <div className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 bg-gradient-to-br from-primary-600 to-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}
                
                <div className={`flex flex-col gap-2 max-w-3xl ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div
                    className={`px-6 py-4 rounded-2xl shadow-sm ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-r from-primary-600 to-blue-600 text-white'
                        : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700'
                    }`}
                  >
                    <div className={`prose prose-sm max-w-none ${msg.role === 'user' ? 'prose-invert' : ''}`}>
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                  
                  {/* Sources Pills */}
                  {msg.sources && msg.sources.length > 0 && msg.role === 'assistant' && (
                    <div className="flex flex-wrap gap-2 mt-1">
                      {msg.sources.slice(0, 4).map((source: any, i: number) => {
                        const isTable = source.type === 'database_table'
                        const isFiche = source.type === 'resolution_fiche' || source.type === 'procedure' || source.source_fr_numbers?.length > 0
                        // Resolve display name — backend now always sends source.name
                        const sName = source.name || source.title || source.file_path?.split('/').pop() || `Source ${i + 1}`
                        // Find the last user message before this assistant message
                        const lastUserMsg = messages.slice(0, messages.indexOf(msg)).filter((m: any) => m.role === 'user').slice(-1)[0]
                        const question = lastUserMsg?.content || ''
                        const isDismissed = dismissedSources.has(sourceKey(source.name || source.title || '', question))
                        
                        return (
                          <div key={i} className="flex items-center gap-0 group/pill rounded-full overflow-hidden">
                            {/* Main pill — opens sources sidebar */}
                            <button
                              onClick={() => {
                                setSelectedSources(msg.sources)
                                setSourcesQuestion(question)
                                setShowSources(true)
                              }}
                              className={`text-xs px-3 py-1.5 font-medium transition-all duration-200 flex items-center gap-1.5 ${
                                isDismissed
                                  ? 'bg-gray-100 text-gray-400 line-through'
                                  : isTable
                                  ? 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                                  : isFiche
                                  ? 'bg-purple-50 text-purple-700 hover:bg-purple-100'
                                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                              }`}
                            >
                              {isTable ? <Database className="w-3 h-3" /> : <FileText className="w-3 h-3" />}
                              {sName}
                            </button>
                            {/* Cite button — appears on hover */}
                            {!isDismissed && (
                              <button
                                onClick={() => handleCiteSource(source)}
                                className={`text-xs px-1.5 py-1.5 font-medium transition-all duration-200 opacity-0 group-hover/pill:opacity-100 border-l ${
                                  isTable ? 'bg-blue-100 text-blue-500 hover:bg-blue-200 border-blue-200'
                                  : isFiche ? 'bg-purple-100 text-purple-500 hover:bg-purple-200 border-purple-200'
                                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200 border-gray-200'
                                }`}
                                title="Citer cette source dans le chat"
                              >
                                <Quote className="w-3 h-3" />
                              </button>
                            )}
                            {/* Dismiss button — appears on hover */}
                            {!isDismissed && (
                              <button
                                onClick={() => handleDismissSource(source, question)}
                                className={`text-xs px-1.5 py-1.5 font-medium transition-all duration-200 opacity-0 group-hover/pill:opacity-100 border-l ${
                                  isTable ? 'bg-blue-100 text-blue-400 hover:bg-red-100 hover:text-red-500 border-blue-200'
                                  : isFiche ? 'bg-purple-100 text-purple-400 hover:bg-red-100 hover:text-red-500 border-purple-200'
                                  : 'bg-gray-100 text-gray-400 hover:bg-red-100 hover:text-red-500 border-gray-200'
                                }`}
                                title="Source non pertinente"
                              >
                                <ThumbsDown className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        )
                      })}
                      {msg.sources.length > 4 && (
                        <button
                          onClick={() => {
                            setSelectedSources(msg.sources)
                            setSourcesQuestion(
                              messages.slice(0, messages.indexOf(msg)).filter((m: any) => m.role === 'user').slice(-1)[0]?.content || ''
                            )
                            setShowSources(true)
                          }}
                          className="text-xs px-3 py-1.5 bg-gray-50 text-gray-600 hover:bg-gray-100 rounded-full font-medium transition-colors"
                        >
                          +{msg.sources.length - 4} autres
                        </button>
                      )}
                    </div>
                  )}
                </div>
                
                {msg.role === 'user' && (
                  <div className="w-8 h-8 bg-gradient-to-br from-gray-600 to-gray-700 rounded-lg flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-white" />
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {mutation.isPending && (
            <div className="flex gap-4 justify-start">
                <div className="w-8 h-8 bg-gradient-to-br from-primary-600 to-blue-600 rounded-lg flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-6 py-4 rounded-2xl shadow-sm">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
        
        {/* Input Area */}
        <div className="border-t border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm px-6 py-4 shadow-lg">
          <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
            <div className="flex gap-3 items-end">
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Posez une question sur BRASIL, les tables ou les fiches de résolution..."
                  rows={1}
                  className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none bg-white dark:bg-gray-700 dark:text-white shadow-sm"
                  style={{ minHeight: '48px', maxHeight: '120px' }}
                />
                <div className="absolute right-3 bottom-3 text-xs text-gray-400">
                  {message.length}/2000
                </div>
              </div>
              <button
                type="submit"
                disabled={mutation.isPending || !message.trim()}
                className="px-6 py-3 bg-gradient-to-r from-primary-600 to-blue-600 text-white rounded-xl hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:scale-105 flex items-center gap-2 font-medium"
              >
                <Send className="w-5 h-5" />
                Envoyer
              </button>
            </div>
            <div className="mt-2 text-xs text-gray-500 flex items-center gap-4">
              <span>💡 Astuce : Utilisez Shift+Entrée pour un retour à la ligne</span>
            </div>
          </form>
        </div>
      </div>
      
      {/* Sources Sidebar */}
      {showSources && selectedSources.length > 0 && (
        <div className="w-96 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col shadow-xl">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/20 dark:to-blue-900/20">
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary-600" />
              <h3 className="font-semibold text-gray-900 dark:text-white">Sources ({selectedSources.length})</h3>
            </div>
            <button
              onClick={() => setShowSources(false)}
              className="text-gray-400 hover:text-gray-600 p-1 hover:bg-white rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {selectedSources.map((source: any, idx: number) => {
              const isTable = source.type === 'database_table'
              const isFiche = source.type === 'resolution_fiche' || source.type === 'procedure' || source.source_fr_numbers?.length > 0
              // Always show a meaningful name
              const sName = source.name || source.title || source.source_id || `Source ${idx + 1}`
              const frNums: string[] = source.source_fr_numbers || []
              const isDismissed = dismissedSources.has(sourceKey(sName, sourcesQuestion))
              
              return (
                <div 
                  key={idx} 
                  className={`p-4 rounded-xl border-2 transition-all duration-200 ${
                    isDismissed
                      ? 'bg-gray-50 border-gray-200 opacity-50'
                      : isTable
                      ? 'bg-blue-50 border-blue-200 hover:border-blue-400 hover:shadow-md'
                      : isFiche
                      ? 'bg-purple-50 border-purple-200 hover:border-purple-400 hover:shadow-md'
                      : 'bg-gray-50 border-gray-200 hover:border-gray-400 hover:shadow-md'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {isTable ? (
                      <Database className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                    ) : (
                      <FileText className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      {/* Name row + action buttons */}
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-semibold ${isDismissed ? 'line-through text-gray-400' : 'text-gray-900'}`}>
                            {sName}
                          </p>
                          {frNums.length > 0 && (
                            <p className="text-xs text-purple-600 font-medium mt-0.5">
                              {frNums.map(f => `FR ${f}`).join(' · ')}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {!isDismissed && (
                            <button
                              onClick={() => { handleCiteSource(source); setShowSources(false) }}
                              className={`p-1.5 rounded-md transition-colors text-xs flex items-center gap-1 font-medium ${
                                isFiche ? 'text-purple-500 hover:bg-purple-100' : isTable ? 'text-blue-500 hover:bg-blue-100' : 'text-gray-500 hover:bg-gray-100'
                              }`}
                              title="Poser une question sur cette source"
                            >
                              <Quote className="w-3.5 h-3.5" />
                              <span className="hidden group-hover:inline text-xs">Citer</span>
                            </button>
                          )}
                          {!isDismissed && (
                            <button
                              onClick={() => handleDismissSource(source, sourcesQuestion)}
                              className="p-1.5 rounded-md text-gray-400 hover:bg-red-50 hover:text-red-500 transition-colors"
                              title="Marquer comme non pertinent"
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {isDismissed && (
                            <span className="text-xs text-orange-500 font-medium">Signalé</span>
                          )}
                        </div>
                      </div>
                      {/* Content snippet if available */}
                      {source.content_snippet && (
                        <p className="text-xs text-gray-600 mb-2 line-clamp-2">
                          {source.content_snippet}
                        </p>
                      )}
                      {/* Relevance bar */}
                      {source.relevance !== undefined && source.relevance > 0 && (
                        <div className="flex items-center gap-2 mt-1">
                          <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                            <div 
                              className={`h-full ${
                                isTable ? 'bg-blue-500' : isFiche ? 'bg-purple-500' : 'bg-gray-500'
                              }`}
                              style={{ width: `${Math.min(source.relevance * 100, 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500 font-medium">
                            {(source.relevance * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
