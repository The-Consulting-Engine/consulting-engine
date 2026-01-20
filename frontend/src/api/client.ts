import axios from 'axios'

const API_BASE = '/api'

export const api = axios.create({
  baseURL: API_BASE,
})

// Runs
export const createRun = async (data: { vertical_id: string; company_name?: string; notes?: string }) => {
  const response = await api.post('/runs/', data)
  return response.data
}

export const getRun = async (runId: number) => {
  const response = await api.get(`/runs/${runId}`)
  return response.data
}

export const deleteRun = async (runId: number) => {
  const response = await api.delete(`/runs/${runId}`)
  return response.data
}

export const listRuns = async () => {
  const response = await api.get('/runs/')
  return response.data
}

export const listVerticals = async () => {
  const response = await api.get('/runs/verticals/list')
  return response.data
}

// Uploads
export const uploadFile = async (runId: number, packType: string, file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('pack_type', packType)
  
  const response = await api.post(`/uploads/${runId}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export const listUploads = async (runId: number) => {
  const response = await api.get(`/uploads/${runId}/uploads`)
  return response.data
}

export const suggestMappings = async (runId: number, uploadId: number) => {
  const response = await api.post(`/uploads/${runId}/uploads/${uploadId}/suggest-mappings`)
  return response.data
}

// Mappings
export const confirmMappings = async (runId: number, data: any) => {
  const response = await api.post(`/mappings/${runId}/confirm`, data)
  return response.data
}

export const getMappings = async (runId: number) => {
  const response = await api.get(`/mappings/${runId}/mappings`)
  return response.data
}

// Analytics
export const analyzeRun = async (runId: number) => {
  const response = await api.post(`/analytics/${runId}/analyze`)
  return response.data
}

export const getResults = async (runId: number) => {
  const response = await api.get(`/analytics/${runId}/results`)
  return response.data
}

// Reports
export const generateMemo = async (runId: number) => {
  const response = await api.post(`/reports/${runId}/generate-memo`)
  return response.data
}

export const generateDeck = async (runId: number) => {
  const response = await api.post(`/reports/${runId}/generate-deck`)
  return response.data
}

export const listReports = async (runId: number) => {
  const response = await api.get(`/reports/${runId}/reports`)
  return response.data
}

export const downloadReport = (reportId: number) => {
  return `${API_BASE}/reports/download/${reportId}`
}

// Questions
export const getQuestions = async (runId: number) => {
  const response = await api.get(`/questions/${runId}/questions`)
  return response.data
}

export const saveResponses = async (runId: number, responses: any[]) => {
  const response = await api.post(`/questions/${runId}/responses`, { responses })
  return response.data
}

export const getResponses = async (runId: number) => {
  const response = await api.get(`/questions/${runId}/responses`)
  return response.data
}

export const getContext = async (runId: number) => {
  const response = await api.get(`/questions/${runId}/context`)
  return response.data
}
