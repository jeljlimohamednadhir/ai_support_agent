/**
 * Chat Service
 * Handles API calls for chat conversations and messages
 */
import axios, { AxiosInstance } from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatConversation {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
  messages?: ChatMessage[];
}

export interface ConversationCreate {
  title?: string;
}

export interface MessageCreate {
  role: 'user' | 'assistant';
  content: string;
}

class ChatService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to include token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );
  }

  async listConversations(skip: number = 0, limit: number = 50): Promise<ChatConversation[]> {
    const response = await this.api.get<ChatConversation[]>('/chat/conversations', {
      params: { skip, limit },
    });
    return response.data;
  }

  async createConversation(data: ConversationCreate): Promise<ChatConversation> {
    const response = await this.api.post<ChatConversation>('/chat/conversations', data);
    return response.data;
  }

  async getConversation(conversationId: number): Promise<ChatConversation> {
    const response = await this.api.get<ChatConversation>(`/chat/conversations/${conversationId}`);
    return response.data;
  }

  async updateConversation(conversationId: number, data: ConversationCreate): Promise<ChatConversation> {
    const response = await this.api.put<ChatConversation>(`/chat/conversations/${conversationId}`, data);
    return response.data;
  }

  async deleteConversation(conversationId: number): Promise<void> {
    await this.api.delete(`/chat/conversations/${conversationId}`);
  }

  async addMessage(conversationId: number, message: MessageCreate): Promise<ChatMessage> {
    const response = await this.api.post<ChatMessage>(
      `/chat/conversations/${conversationId}/messages`,
      message
    );
    return response.data;
  }

  async listMessages(conversationId: number, skip: number = 0, limit: number = 100): Promise<ChatMessage[]> {
    const response = await this.api.get<ChatMessage[]>(
      `/chat/conversations/${conversationId}/messages`,
      {
        params: { skip, limit },
      }
    );
    return response.data;
  }
}

export const chatService = new ChatService();
