/**
 * Correction Service
 * API client for the /api/v1/corrections endpoints (AI Training Interface)
 */
import api from './api'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface CorrectionRequest {
  query: string
  original_response: string
  corrected_response: string
  entity_name: string
  entity_type?: string
  hypothesis_id: string
  correction_type: 'reinforce' | 'suppress'
  corrected_root_cause?: string
  corrected_actions?: string[]
  operator_id?: string
  error_tags?: string[]
}

export interface CorrectionResponse {
  id: string
  created_at: string
  hypothesis_id: string
  correction_type: 'reinforce' | 'suppress'
  entity_name: string
  applied: boolean
  message: string
}

export interface CorrectionStats {
  total: number
  reinforce: number
  suppress: number
  /** Optional extended stats returned by backend */
  tier_distribution?: {
    HIGH: number
    MEDIUM: number
    LOW: number
  }
  today_count?: number
}

export interface SuppressedHypothesis {
  hypothesis_id: string
  suppression_delta: number
  description: string
}

export interface MaintenanceResult {
  status: string
  tasks: Record<string, unknown>
  duration_seconds?: number
}

/** Pattern Insight — per-hypothesis usage analytics */
export interface PatternInsight {
  hypothesis_id: string
  description: string
  appeared_count: number
  confirmed_count: number
  rejected_count: number
  success_rate: number
  confidence_score: number
  trend: 'up' | 'down' | 'stable' | 'unknown'
}

/** Devil's Advocate alternative hypothesis (from orchestrator) */
export interface DevilAdvocate {
  alternative_hypothesis: string
  alternative_id: string
  alternative_confidence: number
  delta_vs_top: number
  root_cause: string
  reason: string
}

/** A "weak pattern" item surfaced for human review */
export interface WeakPattern {
  id: string
  entity_name: string
  entity_type: string
  hypothesis_id: string
  query: string
  pattern_score: number
  evidence_count: number
  source: string
  validation_tier: 'LOW' | 'MEDIUM' | 'HIGH'
  validation_score: number
  needs_review: boolean
  root_cause?: string
  suggested_actions?: string[]
  created_at: string
}

// ─────────────────────────────────────────────────────────────────────────────
// API functions
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetch aggregated correction statistics + tier distribution
 */
export const fetchCorrectionStats = async (): Promise<CorrectionStats> => {
  const res = await api.get<CorrectionStats>('/corrections/stats')
  return res.data
}

/**
 * Submit a human correction (reinforce or suppress)
 */
export const submitCorrection = async (req: CorrectionRequest): Promise<CorrectionResponse> => {
  const res = await api.post<CorrectionResponse>('/corrections/', req)
  return res.data
}

/**
 * Fetch hypotheses currently suppressed due to repeated failures
 */
export const fetchSuppressed = async (threshold = 3): Promise<SuppressedHypothesis[]> => {
  const res = await api.get<SuppressedHypothesis[]>('/corrections/suppressed', {
    params: { threshold },
  })
  return res.data
}

/**
 * Fetch Pattern Insight for a hypothesis (appeared/confirmed/rejected counts + trend)
 */
export const fetchPatternInsight = async (hypothesisId: string): Promise<PatternInsight> => {
  const res = await api.get<PatternInsight>(`/corrections/pattern-insight/${hypothesisId}`)
  return res.data
}

/**
 * Trigger the daily maintenance job
 */
export const runMaintenance = async (dryRun = false): Promise<MaintenanceResult> => {
  const res = await api.post<MaintenanceResult>('/corrections/maintenance', null, {
    params: { dry_run: dryRun },
  })
  return res.data
}

/**
 * Fetch weak-pattern candidates pending human review.
 * Backend: GET /corrections/weak-patterns  (or falls back to suppressed list)
 */
export const fetchWeakPatterns = async (): Promise<WeakPattern[]> => {
  try {
    const res = await api.get<WeakPattern[]>('/corrections/weak-patterns')
    return res.data
  } catch {
    // Endpoint may not be implemented yet — return empty list gracefully
    return []
  }
}
