import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1', timeout: 30_000 })

// ── Jobs ──────────────────────────────────────────────────────────────────────

export interface CreateJobReq {
  task_name: string
  data_path: string
  output_path: string
  custom_config?: Record<string, unknown>
}

export interface Job {
  job_id: string
  task_name: string
  status: string
  created_at: string
  updated_at?: string
  progress_summary: string
  retry_count: number
  circuit_breaker_triggered: boolean
  flagged_record_count: number
  rows_before?: number
  rows_after?: number
  error_messages: string[]
  result_path?: string
}

export const createJob   = (req: CreateJobReq) => api.post<{ job_id: string; status: string }>('/jobs', req)
export const getJob      = (id: string)         => api.get<Job>(`/jobs/${id}`)
export const getAuditLog = (id: string)         => api.get<unknown[]>(`/jobs/${id}/audit-log`)
export const approveJob  = (id: string)         => api.post(`/jobs/${id}/approve`)
export const abortJob    = (id: string)         => api.post(`/jobs/${id}/abort`)

// ── Tasks ─────────────────────────────────────────────────────────────────────

export interface TaskSummary {
  task: string
  version: number
  description: string
  cleaning_strategy_type: string
  metrics: string[]
  max_retries: number
}

export const listTasks = () => api.get<TaskSummary[]>('/tasks')
export const getTask   = (name: string) => api.get<Record<string, unknown>>(`/tasks/${name}`)

// ── Evaluation ────────────────────────────────────────────────────────────────

export interface EvalResult {
  eval_id: string
  status: string
  generated_at?: string
  results?: Record<string, Record<string, number>>
  overall_weighted_score?: number
  error?: string
}

export const triggerEval = (tasks: string, benchmark_dir?: string) =>
  api.post<{ eval_id: string; tasks: string[]; status: string }>('/evaluate', { tasks, benchmark_dir })
export const getEval = (id: string) => api.get<EvalResult>(`/evaluate/${id}`)

// ── Memory ────────────────────────────────────────────────────────────────────

export interface MemoryEntry {
  id: string
  type: 'short' | 'long'
  category: string
  task_name: string
  summary: string
  tags: string[]
  score: number
  created_at: string
  last_used: string
  use_count: number
}

export interface TemplateEntry {
  id: string
  name: string
  task_name: string
  description: string
  tags: string[]
  config_snippet: Record<string, unknown>
  score: number
  use_count: number
  created_at: string
}

export const listMemories  = (type?: string)   => api.get<MemoryEntry[]>('/memory', { params: { type } })
export const searchMemory  = (q: string)        => api.get<MemoryEntry[]>('/memory/search', { params: { q } })
export const listTemplates = (task?: string)    => api.get<TemplateEntry[]>('/memory/templates', { params: { task } })
export const applyTemplate = (id: string)       => api.get<TemplateEntry>(`/memory/templates/${id}`)
export const deleteMemory  = (id: string)       => api.delete(`/memory/${id}`)

// ── LLM ──────────────────────────────────────────────────────────────────────

export interface LLMStatus {
  provider: string
  model: string
  base_url: string
  reachable: boolean
  available_models: string[]
}

export const getLLMStatus = () => api.get<LLMStatus>('/llm/status')
