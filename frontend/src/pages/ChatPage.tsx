import { useState, useEffect } from 'react'
import ChatInterface from '@/components/chatbot/ChatInterface'
import ChatHistory from '@/components/chatbot/ChatHistory'
import { useChatStore } from '@/stores/chatStore'
import { chatService } from '@/services/chatService'

export default function ChatPage() {
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)
  const [historyVisible, setHistoryVisible] = useState(true)
  const { 
    conversations, 
    activeConversationId, 
    setConversations, 
    setActiveConversation,
    deleteConversation,
  } = useChatStore()
  
  // Load conversations from backend on mount
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const convs = await chatService.listConversations()
        setConversations(convs)
        
        // If there's an active conversation ID from localStorage but no conversations loaded yet,
        // ensure we maintain the selection
        if (activeConversationId && convs.length > 0) {
          const found = convs.find(c => c.id === activeConversationId)
          if (found) {
            setSelectedConversation(String(activeConversationId))
          }
        }
      } catch (error) {
        console.error('Failed to load conversations:', error)
        // On error, try to use persisted conversations from localStorage
        // (already loaded by Zustand)
      }
    }
    
    loadConversations()
  }, [setConversations, activeConversationId])
  
  const handleNewConversation = async () => {
    try {
      const newConv = await chatService.createConversation({ 
        title: 'Nouvelle conversation' 
      })
      setConversations([newConv, ...conversations])
      setActiveConversation(newConv.id)
      setSelectedConversation(String(newConv.id))
    } catch (error) {
      console.error('Failed to create conversation:', error)
    }
  }
  
  const handleSelectConversation = (id: string) => {
    setSelectedConversation(id)
    setActiveConversation(Number(id))
  }

  const handleDeleteConversation = async (id: number) => {
    try {
      await chatService.deleteConversation(id)
      deleteConversation(id)
      // If we deleted the active conversation, clear selection
      if (activeConversationId === id) {
        setSelectedConversation(null)
        setActiveConversation(null)
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  }
  
  return (
    <div className="h-full flex relative">
      <ChatHistory
        selectedConversation={selectedConversation}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        visible={historyVisible}
        onToggle={() => setHistoryVisible(!historyVisible)}
      />
      <ChatInterface 
        conversationId={selectedConversation}
        onToggleHistory={() => setHistoryVisible(!historyVisible)}
        historyVisible={historyVisible}
      />
    </div>
  )
}
