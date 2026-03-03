/**
 * Chat Store (Zustand)
 * Manages chat state with localStorage persistence
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ChatConversation, ChatMessage } from '../services/chatService';

interface ChatState {
  conversations: ChatConversation[];
  activeConversationId: number | null;
  messages: ChatMessage[];
  
  // Actions
  setConversations: (conversations: ChatConversation[]) => void;
  addConversation: (conversation: ChatConversation) => void;
  updateConversation: (id: number, conversation: Partial<ChatConversation>) => void;
  deleteConversation: (id: number) => void;
  
  setActiveConversation: (id: number | null) => void;
  
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  
  // Reset everything
  reset: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      conversations: [],
      activeConversationId: null,
      messages: [],
      
      setConversations: (conversations) => set({ conversations }),
      
      addConversation: (conversation) =>
        set((state) => ({
          conversations: [conversation, ...state.conversations],
        })),
      
      updateConversation: (id, updates) =>
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id ? { ...conv, ...updates } : conv
          ),
        })),
      
      deleteConversation: (id) =>
        set((state) => ({
          conversations: state.conversations.filter((conv) => conv.id !== id),
          activeConversationId:
            state.activeConversationId === id ? null : state.activeConversationId,
          messages: state.activeConversationId === id ? [] : state.messages,
        })),
      
      setActiveConversation: (id) => set({ activeConversationId: id }),
      
      setMessages: (messages) => set({ messages }),
      
      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),
      
      clearMessages: () => set({ messages: [] }),
      
      reset: () =>
        set({
          conversations: [],
          activeConversationId: null,
          messages: [],
        }),
    }),
    {
      name: 'chat-storage', // localStorage key
      partialize: (state) => ({
        conversations: state.conversations,
        activeConversationId: state.activeConversationId,
        // Persist conversations list and active ID
        // Messages will be reloaded from backend on mount
      }),
    }
  )
);
