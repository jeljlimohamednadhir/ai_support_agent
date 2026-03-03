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
  Loader
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { classificationMLService, type UploadResponse, type TrainResponse, type ModelInfo, type PredictResponse, type ExecSummary } from '../services/classificationMLService';
import { MetricCard } from '../components/ml/MetricCard';
import { ParetoChart } from '../components/ml/ParetoChart';
import { TimelineChart } from '../components/ml/TimelineChart';
import { ConfusionMatrixDisplay } from '../components/ml/ConfusionMatrixDisplay';
import { DataTable } from '../components/ml/DataTable';
import { KeywordsConfigEditor } from '../components/ml/KeywordsConfigEditor';
import { LowConfidenceTable } from '../components/ml/LowConfidenceTable';
import { TopList } from '../components/ml/TopList';

type Tab = 'resume' | 'synthese' | 'analyse' | 'training' | 'correction' | 'config' | 'export';

export const ClassificationMLPage: React.FC = () => {
  const { canCorrectML } = useAuth(); // Get permission to correct ML
  const [activeTab, setActiveTab] = useState<Tab>('resume');
  const [uploadedData, setUploadedData] = useState<UploadResponse | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null); // Persister session
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [predictions, setPredictions] = useState<PredictResponse | null>(null);
  const [execSummary, setExecSummary] = useState<ExecSummary | null>(null);
  const [trainingResult, setTrainingResult] = useState<TrainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState<number>(0.5);
  const [indexingStatus, setIndexingStatus] = useState<'idle' | 'indexing' | 'done'>('idle');

  // Load model info on mount
  useEffect(() => {
    loadModelInfo();
    // Restaurer session depuis localStorage
    const savedSessionId = localStorage.getItem('ml_session_id');
    if (savedSessionId) {
      setSessionId(savedSessionId);
    }
  }, []);

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
      
      // Sauvegarder session_id dans localStorage
      if (response.session_id) {
        setSessionId(response.session_id);
        localStorage.setItem('ml_session_id', response.session_id);
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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
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
    if (!uploadedData || !modelInfo?.exists) {
      setError('Upload data and train model first');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Prepare tickets for prediction
      const tickets = uploadedData.preview.map(row => ({
        ticket_id: row.ticket_id || String(row.id || Math.random()),
        text: row.texte_complet || row.resume || ''
      }));

      const result = await classificationMLService.predict({ tickets, threshold });
      setPredictions(result);
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
        rca_text: JSON.stringify(execSummary),
        recommendations: execSummary.recommendations
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

      {/* Tab Content */}
      <div className="min-h-[600px]">
        {activeTab === 'resume' && (
          <ResumeExecutifTab execSummary={execSummary} loading={loading} />
        )}

        {activeTab === 'synthese' && (
          <SyntheseTab uploadedData={uploadedData} />
        )}

        {activeTab === 'analyse' && (
          <AnalyseInteractiveTab uploadedData={uploadedData} />
        )}

        {activeTab === 'training' && (
          <TrainingTab
            uploadedData={uploadedData}
            trainingResult={trainingResult}
            modelInfo={modelInfo}
            onTrain={handleTrainModel}
            loading={loading}
          />
        )}

        {activeTab === 'correction' && (
          <CorrectionTab
            predictions={predictions}
            threshold={threshold}
            onThresholdChange={setThreshold}
            onPredict={handlePredict}
            onCorrection={handleCorrection}
            loading={loading}
          />
        )}

        {activeTab === 'config' && (
          <ConfigTab />
        )}

        {activeTab === 'export' && (
          <ExportTab onExport={handleExportPDF} execSummary={execSummary} />
        )}
      </div>
    </div>
  );
};

// Tab Components

const ResumeExecutifTab: React.FC<{ execSummary: ExecSummary | null; loading: boolean }> = ({ execSummary, loading }) => {
  if (loading) return <div className="text-center py-12">Chargement...</div>;
  if (!execSummary) return <div className="text-center py-12 text-gray-500">Aucune donnée disponible</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Volume Total"
          value={execSummary.volume.toLocaleString()}
          icon={BarChart3}
          color="blue"
        />
        <MetricCard
          title="MTTR Médian"
          value={execSummary.mttr_med ? `${execSummary.mttr_med.toFixed(1)}j` : 'N/A'}
          icon={Clock}
          color="green"
        />
        <MetricCard
          title="Catégories"
          value={execSummary.top_categories.length.toString()}
          icon={PieChart}
          color="purple"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TopList
          title="Top Causes"
          items={execSummary.top_causes.map(c => ({ name: c.cause, value: c.volume, percentage: c.pct }))}
        />
        <TopList
          title="Top Catégories"
          items={execSummary.top_categories.map(c => ({ name: c.category, value: c.volume, percentage: c.pct }))}
        />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
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

      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
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
    </div>
  );
};

const SyntheseTab: React.FC<{ uploadedData: UploadResponse | null }> = ({ uploadedData }) => {
  const [paretoColumn, setParetoColumn] = useState<string>('cause_canonique');
  const [paretoData, setParetoData] = useState<any>(null);

  useEffect(() => {
    if (uploadedData && paretoColumn) {
      classificationMLService.getPareto(paretoColumn).then(setParetoData);
    }
  }, [paretoColumn, uploadedData]);

  if (!uploadedData) return <div className="text-center py-12 text-gray-500">Uploadez un fichier CSV d'abord</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <label className="font-medium">Colonne pour Pareto:</label>
        <select
          value={paretoColumn}
          onChange={(e) => setParetoColumn(e.target.value)}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
        >
          <option value="cause_canonique">Cause</option>
          <option value="categorie_intelligente">Catégorie</option>
          <option value="application">Application</option>
          <option value="groupe">Groupe</option>
        </select>
      </div>

      {paretoData && <ParetoChart data={paretoData.items} />}
    </div>
  );
};

const AnalyseInteractiveTab: React.FC<{ uploadedData: UploadResponse | null }> = ({ uploadedData }) => {
  const [timeseriesData, setTimeseriesData] = useState<any>(null);
  const [topValues, setTopValues] = useState<any>(null);

  useEffect(() => {
    if (uploadedData) {
      classificationMLService.getTimeseries('date', 'cause_canonique').then(setTimeseriesData);
      classificationMLService.getTopValues('cause_canonique', 10).then(setTopValues);
    }
  }, [uploadedData]);

  if (!uploadedData) return <div className="text-center py-12 text-gray-500">Uploadez un fichier CSV d'abord</div>;

  return (
    <div className="space-y-6">
      {timeseriesData && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Évolution Temporelle</h3>
          <TimelineChart data={timeseriesData.data} />
        </div>
      )}

      {topValues && (
        <TopList
          title="Top 10 Causes"
          items={topValues.items.map((v: any) => ({ name: v.name, value: v.volume }))}
        />
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
}> = ({ predictions, threshold, onThresholdChange, onPredict, onCorrection, loading }) => {
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 space-y-4">
        <div className="flex items-center gap-4">
          <label className="font-medium">Seuil de confiance:</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={threshold}
            onChange={(e) => onThresholdChange(Number(e.target.value))}
            className="flex-1"
          />
          <span className="font-mono font-bold">{threshold.toFixed(2)}</span>
        </div>

        <button
          onClick={onPredict}
          disabled={loading}
          className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Brain className="w-5 h-5" />
          {loading ? 'Prédiction en cours...' : 'Lancer la prédiction'}
        </button>
      </div>

      {predictions && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard title="Total" value={predictions.stats.total.toString()} icon={BarChart3} color="blue" />
            <MetricCard title="Acceptés" value={predictions.stats.accepted.toString()} icon={CheckCircle} color="green" />
            <MetricCard title="Rejetés" value={predictions.stats.rejected.toString()} icon={AlertCircle} color="red" />
            <MetricCard title="Couverture" value={`${(predictions.stats.coverage * 100).toFixed(1)}%`} icon={TrendingUp} color="purple" />
          </div>

          <LowConfidenceTable
            predictions={predictions.predictions.filter(p => !p.accepted)}
            onCorrection={onCorrection}
          />
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
