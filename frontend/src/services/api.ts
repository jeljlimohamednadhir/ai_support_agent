import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Chatbot API
export const sendMessage = async (data: {
  message: string
  conversation_id?: string | null
  conversation_history?: Array<{ role: string; content: string }>
}) => {
  const response = await api.post('/chatbot/chat', {
    content: data.message,
    role: 'user',
    conversation_id: data.conversation_id ?? null,
    conversation_history: data.conversation_history ?? null,
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

export const getBrasilPresentation = async () => {
  const response = await api.get('/knowledge/brasil')
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

// Chatbot N3 Validation API
export const getChatbotTasks = async (limit = 50, offset = 0) => {
  const res = await api.get('/validation/chatbot-tasks', { params: { limit, offset } })
  return res.data
}

export const getChatbotStats = async () => {
  const res = await api.get('/validation/chatbot-stats')
  return res.data
}

export const approveChatbotTask = async (taskId: number, validatorId: string, comment = '') =>
  (await api.post(`/validation/chatbot-tasks/${taskId}/approve`, { validator_id: validatorId, comment })).data

export const correctChatbotTask = async (
  taskId: number,
  validatorId: string,
  correctedResponse: string,
  correctionReason: string,
) =>
  (await api.post(`/validation/chatbot-tasks/${taskId}/correct`, {
    validator_id: validatorId,
    corrected_response: correctedResponse,
    correction_reason:  correctionReason,
  })).data

export const rejectChatbotTask = async (taskId: number, validatorId: string, reason: string) =>
  (await api.post(`/validation/chatbot-tasks/${taskId}/reject`, { validator_id: validatorId, reason })).data

export const escalateChatbotTask = async (taskId: number, escalatedBy: string, note: string) =>
  (await api.post(`/validation/chatbot-tasks/${taskId}/escalate`, { escalated_by: escalatedBy, escalation_note: note })).data

export const triggerRetraining = async () =>
  (await api.post('/validation/retrain', { triggered_by: 'n3_dashboard' })).data

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
