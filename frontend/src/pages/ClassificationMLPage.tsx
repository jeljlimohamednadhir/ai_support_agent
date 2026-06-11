/**
 * Classification ML Page
 * Main page for ML-based ticket classification
 */
import React, { useState, useEffect } from 'react';
import {
  Upload,
  Brain,
  FileCheck,
  Settings,
  FileDown,
  AlertCircle,
  TrendingUp,
  CheckCircle,
  Clock,
  BarChart3,
  PieChart,
  Database,
  Loader,
  Zap,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  BookOpen,
  History,
  FolderOpen,
  Activity,
  Shield,
  RotateCcw,
  Download
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { usePageStateStore } from '../stores/pageStateStore';
import { classificationMLService, type UploadResponse, type TrainResponse, type ModelInfo, type PredictResponse, type ExecSummary, type CriticalityScore, type TemporalAnomaly, type AIRecommendation, type SavedFileInfo } from '../services/classificationMLService';
import { MetricCard } from '../components/ml/MetricCard';
import { ParetoChart } from '../components/ml/ParetoChart';
import { TimelineChart } from '../components/ml/TimelineChart';
import { ConfusionMatrixDisplay } from '../components/ml/ConfusionMatrixDisplay';
import { KeywordsConfigEditor } from '../components/ml/KeywordsConfigEditor';
import { TopList } from '../components/ml/TopList';

type Tab = 'resume' | 'synthese' | 'analyse' | 'training' | 'correction' | 'config' | 'export' | 'monitoring';

export const ClassificationMLPage: React.FC = () => {
  const { canCorrectML } = useAuth(); // Get permission to correct ML

  // Persisted state via pageStateStore (survives navigation)
  const { ml, setMLUploadedData, setMLSessionId, setMLActiveTab, setMLThreshold } = usePageStateStore();
  const activeTab = ml.activeTab as Tab;
  const setActiveTab = (tab: Tab) => setMLActiveTab(tab);
  const uploadedData = ml.uploadedData as UploadResponse | null;
  const setUploadedData = (data: UploadResponse | null) => setMLUploadedData(data);
  const sessionId = ml.sessionId;
  const setSessionId = (id: string | null) => setMLSessionId(id);
  const threshold = ml.threshold;
  const setThreshold = (v: number) => setMLThreshold(v);

  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [predictions, setPredictions] = useState<PredictResponse | null>(null);
  const [execSummary, setExecSummary] = useState<ExecSummary | null>(null);
  const [trainingResult, setTrainingResult] = useState<TrainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [indexingStatus, setIndexingStatus] = useState<'idle' | 'indexing' | 'done'>('idle');
  const [savedFiles, setSavedFiles] = useState<SavedFileInfo[]>([]);
  const [showFileHistory, setShowFileHistory] = useState(false);

  // Load model info on mount — uploadedData/sessionId/tab/threshold are auto-restored from store
  useEffect(() => {
    loadModelInfo();
    loadSavedFiles();
  }, []);

  const loadSavedFiles = async () => {
    try {
      const files = await classificationMLService.listFiles();
      setSavedFiles(files);
    } catch (err) {
      console.error('Failed to load saved files:', err);
    }
  };

  const loadModelInfo = async () => {
    try {
      const info = await classificationMLService.getModelInfo();
      setModelInfo(info);
      if (info.recommended_threshold) {
        setThreshold(info.recommended_threshold);
      }
    } catch (err) {
      console.error('Failed to load model info:', err);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const response = await classificationMLService.uploadCSV(file);
      setUploadedData(response);
      if (response.session_id) {
        setSessionId(response.session_id);
      }

      // Auto-prepare data
      await classificationMLService.prepareData({
        compute_causes: true,
        compute_categories: true
      });

      // Load exec summary if data is ready
      if (response.n_rows > 0) {
        const summary = await classificationMLService.getExecSummary();
        setExecSummary(summary);
      }
      // Refresh saved files list
      await loadSavedFiles();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSavedFile = async (fileInfo: SavedFileInfo) => {
    setLoading(true);
    setError(null);
    setShowFileHistory(false);
    try {
      const response = await classificationMLService.loadSavedFile(fileInfo.session_id);
      setUploadedData(response);
      if (response.session_id) {
        setSessionId(response.session_id);
      }
      // Refresh exec summary
      if (response.n_rows > 0) {
        const summary = await classificationMLService.getExecSummary();
        setExecSummary(summary);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load saved file');
    } finally {
      setLoading(false);
    }
  };

  const handleTrainModel = async (params: {
    labelCol: string;
    maxFeatures: number;
    useCauseHint: boolean;
  }) => {
    setLoading(true);
    setError(null);

    try {
      const result = await classificationMLService.trainModel({
        label_col: params.labelCol,
        max_features: params.maxFeatures,
        use_cause_hint: params.useCauseHint,
        session_id: sessionId || undefined, // Envoyer session_id pour restaurer données
      });
      setTrainingResult(result);
      setThreshold(result.recommended_threshold);
      await loadModelInfo();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Training failed');
    } finally {
      setLoading(false);
    }
  };

  const handleIndexTickets = async () => {
    if (!uploadedData) {
      setError('Upload CSV first');
      return;
    }

    setIndexingStatus('indexing');
    setError(null);

    try {
      const response = await classificationMLService.indexTickets();
      console.log('Indexation started:', response);
      setIndexingStatus('done');
      setTimeout(() => setIndexingStatus('idle'), 3000); // Reset après 3s
    } catch (err: any) {
      console.error('Indexation failed:', err);
      setIndexingStatus('idle');
      setError(err.response?.data?.detail || 'Indexation failed');
    }
  };

  const handlePredict = async () => {
    if (!uploadedData && !sessionId) {
      setError('Veuillez d\'abord importer un fichier CSV');
      return;
    }
    if (!sessionId) {
      setError('Session introuvable — veuillez réimporter le fichier CSV');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await classificationMLService.predictSession(sessionId, threshold);
      setPredictions(result);

      // Update uploadedData with full classified data
      if (result.updated_preview && result.updated_preview.length > 0) {
        const updatedCols = Object.keys(result.updated_preview[0]);
        setUploadedData({
          ...uploadedData,
          columns: updatedCols,
          preview: result.updated_preview,
          stats: uploadedData?.stats ?? {},
          n_rows: uploadedData?.n_rows ?? result.updated_preview.length,
          detected_columns: uploadedData?.detected_columns ?? {},
        });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Prediction failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCorrection = async (ticketId: string, correctedLabel: string, originalLabel: string) => {
    try {
      await classificationMLService.saveCorrection({
        ticket_id: ticketId,
        corrected_label: correctedLabel,
        original_label: originalLabel
      });
      // Optionally retrain model
      alert('Correction saved! Consider retraining the model.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save correction');
    }
  };

  const handleExportPDF = async () => {
    if (!execSummary) return;

    try {
      const blob = await classificationMLService.exportPDF({
        title: 'Rapport Classification ML',
        rca_text: '',
        recommendations: execSummary.recommendations,
        ai_narrative: execSummary.ai_narrative,
        ai_recommendations: execSummary.ai_recommendations?.map(
          (r: AIRecommendation) => `P${r.priority} [${r.impact.toUpperCase()}] ${r.action}`
        ),
        criticality_scores: execSummary.criticality_scores,
        temporal_anomalies: execSummary.temporal_anomalies,
        top_causes: execSummary.top_causes,
        top_categories: execSummary.top_categories,
        top_codes: execSummary.top_codes,
        volume: execSummary.volume,
        mttr_med: execSummary.mttr_med,
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `classification_ml_report_${new Date().toISOString().split('T')[0]}.pdf`;
      a.click();
    } catch (err: any) {
      setError('PDF export failed');
    }
  };

  // Define all tabs
  const allTabs = [
    { id: 'resume' as const, label: 'Résumé Exécutif', icon: TrendingUp },
    { id: 'synthese' as const, label: 'Synthèse', icon: BarChart3 },
    { id: 'analyse' as const, label: 'Analyse Interactive', icon: PieChart },
    { id: 'training' as const, label: 'Entraînement ML', icon: Brain },
    { id: 'correction' as const, label: 'Correction Tickets', icon: FileCheck, requiresCorrection: true },
    { id: 'monitoring' as const, label: 'Monitoring', icon: Activity },
    { id: 'config' as const, label: 'Configuration', icon: Settings },
    { id: 'export' as const, label: 'Export PDF', icon: FileDown }
  ];

  // Filter tabs based on user permissions
  const tabs = allTabs.filter(tab => {
    // Hide correction tab if user doesn't have correction permission
    if (tab.requiresCorrection && !canCorrectML) {
      return false;
    }
    return true;
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Classification ML</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Machine Learning pour la classification automatique des tickets
          </p>
        </div>

        <div className="flex items-center gap-4">
          {modelInfo?.exists && (
            <div className="px-4 py-2 bg-green-100 dark:bg-green-900 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                <span className="text-sm font-medium text-green-800 dark:text-green-200">
                  Modèle entraîné ({modelInfo.training_count} tickets)
                </span>
              </div>
            </div>
          )}

          {uploadedData && (
            <button
              onClick={handleIndexTickets}
              disabled={indexingStatus === 'indexing'}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
            >
              {indexingStatus === 'indexing' ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Indexation...
                </>
              ) : indexingStatus === 'done' ? (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Indexé ✓
                </>
              ) : (
                <>
                  <Database className="w-4 h-4" />
                  Indexer pour RAG
                </>
              )}
            </button>
          )}

          <div className="relative">
            <button
              onClick={() => setShowFileHistory(!showFileHistory)}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors flex items-center gap-2"
              title="Fichiers précédemment chargés"
            >
              <History className="w-5 h-5" />
              Historique
              {savedFiles.length > 0 && (
                <span className="ml-1 bg-blue-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {savedFiles.length}
                </span>
              )}
            </button>

            {showFileHistory && (
              <div className="absolute right-0 top-full mt-2 w-96 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <FolderOpen className="w-4 h-4" />
                    Fichiers sauvegardés
                  </h3>
                  <button onClick={() => setShowFileHistory(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-lg leading-none">&times;</button>
                </div>
                {savedFiles.length === 0 ? (
                  <div className="px-4 py-6 text-center text-gray-500 dark:text-gray-400 text-sm">
                    Aucun fichier sauvegardé
                  </div>
                ) : (
                  <ul className="max-h-72 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700">
                    {savedFiles.map(f => (
                      <li
                        key={f.session_id}
                        className="px-4 py-3 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer transition-colors"
                        onClick={() => handleLoadSavedFile(f)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{f.filename}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                              {f.n_rows.toLocaleString()} lignes · {new Date(f.uploaded_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                            </p>
                            {f.columns.includes('categorie_intelligente') && (
                              <span className="inline-flex items-center gap-1 text-xs text-green-700 dark:text-green-400 mt-1">
                                <CheckCircle className="w-3 h-3" /> Prédit
                              </span>
                            )}
                          </div>
                          <button className="text-blue-600 dark:text-blue-400 text-xs whitespace-nowrap hover:underline">
                            Charger
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          <label className="px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition-colors flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload CSV
            <input type="file" accept=".csv" onChange={handleFileUpload} className="hidden" />
          </label>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-4">
          {tabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-3 border-b-2 transition-colors
                  ${activeTab === tab.id
                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content — kept mounted to preserve local state, hidden via CSS */}
      <div className="min-h-[600px]">
        <div className={activeTab === 'resume' ? '' : 'hidden'}>
          <ResumeExecutifTab execSummary={execSummary} loading={loading} />
        </div>

        <div className={activeTab === 'synthese' ? '' : 'hidden'}>
          <SyntheseTab uploadedData={uploadedData} />
        </div>

        <div className={activeTab === 'analyse' ? '' : 'hidden'}>
          <AnalyseInteractiveTab uploadedData={uploadedData} />
        </div>

        <div className={activeTab === 'training' ? '' : 'hidden'}>
          <TrainingTab
            uploadedData={uploadedData}
            trainingResult={trainingResult}
            modelInfo={modelInfo}
            onTrain={handleTrainModel}
            loading={loading}
          />
        </div>

        <div className={activeTab === 'correction' ? '' : 'hidden'}>
          <CorrectionTab
            predictions={predictions}
            threshold={threshold}
            onThresholdChange={setThreshold}
            onPredict={handlePredict}
            onCorrection={handleCorrection}
            loading={loading}
            modelInfo={modelInfo}
            uploadedData={uploadedData}
          />
        </div>

        <div className={activeTab === 'config' ? '' : 'hidden'}>
          <ConfigTab />
        </div>

        <div className={activeTab === 'export' ? '' : 'hidden'}>
          <ExportTab onExport={handleExportPDF} execSummary={execSummary} />
        </div>

        <div className={activeTab === 'monitoring' ? '' : 'hidden'}>
          <MonitoringTab sessionId={sessionId} />
        </div>
      </div>
    </div>
  );
};

// Tab Components

const BADGE_COLORS = {
  high:   'bg-red-100 text-red-800 border border-red-200',
  medium: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
  low:    'bg-green-100 text-green-800 border border-green-200',
};

const IMPACT_COLORS = {
  high:   'text-red-700 bg-red-50 border-l-4 border-red-400',
  medium: 'text-yellow-700 bg-yellow-50 border-l-4 border-yellow-400',
  low:    'text-green-700 bg-green-50 border-l-4 border-green-400',
};

const ResumeExecutifTab: React.FC<{ execSummary: ExecSummary | null; loading: boolean }> = ({ execSummary, loading }) => {
  const [injecting, setInjecting] = React.useState(false);
  const [injectMsg, setInjectMsg] = React.useState<string | null>(null);

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <Loader className="w-8 h-8 animate-spin text-blue-500" />
      <span className="text-gray-500">Génération de l'analyse IA en cours…</span>
    </div>
  );
  if (!execSummary) return <div className="text-center py-12 text-gray-500">Aucune donnée disponible</div>;

  const handleInjectChatbot = async () => {
    setInjecting(true);
    setInjectMsg(null);
    try {
      const res = await classificationMLService.injectInsights();
      setInjectMsg(`✅ ${res.message}`);
    } catch {
      setInjectMsg('❌ Injection échouée');
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard title="Volume Total" value={execSummary.volume.toLocaleString()} icon={BarChart3} color="blue" />
        <MetricCard title="MTTR Médian" value={execSummary.mttr_med ? `${execSummary.mttr_med.toFixed(1)}j` : 'N/A'} icon={Clock} color="green" />
        <MetricCard title="Catégories" value={execSummary.top_categories.length.toString()} icon={PieChart} color="purple" />
      </div>

      {/* AI Narrative */}
      {execSummary.ai_narrative && (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-700 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100">Synthèse Managériale IA</h3>
            {execSummary.ai_generated && (
              <span className="ml-auto text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">Groq AI</span>
            )}
          </div>
          <p className="text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-line">{execSummary.ai_narrative}</p>
          <button
            onClick={handleInjectChatbot}
            disabled={injecting}
            className="mt-4 flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition disabled:opacity-50"
          >
            {injecting ? <Loader className="w-4 h-4 animate-spin" /> : <BookOpen className="w-4 h-4" />}
            Injecter dans le Chatbot
          </button>
          {injectMsg && <p className="mt-2 text-sm">{injectMsg}</p>}
        </div>
      )}

      {/* AI Recommendations */}
      {execSummary.ai_recommendations && execSummary.ai_recommendations.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-yellow-500" />
            <h3 className="text-lg font-semibold">Recommandations Prioritaires</h3>
          </div>
          <div className="space-y-3">
            {execSummary.ai_recommendations.map((rec: AIRecommendation, idx: number) => {
              const impact = (rec?.impact ?? 'medium') as 'high' | 'medium' | 'low';
              const priority = rec?.priority ?? idx + 1;
              const action = rec?.action ?? String(rec);
              const category = rec?.category ?? '';
              return (
              <div key={priority} className={`rounded-lg p-4 ${IMPACT_COLORS[impact] || IMPACT_COLORS.medium}`}>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-7 h-7 rounded-full bg-white/60 flex items-center justify-center text-sm font-bold">
                    P{priority}
                  </span>
                  <div className="flex-1">
                    <p className="font-medium">{action}</p>
                    {category && <p className="text-xs mt-1 opacity-70">Catégorie : {category}</p>}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${BADGE_COLORS[impact] || BADGE_COLORS.medium}`}>
                    {impact.toUpperCase()}
                  </span>
                </div>
              </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Criticality Scores */}
      {execSummary.criticality_scores && execSummary.criticality_scores.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            <h3 className="text-lg font-semibold">Criticité par Catégorie</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {[...execSummary.criticality_scores]
              .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
              .map((cs: CriticalityScore) => {
                const badge = (cs?.badge ?? 'medium') as 'high' | 'medium' | 'low';
                return (
                <div key={cs.category} className="rounded-lg border border-gray-200 dark:border-gray-600 p-4 flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm truncate">{cs.category}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${BADGE_COLORS[badge] || BADGE_COLORS.medium}`}>
                      {badge.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          badge === 'high' ? 'bg-red-500' : badge === 'medium' ? 'bg-yellow-400' : 'bg-green-500'
                        }`}
                        style={{ width: `${cs.score ?? 0}%` }}
                      />
                    </div>
                    <span className="text-sm font-bold w-8 text-right">{cs.score ?? 0}</span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{cs.rationale}</p>
                </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Temporal Anomalies */}
      {execSummary.temporal_anomalies && execSummary.temporal_anomalies.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold">Anomalies Temporelles</h3>
            <span className="ml-1 text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full">{execSummary.temporal_anomalies.length} détectée{execSummary.temporal_anomalies.length > 1 ? 's' : ''}</span>
          </div>
          <div className="space-y-3">
            {execSummary.temporal_anomalies.map((a: TemporalAnomaly, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700/40 border border-gray-100 dark:border-gray-600">
                {a.direction === 'spike'
                  ? <ArrowUpRight className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  : <ArrowDownRight className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{a.period}</span>
                    <span className={`text-xs font-bold ${a.direction === 'spike' ? 'text-red-600' : 'text-blue-600'}`}>
                      {a.delta_pct > 0 ? '+' : ''}{a.delta_pct.toFixed(1)}%
                    </span>
                    <span className="text-xs text-gray-500">{a.volume} tickets</span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-0.5">{a.hypothesis}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top lists */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TopList title="Top Causes" items={execSummary.top_causes.map(c => ({ name: c.cause, value: c.volume, percentage: c.pct }))} />
        <TopList title="Top Catégories" items={execSummary.top_categories.map(c => ({ name: c.category, value: c.volume, percentage: c.pct }))} />
      </div>

      {/* Highlights */}
      {execSummary.highlights.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Highlights</h3>
          <ul className="space-y-2">
            {execSummary.highlights.map((h, i) => (
              <li key={i} className="flex items-start gap-2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>{h}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommandations legacy (si pas d'IA) */}
      {!execSummary.ai_narrative && execSummary.recommendations.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-800">
          <h3 className="text-lg font-semibold mb-4 text-blue-900 dark:text-blue-100">Recommandations</h3>
          <ul className="space-y-2">
            {execSummary.recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-blue-800 dark:text-blue-200">
                <span className="font-bold">{i + 1}.</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

const SyntheseTab: React.FC<{ uploadedData: UploadResponse | null }> = ({ uploadedData }) => {
  // Auto-détection de la colonne : priorité à ce qui existe dans les données
  const PARETO_CANDIDATES = ['cause_canonique', 'categorie_intelligente', 'predicted_label', 'application', 'groupe', 'label'];

  // Colonnes à exclure du Pareto (identifiants, URLs, textes libres longs)
  const EXCLUDE_PATTERNS = /^(id|inc_numero|numero|url|link|lien|href|uuid|key|ticket_id|_id|date|created|updated|timestamp)/i;
  const EXCLUDE_EXACT = ['inc_link', 'inc_url', 'inc_id', 'inc_key', 'inc_numero', 'incident_id'];

  const getUsableCols = (cols: string[]) =>
    cols.filter(c => !EXCLUDE_PATTERNS.test(c) && !EXCLUDE_EXACT.includes(c.toLowerCase()));

  const defaultCol = uploadedData
    ? PARETO_CANDIDATES.find(c => uploadedData.columns.includes(c))
      ?? getUsableCols(uploadedData.columns)[0]
      ?? uploadedData.columns[0]
      ?? 'cause_canonique'
    : 'cause_canonique';

  const [paretoColumn, setParetoColumn] = useState<string>(defaultCol);
  const [paretoData, setParetoData] = useState<any>(null);

  // Mettre à jour la colonne sélectionnée si uploadedData change
  useEffect(() => {
    if (uploadedData) {
      const col = PARETO_CANDIDATES.find(c => uploadedData.columns.includes(c))
        ?? getUsableCols(uploadedData.columns)[0]
        ?? uploadedData.columns[0];
      if (col && col !== paretoColumn) setParetoColumn(col);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadedData?.columns?.join(',')]);

  useEffect(() => {
    if (uploadedData && paretoColumn) {
      classificationMLService.getPareto(paretoColumn).then(d => {
        // Si le backend a fait un fallback, mettre à jour le select
        if (d?.column && d.column !== paretoColumn) setParetoColumn(d.column);
        setParetoData(d);
      }).catch(() => setParetoData(null));
    }
  }, [paretoColumn, uploadedData]);

  if (!uploadedData) return <div className="text-center py-12 text-gray-500">Uploadez un fichier CSV d'abord</div>;

  const usableCols = getUsableCols(uploadedData.columns);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <label className="font-medium">Colonne pour Pareto:</label>
        <select
          value={paretoColumn}
          onChange={(e) => setParetoColumn(e.target.value)}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
        >
          {usableCols.length > 0
            ? usableCols.map(col => (
                <option key={col} value={col}>{col}</option>
              ))
            : uploadedData.columns.map(col => (
                <option key={col} value={col}>{col}</option>
              ))
          }
        </select>
        {paretoData?.column && paretoData.column !== paretoColumn && (
          <span className="text-xs text-yellow-600">→ fallback sur « {paretoData.column} »</span>
        )}
      </div>

      {paretoData && <ParetoChart data={paretoData.items} />}
    </div>
  );
};

const AnalyseInteractiveTab: React.FC<{ uploadedData: UploadResponse | null }> = ({ uploadedData }) => {
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchText, setSearchText] = useState('');
  const [sortCol, setSortCol] = useState<string>('');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [timeseriesData, setTimeseriesData] = useState<any>(null);

  useEffect(() => {
    if (uploadedData) {
      classificationMLService.getTimeseries('date', 'cause_canonique').then(setTimeseriesData).catch(() => {});
    }
  }, [uploadedData]);

  if (!uploadedData) return <div className="text-center py-12 text-gray-500">Uploadez un fichier CSV d'abord</div>;

  const rows = uploadedData.preview || [];
  const hasCategorie = uploadedData.columns.includes('categorie_intelligente');

  // Unique categories for filter
  const categories = hasCategorie
    ? Array.from(new Set(rows.map((r: any) => r.categorie_intelligente).filter(Boolean))).sort() as string[]
    : [];

  // Filtered + searched rows
  const filtered = rows.filter((r: any) => {
    const matchCat = categoryFilter === 'all' || r.categorie_intelligente === categoryFilter;
    const matchSearch = !searchText || Object.values(r).some(v =>
      String(v).toLowerCase().includes(searchText.toLowerCase())
    );
    return matchCat && matchSearch;
  });

  // Sort
  const sorted = sortCol
    ? [...filtered].sort((a: any, b: any) => {
        const av = String(a[sortCol] ?? '');
        const bv = String(b[sortCol] ?? '');
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      })
    : filtered;

  const handleSort = (col: string) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
  };

  // Category distribution stats
  const catStats = categories.map(cat => ({
    cat,
    count: rows.filter((r: any) => r.categorie_intelligente === cat).length
  })).sort((a, b) => b.count - a.count);

  // Show key columns: prioritize categorie_intelligente, then a few useful ones
  const priorityCols = ['categorie_intelligente', 'inc_cause', 'cause_canonique', 'resume', 'texte_complet', 'application', 'groupe'];
  const displayCols = [
    ...priorityCols.filter(c => uploadedData.columns.includes(c)),
    ...uploadedData.columns.filter(c => !priorityCols.includes(c))
  ].slice(0, 8);

  return (
    <div className="space-y-6">
      {/* Category distribution cards */}
      {hasCategorie && catStats.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="text-base font-semibold mb-3 flex items-center gap-2">
            <PieChart className="w-4 h-4 text-blue-500" />
            Distribution par Catégorie Intelligente
          </h3>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setCategoryFilter('all')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                categoryFilter === 'all'
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:bg-gray-50'
              }`}
            >
              Tout ({rows.length})
            </button>
            {catStats.map(({ cat, count }) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat === categoryFilter ? 'all' : cat)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  categoryFilter === cat
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:bg-gray-50'
                }`}
              >
                {cat} <span className="ml-1 opacity-75">({count})</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {!hasCategorie && (
        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg text-sm text-yellow-800 dark:text-yellow-200 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          Lancez la prédiction dans l'onglet <strong>Correction Tickets</strong> pour voir les catégories intelligentes.
        </div>
      )}

      {/* Ticket table with filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center gap-3">
          <h3 className="font-semibold text-sm">
            Tickets ({sorted.length}{rows.length !== sorted.length ? ` / ${rows.length}` : ''})
          </h3>
          <input
            type="text"
            placeholder="Rechercher..."
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            className="ml-auto w-56 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 dark:text-white"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                {displayCols.map(col => (
                  <th
                    key={col}
                    onClick={() => handleSort(col)}
                    className={`px-4 py-2.5 text-left font-medium cursor-pointer select-none whitespace-nowrap ${
                      col === 'categorie_intelligente'
                        ? 'text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/20'
                        : 'text-gray-600 dark:text-gray-300'
                    }`}
                  >
                    {col}
                    {sortCol === col && (
                      <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {sorted.length === 0 ? (
                <tr><td colSpan={displayCols.length} className="px-4 py-8 text-center text-gray-400">Aucun résultat</td></tr>
              ) : (
                sorted.map((row: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                    {displayCols.map(col => (
                      <td
                        key={col}
                        className={`px-4 py-2 max-w-xs truncate ${
                          col === 'categorie_intelligente'
                            ? 'font-medium text-blue-700 dark:text-blue-300 bg-blue-50/50 dark:bg-blue-900/10'
                            : 'text-gray-700 dark:text-gray-200'
                        }`}
                        title={String(row[col] ?? '')}
                      >
                        {String(row[col] ?? '—')}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Timeline */}
      {timeseriesData && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-base font-semibold mb-4">Évolution Temporelle</h3>
          <TimelineChart data={timeseriesData.data} />
        </div>
      )}
    </div>
  );
};

const TrainingTab: React.FC<{
  uploadedData: UploadResponse | null;
  trainingResult: TrainResponse | null;
  modelInfo: ModelInfo | null;
  onTrain: (params: any) => void;
  loading: boolean;
}> = ({ uploadedData, trainingResult, modelInfo, onTrain, loading }) => {
  const [labelCol, setLabelCol] = useState('cause');
  const [maxFeatures, setMaxFeatures] = useState(5000);
  const [useCauseHint, setUseCauseHint] = useState(false);
  const [retraining, setRetraining] = React.useState(false);
  const [retrainResult, setRetrainResult] = React.useState<any>(null);
  const [retrainError, setRetrainError] = React.useState<string | null>(null);

  const handleRetrainWithCorrections = async () => {
    setRetraining(true);
    setRetrainResult(null);
    setRetrainError(null);
    try {
      const res = await classificationMLService.retrainWithCorrections();
      setRetrainResult(res);
    } catch (err: any) {
      setRetrainError(err.response?.data?.detail || 'Erreur lors du réentraînement');
    } finally {
      setRetraining(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onTrain({ labelCol, maxFeatures, useCauseHint });
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 space-y-4">
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 mb-4 border border-blue-200 dark:border-blue-800">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            ℹ️ La colonne de texte sera automatiquement détectée (text_ml_postmortem, texte_complet, ou resume).
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Colonne à prédire (label)</label>
            <select
              value={labelCol}
              onChange={(e) => setLabelCol(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
            >
              {uploadedData?.columns.map(col => (
                <option key={col} value={col}>{col}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Max Features</label>
            <input
              type="number"
              value={maxFeatures}
              onChange={(e) => setMaxFeatures(Number(e.target.value))}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
            />
          </div>

          <div className="flex items-center col-span-2">
            <input
              type="checkbox"
              checked={useCauseHint}
              onChange={(e) => setUseCauseHint(e.target.checked)}
              className="mr-2"
            />
            <label className="text-sm font-medium">Utiliser hint cause (pour catégories)</label>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !uploadedData}
          className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <Brain className="w-5 h-5" />
          {loading ? 'Entraînement en cours...' : 'Entraîner le modèle'}
        </button>

        {/* Idée 6 : Réentraîner avec corrections */}
        <button
          type="button"
          onClick={handleRetrainWithCorrections}
          disabled={retraining || !uploadedData}
          className="w-full px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-2"
        >
          {retraining ? <Loader className="w-5 h-5 animate-spin" /> : <RefreshCw className="w-5 h-5" />}
          {retraining ? 'Réentraînement en cours...' : 'Réentraîner avec corrections validées'}
        </button>
        {retrainResult && (
          <div className="mt-3 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 text-sm text-green-800 dark:text-green-200">
            ✅ {retrainResult.message} — F1 : <strong>{retrainResult.macro_f1?.toFixed(3) ?? 'N/A'}</strong>
            {' '}• {retrainResult.total_samples?.toLocaleString()} samples
          </div>
        )}
        {retrainError && (
          <div className="mt-3 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 text-sm text-red-800 dark:text-red-200">
            ⚠️ {retrainError}
          </div>
        )}
      </form>

      {modelInfo && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Informations du Modèle</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard title="Tickets d'entraînement" value={modelInfo.training_count.toString()} icon={Brain} color="blue" />
            <MetricCard title="Classes" value={modelInfo.classes.length.toString()} icon={PieChart} color="purple" />
            <MetricCard title="F1-Score" value={modelInfo.macro_f1 ? modelInfo.macro_f1.toFixed(3) : 'N/A'} icon={TrendingUp} color="green" />
            <MetricCard title="Seuil recommandé" value={modelInfo.recommended_threshold.toFixed(2)} icon={CheckCircle} color="orange" />
          </div>
        </div>
      )}

      {trainingResult && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4">Rapport de Classification</h3>
            <pre className="text-xs overflow-x-auto bg-gray-50 dark:bg-gray-900 p-4 rounded">
              {trainingResult.metrics.classification_report}
            </pre>
          </div>

          {trainingResult.metrics.confusion_matrix && (
            <ConfusionMatrixDisplay
              matrix={trainingResult.metrics.confusion_matrix}
              classes={trainingResult.classes}
            />
          )}

          {trainingResult.weak_points.length > 0 && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-6 border border-yellow-200 dark:border-yellow-800">
              <h3 className="text-lg font-semibold mb-4 text-yellow-900 dark:text-yellow-100">Points Faibles</h3>
              <ul className="space-y-2">
                {trainingResult.weak_points.map((wp, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold">{wp.type}:</span> {wp.detail}
                      <span className={`ml-2 text-xs px-2 py-1 rounded ${
                        wp.severity === 'high' ? 'bg-red-200 text-red-800' : 'bg-yellow-200 text-yellow-800'
                      }`}>
                        {wp.severity}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const CorrectionTab: React.FC<{
  predictions: PredictResponse | null;
  threshold: number;
  onThresholdChange: (value: number) => void;
  onPredict: () => void;
  onCorrection: (ticketId: string, correctedLabel: string, originalLabel: string) => void;
  loading: boolean;
  modelInfo: ModelInfo | null;
  uploadedData: UploadResponse | null;
}> = ({ predictions, threshold, onThresholdChange, onPredict, onCorrection, loading, modelInfo, uploadedData }) => {
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [filterAccepted, setFilterAccepted] = useState<'all' | 'accepted' | 'rejected'>('all');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  // All known classes from modelInfo (preferred) or from predictions
  const allClasses: string[] = modelInfo?.classes?.length
    ? [...modelInfo.classes].sort()
    : predictions
      ? Array.from(new Set(predictions.predictions.map(p => p.predicted_label))).sort()
      : [];

  // Build a lookup: index -> original row data from updated_preview
  const previewByIndex: Record<string, Record<string, any>> = {};
  const preview = predictions?.updated_preview ?? uploadedData?.preview ?? [];
  preview.forEach((row, i) => { previewByIndex[String(i)] = row; });

  // Key columns to display as ticket context (shown in expanded row)
  const CONTEXT_COLS = [
    'inc_resume', 'resume', 'description', 'inc_description',
    'inc_cause', 'cause_canonique', 'inc_solution', 'soution',
    'inc_date_creation', 'date', 'inc_numero', 'id',
    'composant', 'inc_composant', 'application',
  ];

  const displayed = predictions
    ? predictions.predictions.filter(p =>
        filterAccepted === 'all' ? true :
        filterAccepted === 'accepted' ? p.accepted :
        !p.accepted
      )
    : [];

  const allRejected = predictions && predictions.stats.accepted === 0;

  const handleSave = async (p: any) => {
    const corrected = corrections[p.ticket_id];
    if (!corrected) return;
    await onCorrection(p.ticket_id, corrected, p.predicted_label);
    setSaved(s => ({ ...s, [p.ticket_id]: true }));
  };

  // Get a short summary of a ticket row for the table
  const getTicketSummary = (rowData: Record<string, any> | undefined): string => {
    if (!rowData) return '—';
    const resumeKey = ['inc_resume', 'resume', 'description', 'inc_description']
      .find(k => rowData[k] && String(rowData[k]).trim());
    if (!resumeKey) return '—';
    const text = String(rowData[resumeKey]);
    return text.length > 80 ? text.slice(0, 80) + '…' : text;
  };

  const getTicketId = (rowData: Record<string, any> | undefined): string => {
    if (!rowData) return '—';
    const idKey = ['inc_numero', 'id', 'ticket_id', 'numero']
      .find(k => rowData[k] && String(rowData[k]).trim());
    return idKey ? String(rowData[idKey]) : '—';
  };

  const getRealLabel = (rowData: Record<string, any> | undefined): string => {
    if (!rowData) return '—';
    const labelKey = ['inc_cause', 'cause_canonique', 'categorie', 'inc_categorie', 'label']
      .find(k => rowData[k] && String(rowData[k]).trim());
    return labelKey ? String(rowData[labelKey]) : '—';
  };

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 space-y-4">
        <div className="flex items-center gap-4">
          <label className="font-medium text-sm whitespace-nowrap">Seuil de confiance :</label>
          <input
            type="range" min="0.3" max="0.95" step="0.01"
            value={threshold}
            onChange={(e) => onThresholdChange(Number(e.target.value))}
            className="flex-1"
          />
          <span className="font-mono font-bold text-blue-600 w-12 text-right">{threshold.toFixed(2)}</span>
        </div>
        <button
          onClick={onPredict}
          disabled={loading}
          className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2 font-medium"
        >
          <Brain className="w-5 h-5" />
          {loading ? 'Classification en cours...' : 'Classifier tous les tickets'}
        </button>
      </div>

      {!predictions && !loading && (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <Brain className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p>Cliquez sur <strong>Classifier tous les tickets</strong> pour lancer la prédiction.</p>
        </div>
      )}

      {predictions && (
        <>
          {/* Warning: all rejected */}
          {allRejected && (
            <div className="flex items-start gap-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-xl p-4">
              <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-800 dark:text-yellow-200">
                <strong>Tous les tickets sont rejetés</strong> — le modèle prédit avec une confiance inférieure au seuil ({threshold.toFixed(2)}).
                Essayez de <strong>baisser le seuil</strong> (ex : 0.10–0.30) pour voir les prédictions, ou relancez l'entraînement avec plus de données.
              </div>
            </div>
          )}

          {/* Stats row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard title="Total" value={predictions.stats.total.toString()} icon={BarChart3} color="blue" />
            <MetricCard title="Acceptés" value={predictions.stats.accepted.toString()} icon={CheckCircle} color="green" />
            <MetricCard title="Rejetés" value={predictions.stats.rejected.toString()} icon={AlertCircle} color="red" />
            <MetricCard title="Couverture" value={`${(predictions.stats.coverage * 100).toFixed(1)}%`} icon={TrendingUp} color="purple" />
          </div>

          {/* Filter bar */}
          <div className="flex items-center gap-2">
            {(['all', 'accepted', 'rejected'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilterAccepted(f)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  filterAccepted === f
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-500 hover:bg-gray-50'
                }`}
              >
                {f === 'all' ? 'Tous' : f === 'accepted' ? '✓ Acceptés' : '✗ Rejetés'}
              </button>
            ))}
            <span className="ml-auto text-xs text-gray-400">
              Cliquez sur <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">▶</kbd> pour voir le détail du ticket
            </span>
            <span className="text-sm text-gray-500">{displayed.length} tickets</span>
          </div>

          {/* Prediction table */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700/50 sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-3 w-8"></th>
                    <th className="px-3 py-3 text-left font-medium text-gray-600 dark:text-gray-300 w-24">N° Ticket</th>
                    <th className="px-3 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Résumé</th>
                    <th className="px-3 py-3 text-left font-medium text-gray-600 dark:text-gray-300 w-48">Catégorie réelle</th>
                    <th className="px-3 py-3 text-left font-medium text-gray-600 dark:text-gray-300 w-52">Prédiction ML</th>
                    <th className="px-3 py-3 text-left font-medium text-gray-600 dark:text-gray-300 w-24">Confiance</th>
                    <th className="px-3 py-3 text-left font-medium text-gray-600 dark:text-gray-300 w-20">Statut</th>
                    <th className="px-3 py-3 text-left font-medium text-gray-600 dark:text-gray-300 w-52">Correction</th>
                    <th className="px-3 py-3 w-16"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {displayed.map((p, i) => {
                    const rowData = previewByIndex[p.ticket_id];
                    const isExpanded = expandedRow === p.ticket_id;
                    const ticketNum = getTicketId(rowData);
                    const summary = getTicketSummary(rowData);
                    const realLabel = getRealLabel(rowData);
                    const predMatchesReal = realLabel !== '—' && realLabel.trim().toLowerCase() === p.predicted_label.trim().toLowerCase();

                    // Context fields for expanded view
                    const contextFields = CONTEXT_COLS
                      .filter(k => rowData?.[k] && String(rowData[k]).trim() && String(rowData[k]) !== 'nan')
                      .map(k => ({ key: k, value: String(rowData[k]) }));

                    return (
                      <>
                        <tr
                          key={p.ticket_id}
                          className={`transition-colors cursor-pointer ${
                            saved[p.ticket_id] ? 'bg-green-50 dark:bg-green-900/10' :
                            isExpanded ? 'bg-blue-50 dark:bg-blue-900/10' :
                            !p.accepted ? 'bg-red-50/40 dark:bg-red-900/5' : 'hover:bg-gray-50 dark:hover:bg-gray-700/30'
                          }`}
                          onClick={() => setExpandedRow(isExpanded ? null : p.ticket_id)}
                        >
                          <td className="px-3 py-2.5 text-gray-400 text-center">
                            <span className="text-xs">{isExpanded ? '▼' : '▶'}</span>
                          </td>
                          <td className="px-3 py-2.5 text-gray-500 font-mono text-xs">{ticketNum}</td>
                          <td className="px-3 py-2.5 text-gray-700 dark:text-gray-200 max-w-xs">
                            <span className="line-clamp-2 text-xs">{summary}</span>
                          </td>
                          <td className="px-3 py-2.5">
                            <span className="text-xs text-gray-600 dark:text-gray-300">{realLabel}</span>
                          </td>
                          <td className="px-3 py-2.5">
                            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                              predMatchesReal
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                                : 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                            }`}>{p.predicted_label}</span>
                          </td>
                          <td className="px-3 py-2.5">
                            <div className="flex items-center gap-1.5">
                              <div className="w-12 bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                                <div
                                  className={`h-1.5 rounded-full ${
                                    p.confidence >= 0.6 ? 'bg-green-500' :
                                    p.confidence >= 0.35 ? 'bg-yellow-500' : 'bg-red-500'
                                  }`}
                                  style={{ width: `${Math.min(p.confidence * 100, 100)}%` }}
                                />
                              </div>
                              <span className="text-xs font-mono text-gray-500">{(p.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </td>
                          <td className="px-3 py-2.5" onClick={e => e.stopPropagation()}>
                            <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium ${
                              p.accepted
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                                : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                            }`}>
                              {p.accepted ? '✓' : '✗'}
                            </span>
                          </td>
                          <td className="px-3 py-2.5" onClick={e => e.stopPropagation()}>
                            {saved[p.ticket_id] ? (
                              <span className="text-xs text-green-600 dark:text-green-400 font-medium">✓ Sauvegardé</span>
                            ) : (
                              <select
                                value={corrections[p.ticket_id] || ''}
                                onChange={e => setCorrections(c => ({ ...c, [p.ticket_id]: e.target.value }))}
                                className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 dark:text-white w-full max-w-[200px]"
                              >
                                <option value="">— corriger —</option>
                                {allClasses.map(cls => (
                                  <option key={cls} value={cls}>{cls}</option>
                                ))}
                              </select>
                            )}
                          </td>
                          <td className="px-3 py-2.5" onClick={e => e.stopPropagation()}>
                            {!saved[p.ticket_id] && corrections[p.ticket_id] && (
                              <button
                                onClick={() => handleSave(p)}
                                className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                              >
                                Sauver
                              </button>
                            )}
                          </td>
                        </tr>
                        {/* Expanded ticket detail row */}
                        {isExpanded && (
                          <tr key={`${p.ticket_id}-detail`} className="bg-blue-50 dark:bg-blue-900/10">
                            <td colSpan={9} className="px-6 py-4">
                              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                {contextFields.length > 0 ? contextFields.map(({ key, value }) => (
                                  <div key={key} className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-blue-100 dark:border-blue-800">
                                    <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">{key}</p>
                                    <p className="text-sm text-gray-800 dark:text-gray-100 break-words">{value}</p>
                                  </div>
                                )) : (
                                  <p className="text-sm text-gray-500 col-span-3">Aucun détail disponible pour ce ticket.</p>
                                )}
                                {/* Top-3 probabilities if available */}
                                {p.all_probabilities && (
                                  <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-blue-100 dark:border-blue-800 col-span-full">
                                    <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Top probabilités ML</p>
                                    <div className="flex flex-wrap gap-2">
                                      {Object.entries(p.all_probabilities)
                                        .sort(([,a],[,b]) => b - a)
                                        .slice(0, 5)
                                        .map(([cls, prob]) => (
                                          <span key={cls} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-full text-xs">
                                            <span className="font-medium text-blue-800 dark:text-blue-200">{cls}</span>
                                            <span className="text-blue-600 dark:text-blue-400">{(prob * 100).toFixed(1)}%</span>
                                          </span>
                                        ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const ConfigTab: React.FC = () => {
  return (
    <div className="space-y-6">
      <KeywordsConfigEditor />
    </div>
  );
};

const ExportTab: React.FC<{ onExport: () => void; execSummary: ExecSummary | null }> = ({ onExport, execSummary }) => {
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold mb-4">Export PDF</h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Générez un rapport PDF avec l'analyse complète et les recommandations.
        </p>

        <button
          onClick={onExport}
          disabled={!execSummary}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          <FileDown className="w-5 h-5" />
          Télécharger le rapport PDF
        </button>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// MonitoringTab — Observabilité ML production-grade
// ─────────────────────────────────────────────────────────────────────────────

const MonitoringTab: React.FC<{ sessionId: string | null }> = ({ sessionId }) => {
  const [health, setHealth] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [drift, setDrift] = useState<any>(null);
  const [versions, setVersions] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rollbackLoading, setRollbackLoading] = useState<string | null>(null);
  const [retrainLoading, setRetrainLoading] = useState(false);
  const [retrainMsg, setRetrainMsg] = useState<string | null>(null);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, s, v] = await Promise.all([
        classificationMLService.getHealth(),
        classificationMLService.getStats(),
        classificationMLService.getModelVersions(),
      ]);
      setHealth(h);
      setStats(s);
      setVersions(v);

      // Drift seulement si modèle entraîné et données chargées
      if (h.model.exists && h.data.loaded) {
        try {
          const d = await classificationMLService.getDriftDetection();
          setDrift(d);
        } catch {
          // silencieux si pas de données
        }
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erreur chargement monitoring');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  const handleRollback = async (versionDir: string) => {
    if (!confirm(`Rollback vers ${versionDir} ?`)) return;
    setRollbackLoading(versionDir);
    try {
      const res = await classificationMLService.rollbackToVersion(versionDir);
      alert(res.message);
      await loadAll();
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Rollback échoué');
    } finally {
      setRollbackLoading(null);
    }
  };

  const handleRetrain = async () => {
    setRetrainLoading(true);
    setRetrainMsg(null);
    try {
      const res = await classificationMLService.retrainWithCorrections();
      setRetrainMsg(`✅ ${res.message} — F1: ${res.macro_f1?.toFixed(3) ?? 'N/A'}`);
      await loadAll();
    } catch (e: any) {
      setRetrainMsg(`❌ ${e?.response?.data?.detail || 'Réentraînement échoué'}`);
    } finally {
      setRetrainLoading(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const blob = await classificationMLService.exportCSV(sessionId || undefined);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tickets_ml_${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Export échoué');
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader className="w-8 h-8 animate-spin text-blue-500" />
      <span className="ml-3 text-gray-500">Chargement monitoring...</span>
    </div>
  );

  if (error) return (
    <div className="p-6 bg-red-50 dark:bg-red-900/20 rounded-lg flex items-center gap-3">
      <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
      <span className="text-red-700 dark:text-red-300">{error}</span>
      <button onClick={loadAll} className="ml-auto text-sm text-blue-600 hover:underline">Réessayer</button>
    </div>
  );

  const statusColor = health?.status === 'healthy' ? 'green' : 'yellow';
  const driftColor = drift?.alert_level === 'ok' ? 'green' : drift?.alert_level === 'warning' ? 'yellow' : 'red';

  return (
    <div className="space-y-6">
      {/* Header + actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-blue-600" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Monitoring ML</h2>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExportCSV} className="flex items-center gap-1 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600">
            <Download className="w-4 h-4" /> Export CSV
          </button>
          <button onClick={loadAll} className="flex items-center gap-1 px-3 py-2 text-sm bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-100">
            <RefreshCw className="w-4 h-4" /> Actualiser
          </button>
        </div>
      </div>

      {/* Row 1 — Health + Model + Corrections */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Santé globale */}
        <div className={`p-4 rounded-xl border-2 ${statusColor === 'green' ? 'border-green-300 bg-green-50 dark:bg-green-900/20' : 'border-yellow-300 bg-yellow-50 dark:bg-yellow-900/20'}`}>
          <div className="flex items-center gap-2 mb-2">
            <Shield className={`w-5 h-5 ${statusColor === 'green' ? 'text-green-600' : 'text-yellow-600'}`} />
            <span className="font-semibold text-gray-800 dark:text-gray-200">Statut Global</span>
          </div>
          <div className={`text-2xl font-bold ${statusColor === 'green' ? 'text-green-700' : 'text-yellow-700'}`}>
            {health?.status === 'healthy' ? '✅ Healthy' : '⚠️ Dégradé'}
          </div>
          {health?.issues?.length > 0 && (
            <ul className="mt-2 space-y-1">
              {health.issues.map((issue: string, i: number) => (
                <li key={i} className="text-xs text-yellow-700 dark:text-yellow-300 flex items-start gap-1">
                  <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />{issue}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Modèle actuel */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="w-5 h-5 text-purple-600" />
            <span className="font-semibold text-gray-800 dark:text-gray-200">Modèle Actuel</span>
          </div>
          {health?.model?.exists ? (
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Macro F1</span>
                <span className="font-semibold text-blue-600">
                  {health.model.macro_f1 != null ? health.model.macro_f1.toFixed(3) : '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Classes</span>
                <span className="font-medium">{health.model.classes_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Version</span>
                <span className="font-medium">v{health.model.training_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Seuil</span>
                <span className="font-medium">{(health.model.recommended_threshold * 100).toFixed(0)}%</span>
              </div>
              {health.model.trained_at && (
                <div className="text-xs text-gray-400 mt-1">
                  {new Date(health.model.trained_at).toLocaleString('fr-FR')}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">Aucun modèle entraîné</p>
          )}
        </div>

        {/* Corrections */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center gap-2 mb-2">
            <FileCheck className="w-5 h-5 text-orange-600" />
            <span className="font-semibold text-gray-800 dark:text-gray-200">Corrections</span>
          </div>
          <div className="text-3xl font-bold text-orange-600 mb-1">
            {stats?.corrections?.total ?? 0}
          </div>
          <div className="text-xs text-gray-500 mb-3">
            Seuil réentraînement : {stats?.corrections?.auto_retrain_threshold ?? 20}
          </div>
          {stats?.corrections?.retrain_eligible && (
            <div className="mb-2 px-2 py-1 bg-orange-100 dark:bg-orange-900/30 rounded text-xs text-orange-700 dark:text-orange-300">
              ⚡ Réentraînement éligible
            </div>
          )}
          <button
            onClick={handleRetrain}
            disabled={retrainLoading || !stats?.corrections?.total}
            className="w-full mt-1 py-1.5 text-xs bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 flex items-center justify-center gap-1"
          >
            {retrainLoading ? <Loader className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            Réentraîner avec corrections
          </button>
          {retrainMsg && (
            <p className="text-xs mt-1 text-gray-600 dark:text-gray-400">{retrainMsg}</p>
          )}
        </div>
      </div>

      {/* Row 2 — Drift + Coverage */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Drift */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-5 h-5 text-blue-600" />
            <span className="font-semibold text-gray-800 dark:text-gray-200">Drift Distribution</span>
            {drift && (
              <span className={`ml-auto text-xs font-bold px-2 py-0.5 rounded-full
                ${driftColor === 'green' ? 'bg-green-100 text-green-700' :
                  driftColor === 'yellow' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'}`}>
                {drift.alert_level.toUpperCase()}
              </span>
            )}
          </div>
          {drift ? (
            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <div>
                  <div className="text-xs text-gray-500">Divergence KL</div>
                  <div className="text-2xl font-bold">{drift.kl_divergence.toFixed(4)}</div>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 flex-1">
                  {drift.alert_message}
                </div>
              </div>
              {drift.drifted_labels?.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Labels dérivés (top {Math.min(5, drift.drifted_labels.length)})</div>
                  <div className="space-y-1">
                    {drift.drifted_labels.slice(0, 5).map((l: any) => (
                      <div key={l.label} className="flex items-center gap-2 text-xs">
                        <span className="truncate flex-1 text-gray-700 dark:text-gray-300">{l.label}</span>
                        <span className={`${l.delta_pct > 0 ? 'text-red-600' : 'text-blue-600'} font-semibold`}>
                          {l.delta_pct > 0 ? '▲' : '▼'} {Math.abs(l.delta_pct).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {drift.training_date && (
                <div className="text-xs text-gray-400">Référence entraînement : {new Date(drift.training_date).toLocaleDateString('fr-FR')}</div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">
              {!health?.model?.exists ? 'Entraîner un modèle pour surveiller le drift' :
               !health?.data?.loaded ? 'Importer des données pour surveiller le drift' :
               'Calcul drift non disponible'}
            </p>
          )}
        </div>

        {/* Coverage + Distribution */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-5 h-5 text-indigo-600" />
            <span className="font-semibold text-gray-800 dark:text-gray-200">Coverage & Distribution</span>
          </div>
          {stats?.predictions?.coverage_pct != null ? (
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-500">Coverage prédictions</span>
                  <span className="font-semibold text-blue-600">{stats.predictions.coverage_pct}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${stats.predictions.coverage_pct >= 65 ? 'bg-green-500' : stats.predictions.coverage_pct >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.min(stats.predictions.coverage_pct, 100)}%` }}
                  />
                </div>
                <div className="text-xs text-gray-400 mt-0.5">Cible ≥ 65%</div>
              </div>
              {Object.keys(stats.predictions.current_distribution).length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Distribution actuelle (top 5)</div>
                  <div className="space-y-1">
                    {Object.entries(stats.predictions.current_distribution as Record<string,number>)
                      .sort(([,a],[,b]) => b - a).slice(0, 5)
                      .map(([label, pct]) => (
                      <div key={label} className="flex items-center gap-2 text-xs">
                        <span className="truncate flex-1 text-gray-700 dark:text-gray-300">{label}</span>
                        <div className="flex items-center gap-1">
                          <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded h-1.5">
                            <div className="bg-indigo-500 h-1.5 rounded" style={{ width: `${Math.min(pct, 100)}%` }} />
                          </div>
                          <span className="text-gray-500 w-8 text-right">{pct}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">
              Classifier les tickets pour voir la coverage
            </p>
          )}
        </div>
      </div>

      {/* Row 3 — Preprocessing + Versions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Preprocessing */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-5 h-5 text-yellow-600" />
            <span className="font-semibold text-gray-800 dark:text-gray-200">Preprocessing Télécom</span>
            <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-bold
              ${health?.preprocessing?.available ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              {health?.preprocessing?.available ? '✓ Actif' : '✗ Inactif'}
            </span>
          </div>
          {health?.preprocessing?.sample_output && (
            <div className="space-y-2">
              <div className="text-xs text-gray-500 font-medium">Exemple de normalisation :</div>
              <div className="text-xs bg-gray-50 dark:bg-gray-900 rounded p-2 font-mono">
                <span className="text-gray-400">→ </span>
                <span className="text-green-600 dark:text-green-400">{health.preprocessing.sample_output}</span>
              </div>
              <div className="text-xs text-gray-400">
                Entrée : "DSLAM OP49MAB11 bloqué erreur 1300"
              </div>
            </div>
          )}
          <div className="mt-3 space-y-1 text-xs text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-1"><CheckCircle className="w-3 h-3 text-green-500" /> Normalisation équipements (EQUIPMENT_ID)</div>
            <div className="flex items-center gap-1"><CheckCircle className="w-3 h-3 text-green-500" /> Normalisation codes erreur (ERROR_CODE_XXXX)</div>
            <div className="flex items-center gap-1"><CheckCircle className="w-3 h-3 text-green-500" /> Synonymes télécom FR</div>
            <div className="flex items-center gap-1"><CheckCircle className="w-3 h-3 text-green-500" /> Stopwords FR métier</div>
          </div>
        </div>

        {/* Versions modèle */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center gap-2 mb-3">
            <History className="w-5 h-5 text-gray-600" />
            <span className="font-semibold text-gray-800 dark:text-gray-200">Historique Modèles</span>
            <span className="ml-auto text-xs text-gray-500">{versions?.count ?? 0} version(s)</span>
          </div>
          {versions?.versions?.length > 0 ? (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {versions.versions.map((v: any, i: number) => (
                <div key={v.version_dir} className={`flex items-center gap-2 p-2 rounded-lg text-xs
                  ${i === 0 ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700' : 'bg-gray-50 dark:bg-gray-700/50'}`}>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-800 dark:text-gray-200 flex items-center gap-1">
                      {i === 0 && <span className="text-blue-600">●</span>}
                      v{v.training_count ?? '?'}
                      {v.macro_f1 != null && <span className="text-blue-600 ml-1">F1:{v.macro_f1.toFixed(3)}</span>}
                    </div>
                    <div className="text-gray-400 truncate">
                      {v.trained_at ? new Date(v.trained_at).toLocaleString('fr-FR') : v.created_at.slice(0, 16).replace('T', ' ')}
                    </div>
                    <div className="text-gray-400">
                      {v.n_samples ? `${v.n_samples} tickets` : ''}{v.classes_count ? ` · ${v.classes_count} classes` : ''}
                      {v.preprocessing ? ' · 🔧 prep' : ''}
                    </div>
                  </div>
                  {i > 0 && (
                    <button
                      onClick={() => handleRollback(v.version_dir)}
                      disabled={rollbackLoading === v.version_dir}
                      className="shrink-0 p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
                      title="Rollback vers cette version"
                    >
                      {rollbackLoading === v.version_dir
                        ? <Loader className="w-3 h-3 animate-spin" />
                        : <RotateCcw className="w-3 h-3 text-gray-500" />}
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">Aucune version sauvegardée. Entraîner un modèle pour créer la première version.</p>
          )}
        </div>
      </div>

      {/* Corrections by label */}
      {stats?.corrections?.total > 0 && Object.keys(stats.corrections.by_label).length > 0 && (
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center gap-2 mb-3">
            <FileCheck className="w-5 h-5 text-orange-600" />
            <span className="font-semibold text-gray-800 dark:text-gray-200">Corrections par Label</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(stats.corrections.by_label as Record<string,number>)
              .sort(([,a],[,b]) => b - a).slice(0, 8)
              .map(([label, count]) => (
              <div key={label} className="p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg text-xs">
                <div className="font-semibold text-orange-700 dark:text-orange-300 text-lg">{count}</div>
                <div className="text-gray-600 dark:text-gray-400 truncate" title={label}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
