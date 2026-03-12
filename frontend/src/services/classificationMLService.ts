/**
 * Classification ML Service
 * API client for classification ML endpoints
 */
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const BASE_URL = `${API_URL}/classification-ml`;

export interface UploadResponse {
  columns: string[];
  preview: Record<string, any>[];
  stats?: Record<string, any>;
  n_rows: number;
  detected_columns?: Record<string, string | null>;
  session_id?: string;
}

export interface TrainRequest {
  text_col?: string;
  label_col: string;
  max_features?: number;
  use_cause_hint?: boolean;
  test_size?: number;
  session_id?: string;
}

export interface TrainResponse {
  metrics: {
    classification_report: string;
    macro_f1: number | null;
    confusion_matrix: number[][];
  };
  recommended_threshold: number;
  classes: string[];
  training_count: number;
  trained_at: string;
  weak_points: Array<{ type: string; detail: string; severity: string }>;
}

export interface PredictRequest {
  tickets: Array<{ ticket_id: string; text: string }>;
  threshold?: number;
  session_id?: string;
}

export interface PredictionResult {
  ticket_id: string;
  predicted_label: string;
  confidence: number;
  all_probabilities?: Record<string, number>;
  accepted: boolean;
}

export interface PredictResponse {
  predictions: PredictionResult[];
  stats: {
    total: number;
    accepted: number;
    rejected: number;
    coverage: number;
  };
  updated_preview?: Record<string, any>[];
}

export interface SavedFileInfo {
  session_id: string;
  filename: string;
  n_rows: number;
  columns: string[];
  uploaded_at: string;
}

export interface CorrectionRequest {
  ticket_id: string;
  corrected_label: string;
  original_label: string;
  text?: string;
  reason?: string;
}

export interface KeywordsConfig {
  categories: Record<string, string[]>;
}

export interface ParetoItem {
  label: string;
  volume: number;
  percentage: number;
  cumulative: number;
}

export interface TimeseriesPoint {
  date: string;
  volume: number;
  label?: string;
}

export interface TopValue {
  name: string;
  volume: number;
}

export interface CriticalityScore {
  category: string;
  score: number;
  volume: number;
  mttr?: number;
  badge: 'high' | 'medium' | 'low';
  rationale: string;
}

export interface TemporalAnomaly {
  period: string;
  volume: number;
  delta_pct: number;
  direction: 'spike' | 'drop';
  hypothesis: string;
}

export interface AIRecommendation {
  priority: number;
  action: string;
  impact: 'high' | 'medium' | 'low';
  category: string;
}

export interface ExecSummary {
  volume: number;
  mttr_med: number | null;
  top_causes: Array<{ cause: string; volume: number; pct: number }>;
  top_categories: Array<{ category: string; volume: number; pct: number }>;
  top_codes: Array<{ code: string; volume: number }>;
  highlights: string[];
  recommendations: string[];
  // AI fields (ideas 1+2+3+4)
  ai_narrative?: string;
  ai_recommendations?: AIRecommendation[];
  criticality_scores?: CriticalityScore[];
  temporal_anomalies?: TemporalAnomaly[];
  ai_generated: boolean;
  date_range?: { start: string; end: string };
}

export interface ModelInfo {
  exists: boolean;
  trained_at?: string;
  training_count: number;
  label_col?: string;
  n_samples?: number;
  classes: string[];
  macro_f1?: number;
  recommended_threshold: number;
  weak_points: Array<{ type: string; detail: string; severity: string }>;
}

export interface IndexRAGLaunched {
  source: string;
  count?: number;
  collection?: string;
  parser?: string;
  note?: string;
}

export interface IndexRAGResult {
  source: string;
  message: string;
  launched: IndexRAGLaunched[];
  errors: string[];
}

export const classificationMLService = {
  /**
   * Upload CSV file
   */
  async uploadCSV(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await axios.post<UploadResponse>(`${BASE_URL}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
  },

  /**
   * Prepare data (compute features)
   */
  async prepareData(params: { extended_semantic?: boolean; compute_causes?: boolean; compute_categories?: boolean }) {
    const { data } = await axios.post(`${BASE_URL}/prepare`, params);
    return data;
  },

  /**
   * Get keywords configuration
   */
  async getKeywordsConfig(): Promise<KeywordsConfig> {
    const { data } = await axios.get<KeywordsConfig>(`${BASE_URL}/keywords-config`);
    return data;
  },

  /**
   * Save keywords configuration
   */
  async saveKeywordsConfig(config: KeywordsConfig): Promise<KeywordsConfig> {
    const { data } = await axios.put<KeywordsConfig>(`${BASE_URL}/keywords-config`, config);
    return data;
  },

  /**
   * Reset keywords to defaults
   */
  async resetKeywordsConfig() {
    const { data } = await axios.post(`${BASE_URL}/keywords-config/reset`);
    return data;
  },

  /**
   * Train ML model
   */
  async trainModel(request: TrainRequest): Promise<TrainResponse> {
    const { data } = await axios.post<TrainResponse>(`${BASE_URL}/train`, request);
    return data;
  },

  /**
   * Get model information
   */
  async getModelInfo(): Promise<ModelInfo> {
    const { data } = await axios.get<ModelInfo>(`${BASE_URL}/model-info`);
    return data;
  },

  /**
   * Predict labels for a small list of tickets (pass tickets array)
   */
  async predict(request: PredictRequest): Promise<PredictResponse> {
    const { data } = await axios.post<PredictResponse>(`${BASE_URL}/predict`, request);
    return data;
  },

  /**
   * Predict ALL tickets from the stored session (no ticket list needed)
   */
  async predictSession(sessionId: string, threshold: number): Promise<PredictResponse> {
    const { data } = await axios.post<PredictResponse>(`${BASE_URL}/predict-session`, {
      tickets: [],
      threshold,
      session_id: sessionId
    });
    return data;
  },

  /**
   * Save manual correction
   */
  async saveCorrection(request: CorrectionRequest) {
    const { data } = await axios.post(`${BASE_URL}/corrections`, request);
    return data;
  },

  /**
   * Get corrections statistics
   */
  async getCorrectionsStats() {
    const { data } = await axios.get(`${BASE_URL}/corrections/stats`);
    return data;
  },

  /**
   * Get Pareto analysis
   */
  async getPareto(column: string): Promise<{ items: ParetoItem[]; column: string }> {
    const { data } = await axios.get(`${BASE_URL}/pareto`, { params: { column } });
    return data;
  },

  /**
   * Get timeseries data
   */
  async getTimeseries(dateCol: string, groupBy?: string): Promise<{ data: TimeseriesPoint[]; date_col: string }> {
    const { data } = await axios.get(`${BASE_URL}/timeseries`, {
      params: { date_col: dateCol, group_by: groupBy }
    });
    return data;
  },

  /**
   * Get top values for a column
   */
  async getTopValues(column: string, topn: number = 10): Promise<{ items: TopValue[]; column: string; total: number }> {
    const { data } = await axios.get(`${BASE_URL}/top-values`, {
      params: { column, topn }
    });
    return data;
  },

  /**
   * Get executive summary (avec IA par défaut)
   */
  async getExecSummary(ai: boolean = true): Promise<ExecSummary> {
    const { data } = await axios.get<ExecSummary>(`${BASE_URL}/exec-summary`, {
      params: { ai }
    });
    return data;
  },

  /**
   * Export PDF enrichi (idée 7)
   */
  async exportPDF(params: {
    title?: string;
    rca_text?: string;
    recommendations?: string[];
    synthesis?: any;
    ai_narrative?: string;
    ai_recommendations?: string[];
    criticality_scores?: CriticalityScore[];
    temporal_anomalies?: TemporalAnomaly[];
    top_causes?: Array<{ cause: string; volume: number; pct: number }>;
    top_categories?: Array<{ category: string; volume: number; pct: number }>;
    top_codes?: Array<{ code: string; volume: number }>;
    volume?: number;
    mttr_med?: number | null;
  }) {
    const payload = {
      title: params.title || 'Rapport ML',
      rca_text: params.rca_text,
      recommendations: params.recommendations,
      ai_narrative: params.ai_narrative,
      ai_recommendations: params.ai_recommendations,
      criticality_scores: params.criticality_scores,
      temporal_anomalies: params.temporal_anomalies,
      top_causes: params.top_causes,
      top_categories: params.top_categories,
      top_codes: params.top_codes,
      volume: params.volume,
      mttr_med: params.mttr_med,
    };
    const { data } = await axios.post(`${BASE_URL}/export-pdf`, payload, {
      responseType: 'blob'
    });
    return data;
  },

  /**
   * List all previously saved CSV uploads
   */
  async listFiles(): Promise<SavedFileInfo[]> {
    const { data } = await axios.get<SavedFileInfo[]>(`${BASE_URL}/files`);
    return data;
  },

  /**
   * Load a previously saved file from disk into active session
   */
  async loadSavedFile(sessionId: string): Promise<UploadResponse> {
    const { data } = await axios.post<UploadResponse>(`${BASE_URL}/files/${sessionId}/load`);
    return data;
  },

  /**
   * Index tickets for RAG chatbot (legacy single-source)
   */
  async indexTickets(): Promise<{ message: string; ticket_count: number; text_columns: string[] }> {
    const { data } = await axios.post(`${BASE_URL}/index-tickets`);
    return data;
  },

  /**
   * RAG multi-source indexation : tickets (SmartN3Parser) | fr | logs | all
   */
  async indexRAG(
    source: 'tickets' | 'fr' | 'logs' | 'all',
    options?: { fr_dir?: string; log_file?: string },
  ): Promise<IndexRAGResult> {
    const { data } = await axios.post<IndexRAGResult>(`${BASE_URL}/index-rag`, {
      source,
      ...options,
    });
    return data;
  },

  /**
   * Idée 5 : injecter le résumé ML dans Qdrant pour le chatbot
   */
  async injectInsights(): Promise<{ message: string; text_length: number }> {
    const { data } = await axios.post<{ message: string; text_length: number }>(`${BASE_URL}/inject-insights`);
    return data;
  },

  /**
   * Idée 6 : réentraîner le modèle avec les corrections validées
   */
  async retrainWithCorrections(): Promise<{
    message: string;
    corrections_merged: number;
    total_samples: number;
    macro_f1?: number;
    recommended_threshold?: number;
  }> {
    const { data } = await axios.post(`${BASE_URL}/retrain-with-corrections`);
    return data;
  }
};
