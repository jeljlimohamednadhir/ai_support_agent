import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Chatbot API
export const sendMessage = async (data: { message: string; conversation_id?: string | null }) => {
  const response = await api.post('/chatbot/chat', {
    content: data.message,
    role: 'user'
  })
  return response.data
}

// Collector API
export const startCodeCollection = async (repo_url: string, branch: string = 'main') => {
  const response = await api.post('/collector/collect/code', { repo_url, branch })
  return response.data
}

// Knowledge API
export const searchKnowledge = async (query: string) => {
  const response = await api.post('/knowledge/search', { query, limit: 10 })
  return response.data
}

// Validation API
export const getPendingValidations = async (limit: number = 50) => {
  const response = await api.get('/validation/pending', { params: { limit } })
  return response.data
}

export const submitValidation = async (data: any) => {
  const response = await api.post('/validation/submit', data)
  return response.data
}

// Dashboard API
export const getDashboardStats = async () => {
  const response = await api.get('/dashboard/stats')
  return response.data
}

export const getActivityChart = async () => {
  const response = await api.get('/dashboard/activity')
  return response.data
}

export const getRecentIssues = async (limit: number = 10) => {
  const response = await api.get('/dashboard/recent-issues', { params: { limit } })
  return response.data
}

// Configuration API
export const getConfig = async () => {
  const response = await api.get('/config/')
  return response.data
}

export const getConfigByCategory = async (category: string) => {
  const response = await api.get(`/config/category/${category}`)
  return response.data
}

export const getConfigItem = async (key: string) => {
  const response = await api.get(`/config/${key}`)
  return response.data
}

export const updateConfigItem = async (key: string, value: any) => {
  const response = await api.put(`/config/${key}`, { value })
  return response.data
}

export const updateBulkConfig = async (config: any) => {
  const response = await api.post('/config/bulk', config)
  return response.data
}

export const resetConfig = async () => {
  const response = await api.post('/config/reset')
  return response.data
}

export default api
