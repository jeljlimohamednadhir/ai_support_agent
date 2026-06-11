/**
 * ValidationQueue — AI Training Interface Queue
 *
 * Dual-mode component:
 *   1. AI Correction Queue  — LOW/MEDIUM weak-pattern items, sorted by priority
 *   2. Chatbot Task Queue   — classic N3 validation workflow (approve/reject/escalate/correct)
 *
 * Features:
 *   • Priority sort: LOW first, MEDIUM second, HIGH hidden by default (toggle)
 *   • Quick Correction Mode: hides context block, only cause/tags visible
 *   • Role guard: only admin / n3 role
 *   • Filter bar: ALL / LOW / MEDIUM / HIGH
 */
import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle,
  XCircle,
  Edit3,
  ArrowUpCircle,
  ChevronDown,
  ChevronUp,
  Zap,
  ZapOff,
  Eye,
  EyeOff,
  RefreshCw,
  AlertCircle,
} from 'lucide-react'
import api from '@/services/api'
import { useCorrectionStore, type TierFilter } from '@/stores/correctionStore'
import CorrectionCard from './CorrectionCard'

// ─────────────────────────────────────────────────────────────────────────────
// Auth helpers
// ─────────────────────────────────────────────────────────────────────────────

const getUser = () => {
  try {
    const raw = localStorage.getItem('user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const getValidatorId = (): string => {
  const u = getUser()
  return u?.username || u?.login || 'n3_engineer'
}

const hasTrainingAccess = (): boolean => {
  const u = getUser()
  if (!u) return false
  const role = (u.role ?? '').toLowerCase()
  return role === 'admin' || role === 'n3' || role === 'n3_engineer'
}

// ─────────────────────────────────────────────────────────────────────────────
// Classic chatbot task types
// ─────────────────────────────────────────────────────────────────────────────

interface ChatbotTask {
  task_id: number
  status: string
  priority: number
  priority_label: 'low' | 'medium' | 'high'
  created_at: string
  user_question: string
  bot_response: string
  trust_score: number
  incident_type: string
  application: string
}

interface CorrectModalState {
  open: boolean
  task: ChatbotTask | null
  correctedResponse: string
  correctionReason: string
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components (classic task queue)
// ─────────────────────────────────────────────────────────────────────────────

const PriorityBadge = ({ label }: { label: string }) => {
  const cls =
    label === 'high'   ? 'bg-red-100 text-red-700 border-red-300' :
    label === 'medium' ? 'bg-yellow-100 text-yellow-700 border-yellow-300' :
                         'bg-green-100 text-green-700 border-green-300'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${cls}`}>
      {label.toUpperCase()}
    </span>
  )
}

const TrustBar = ({ score }: { score: number }) => {
  const pct = Math.round(score * 100)
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 font-mono">{pct}%</span>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab type
// ─────────────────────────────────────────────────────────────────────────────

type Tab = 'training' | 'classic'

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

export default function ValidationQueue() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<Tab>('training')
  const [expanded, setExpanded] = useState<number | null>(null)
  const [correctModal, setCorrectModal] = useState<CorrectModalState>({
    open: false, task: null, correctedResponse: '', correctionReason: '',
  })

  // ── Correction store ──────────────────────────────────────────────────────
  const {
    items,
    quickMode,
    filter,
    showHigh,
    loadStatus,
    loadItems,
    toggleQuickMode,
    setFilter,
    setShowHigh,
  } = useCorrectionStore()

  useEffect(() => {
    if (activeTab === 'training' && loadStatus === 'idle') {
      loadItems()
    }
  }, [activeTab, loadStatus, loadItems])

  // ── Classic tasks query ───────────────────────────────────────────────────
  const { data, isLoading: tasksLoading } = useQuery({
    queryKey: ['chatbotTasks'],
    queryFn: async () => {
      const res = await api.get('/validation/chatbot-tasks', { params: { limit: 50 } })
      return res.data
    },
    refetchInterval: 10000,
    enabled: activeTab === 'classic',
  })

  const tasks: ChatbotTask[] = data?.tasks ?? []

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['chatbotTasks'] })
    queryClient.invalidateQueries({ queryKey: ['chatbotStats'] })
  }

  const approveMutation = useMutation({
    mutationFn: (id: number) =>
      api.post(`/validation/chatbot-tasks/${id}/approve`, {
        validator_id: getValidatorId(),
        comment: 'Approuvé via dashboard N3',
      }),
    onSuccess: invalidate,
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      api.post(`/validation/chatbot-tasks/${id}/reject`, {
        validator_id: getValidatorId(),
        reason,
      }),
    onSuccess: invalidate,
  })

  const escalateMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) =>
      api.post(`/validation/chatbot-tasks/${id}/escalate`, {
        escalated_by: getValidatorId(),
        escalation_note: note,
      }),
    onSuccess: invalidate,
  })

  const correctMutation = useMutation({
    mutationFn: (payload: { id: number; correctedResponse: string; correctionReason: string }) =>
      api.post(`/validation/chatbot-tasks/${payload.id}/correct`, {
        validator_id:       getValidatorId(),
        corrected_response: payload.correctedResponse,
        correction_reason:  payload.correctionReason,
      }),
    onSuccess: () => {
      invalidate()
      setCorrectModal({ open: false, task: null, correctedResponse: '', correctionReason: '' })
    },
  })

  // ─────────────────────────────────────────────────────────────────────────
  // Filtered + displayed items for training tab
  // ─────────────────────────────────────────────────────────────────────────

  const visibleItems = items.filter((item) => {
    if (item._localAction === 'confirmed' || item._localAction === 'suppressed') return false
    if (!showHigh && item.validation_tier === 'HIGH') return false
    if (filter !== 'ALL' && item.validation_tier !== filter) return false
    return true
  })

  const pendingCount = items.filter(
    (i) => !i._localAction && i.validation_tier !== 'HIGH'
  ).length

  // ─────────────────────────────────────────────────────────────────────────
  // Render: Training tab
  // ─────────────────────────────────────────────────────────────────────────

  const renderTrainingTab = () => {
    if (!hasTrainingAccess()) {
      return (
        <div className="p-10 text-center space-y-2">
          <AlertCircle size={32} className="mx-auto text-yellow-500" />
          <p className="text-gray-500 font-medium">Accès réservé aux rôles N3 / Admin</p>
          <p className="text-sm text-gray-400">Connectez-vous avec un compte autorisé pour accéder à l'interface d'entraînement IA.</p>
        </div>
      )
    }

    if (loadStatus === 'loading') {
      return (
        <div className="p-5 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse h-24 bg-gray-100 rounded-xl" />
          ))}
        </div>
      )
    }

    if (loadStatus === 'error') {
      return (
        <div className="p-8 text-center space-y-2">
          <AlertCircle size={28} className="mx-auto text-red-400" />
          <p className="text-gray-500">Erreur de chargement des patterns faibles</p>
          <button
            onClick={loadItems}
            className="text-xs text-indigo-600 underline hover:text-indigo-800"
          >
            Réessayer
          </button>
        </div>
      )
    }

    if (visibleItems.length === 0) {
      return (
        <div className="p-10 text-center text-gray-400">
          <CheckCircle size={32} className="mx-auto mb-2 text-green-400" />
          <p>Aucun pattern à réviser ✓</p>
          {items.some((i) => i.validation_tier === 'HIGH' && !i._localAction) && !showHigh && (
            <button
              onClick={() => setShowHigh(true)}
              className="mt-2 text-xs text-indigo-600 underline hover:text-indigo-800"
            >
              Afficher les réponses HIGH ({items.filter((i) => i.validation_tier === 'HIGH' && !i._localAction).length})
            </button>
          )}
        </div>
      )
    }

    return (
      <div className="divide-y divide-gray-100 dark:divide-gray-700">
        {visibleItems.map((item) => (
          <div key={item.id} className="py-3 px-3">
            <CorrectionCard item={item} quickMode={quickMode} />
          </div>
        ))}
      </div>
    )
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Render: Classic validation tab
  // ─────────────────────────────────────────────────────────────────────────

  const renderClassicTab = () => {
    if (tasksLoading) {
      return (
        <div className="p-5 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse h-16 bg-gray-100 rounded-lg" />
          ))}
        </div>
      )
    }

    if (tasks.length === 0) {
      return (
        <div className="p-10 text-center text-gray-400">
          <CheckCircle size={32} className="mx-auto mb-2 text-green-400" />
          Aucune réponse en attente de validation ✓
        </div>
      )
    }

    return (
      <div className="divide-y">
        {tasks.map((task) => (
          <div
            key={task.task_id}
            className={`border-l-4 transition-all ${
              task.priority_label === 'high'   ? 'border-l-red-500' :
              task.priority_label === 'medium' ? 'border-l-yellow-500' :
                                                 'border-l-green-400'
            }`}
          >
            {/* Header row */}
            <div
              className="p-4 cursor-pointer flex items-start justify-between gap-3"
              onClick={() => setExpanded(expanded === task.task_id ? null : task.task_id)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <PriorityBadge label={task.priority_label} />
                  <span className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full font-mono">
                    {task.application}
                  </span>
                  <span className="text-xs text-gray-400">{task.incident_type}</span>
                </div>
                <p className="text-sm font-medium text-gray-800 truncate">{task.user_question}</p>
                <div className="flex items-center gap-4 mt-1">
                  <TrustBar score={task.trust_score} />
                  <span className="text-xs text-gray-400">
                    {new Date(task.created_at).toLocaleString('fr-FR')}
                  </span>
                </div>
              </div>
              {expanded === task.task_id
                ? <ChevronUp size={15} className="text-gray-400 mt-1" />
                : <ChevronDown size={15} className="text-gray-400 mt-1" />}
            </div>

            {/* Expanded */}
            {expanded === task.task_id && (
              <div className="px-4 pb-4 space-y-3 border-t pt-3">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Réponse du chatbot</p>
                  <div className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 border max-h-36 overflow-y-auto whitespace-pre-wrap">
                    {task.bot_response}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => approveMutation.mutate(task.task_id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                  >
                    <CheckCircle size={12} /> Approuver
                  </button>
                  <button
                    onClick={() => setCorrectModal({ open: true, task, correctedResponse: '', correctionReason: '' })}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                  >
                    <Edit3 size={12} /> Corriger
                  </button>
                  <button
                    onClick={() => {
                      const r = prompt('Raison du rejet :')
                      if (r) rejectMutation.mutate({ id: task.task_id, reason: r })
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                  >
                    <XCircle size={12} /> Rejeter
                  </button>
                  <button
                    onClick={() => {
                      const n = prompt("Note d'escalade :")
                      if (n) escalateMutation.mutate({ id: task.task_id, note: n })
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition"
                  >
                    <ArrowUpCircle size={12} /> Escalader
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    )
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Main render
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <>
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
        {/* ── Tabs ──────────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-2">
          <div className="flex">
            <button
              onClick={() => setActiveTab('training')}
              className={`px-4 py-3.5 text-sm font-semibold transition border-b-2 ${
                activeTab === 'training'
                  ? 'border-indigo-600 text-indigo-700 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              🧠 Entraînement IA
              {pendingCount > 0 && (
                <span className="ml-2 text-xs bg-indigo-100 text-indigo-700 font-bold px-1.5 py-0.5 rounded-full">
                  {pendingCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('classic')}
              className={`px-4 py-3.5 text-sm font-semibold transition border-b-2 ${
                activeTab === 'classic'
                  ? 'border-blue-600 text-blue-700 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              🛡️ Validation N3
              {tasks.length > 0 && (
                <span className="ml-2 text-xs bg-blue-100 text-blue-700 font-bold px-1.5 py-0.5 rounded-full">
                  {tasks.length}
                </span>
              )}
            </button>
          </div>

          {/* ── Toolbar (training tab only) ─────────────────────────────────── */}
          {activeTab === 'training' && (
            <div className="flex items-center gap-2 pr-2">
              {/* Quick mode toggle */}
              <button
                onClick={toggleQuickMode}
                title={quickMode ? 'Désactiver le mode rapide' : 'Activer le mode rapide'}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg border transition font-medium
                  ${quickMode
                    ? 'bg-indigo-100 border-indigo-400 text-indigo-700'
                    : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-600'
                  }
                `}
              >
                {quickMode ? <Zap size={12} /> : <ZapOff size={12} />}
                {quickMode ? 'Rapide ON' : 'Mode rapide'}
              </button>

              {/* Show/hide HIGH tier */}
              <button
                onClick={() => setShowHigh(!showHigh)}
                title={showHigh ? 'Masquer les HIGH' : 'Afficher les HIGH'}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg border transition font-medium
                  ${showHigh
                    ? 'bg-green-50 border-green-300 text-green-700'
                    : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-green-50 hover:border-green-300 hover:text-green-700'
                  }
                `}
              >
                {showHigh ? <Eye size={12} /> : <EyeOff size={12} />}
                HIGH
              </button>

              {/* Refresh */}
              <button
                onClick={loadItems}
                title="Rafraîchir"
                className="flex items-center p-1.5 text-gray-400 hover:text-indigo-600 rounded-lg hover:bg-indigo-50 transition"
              >
                <RefreshCw size={13} />
              </button>
            </div>
          )}
        </div>

        {/* ── Filter bar (training tab) ────────────────────────────────────── */}
        {activeTab === 'training' && (
          <div className="flex items-center gap-1 px-4 py-2 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-750">
            {(['ALL', 'LOW', 'MEDIUM', 'HIGH'] as TierFilter[]).map((f) => {
              const count =
                f === 'ALL'
                  ? items.filter((i) => !i._localAction).length
                  : items.filter((i) => !i._localAction && i.validation_tier === f).length
              const active = filter === f
              const colorCls =
                f === 'LOW'    ? 'border-red-400 bg-red-50 text-red-700' :
                f === 'MEDIUM' ? 'border-yellow-400 bg-yellow-50 text-yellow-700' :
                f === 'HIGH'   ? 'border-green-400 bg-green-50 text-green-700' :
                                 'border-indigo-400 bg-indigo-50 text-indigo-700'
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`text-xs font-semibold px-2.5 py-1 rounded-full border transition
                    ${active ? colorCls : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300'}
                  `}
                >
                  {f} {count > 0 && <span className="ml-0.5 opacity-70">({count})</span>}
                </button>
              )
            })}
          </div>
        )}

        {/* ── Tab content ──────────────────────────────────────────────────── */}
        {activeTab === 'training' ? renderTrainingTab() : renderClassicTab()}
      </div>

      {/* ── Correct Modal (classic tab) ──────────────────────────────────── */}
      {correctModal.open && correctModal.task && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl">
            <div className="flex items-center justify-between p-5 border-b">
              <div className="flex items-center gap-2">
                <Edit3 size={16} className="text-blue-600" />
                <h2 className="font-semibold text-gray-800">Corriger la réponse</h2>
              </div>
              <button
                onClick={() => setCorrectModal({ open: false, task: null, correctedResponse: '', correctionReason: '' })}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >✕</button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Question utilisateur</p>
                <p className="mt-1 text-sm text-gray-700 bg-gray-50 rounded-lg p-3 border">{correctModal.task.user_question}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Réponse originale</p>
                <p className="mt-1 text-sm text-gray-500 bg-red-50 rounded-lg p-3 border border-red-100 line-through opacity-60">{correctModal.task.bot_response}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide">✏️ Réponse corrigée *</p>
                <textarea
                  rows={5}
                  className="mt-1 w-full text-sm border rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  placeholder="Entrez la réponse correcte…"
                  value={correctModal.correctedResponse}
                  onChange={(e) => setCorrectModal((s) => ({ ...s, correctedResponse: e.target.value }))}
                />
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Raison de la correction *</p>
                <input
                  type="text"
                  className="mt-1 w-full text-sm border rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  placeholder="Ex: Procédure incorrecte, mauvais système cible…"
                  value={correctModal.correctionReason}
                  onChange={(e) => setCorrectModal((s) => ({ ...s, correctionReason: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 p-5 border-t bg-gray-50 rounded-b-2xl">
              <button
                onClick={() => setCorrectModal({ open: false, task: null, correctedResponse: '', correctionReason: '' })}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg transition"
              >
                Annuler
              </button>
              <button
                onClick={() => correctMutation.mutate({
                  id: correctModal.task!.task_id,
                  correctedResponse: correctModal.correctedResponse,
                  correctionReason:  correctModal.correctionReason,
                })}
                disabled={!correctModal.correctedResponse || !correctModal.correctionReason || correctMutation.isPending}
                className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40 transition"
              >
                {correctMutation.isPending ? 'Envoi…' : 'Soumettre la correction'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
