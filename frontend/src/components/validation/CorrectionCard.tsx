/**
 * CorrectionCard — AI Training Interface Card
 *
 * Displays a single WeakPattern item for human review with:
 *  • Context block: query / intent / entity / tier / score
 *  • Pattern Insight: appeared N× / confirmed / rejected / confidence trend
 *  • AI Suggestion block: editable cause + solution + error tag checkboxes
 *  • Smart hints: confidence label, weak-evidence warning, learned-pattern indicator
 *  • Devil's Advocate: alternative hypothesis toggle
 *  • Action buttons: Confirm (reinforce) / Mark Wrong (suppress) / Skip
 */
import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CheckCircle2,
  XCircle,
  SkipForward,
  ChevronDown,
  ChevronUp,
  Pencil,
  BookOpen,
  AlertTriangle,
  Sparkles,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  Brain,
  Swords,
} from 'lucide-react'
import { useCorrectionStore, type CorrectionItem } from '@/stores/correctionStore'
import { fetchPatternInsight, type DevilAdvocate } from '@/services/correctionService'

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const ERROR_TAGS = [
  { id: 'generic_response',    label: 'Réponse générique' },
  { id: 'missing_correlation', label: 'Corrélation manquante' },
  { id: 'hallucination',       label: 'Hallucination' },
  { id: 'missing_entity',      label: 'Entité manquante' },
]

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

const TierBadge = ({ tier }: { tier: string }) => {
  const cls =
    tier === 'HIGH'   ? 'bg-green-100 text-green-700 border-green-300' :
    tier === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700 border-yellow-300' :
                        'bg-red-100 text-red-700 border-red-300'
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${cls}`}>
      {tier}
    </span>
  )
}

const ScoreBar = ({ score }: { score: number }) => {
  const pct = Math.round(score * 100)
  const color =
    pct >= 70 ? 'bg-green-500' :
    pct >= 40 ? 'bg-yellow-500' :
                'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-500">{pct}%</span>
    </div>
  )
}

interface SmartHintsProps {
  item: CorrectionItem
}

const SmartHints = ({ item }: SmartHintsProps) => {
  const hints: React.ReactNode[] = []

  // Confidence label
  const tierLabel =
    item.validation_tier === 'HIGH'   ? { text: 'Haute', cls: 'text-green-600' } :
    item.validation_tier === 'MEDIUM' ? { text: 'Moyenne', cls: 'text-yellow-600' } :
                                        { text: 'Faible', cls: 'text-red-600' }
  hints.push(
    <span key="conf" className={`flex items-center gap-1 text-xs font-medium ${tierLabel.cls}`}>
      <Sparkles size={11} />
      Confiance IA : {tierLabel.text}
    </span>
  )

  // Weak evidence
  if ((item.evidence_count ?? 0) < 2) {
    hints.push(
      <span key="weak" className="flex items-center gap-1 text-xs font-medium text-orange-500">
        <AlertTriangle size={11} />
        Preuves insuffisantes ({item.evidence_count ?? 0})
      </span>
    )
  }

  // Learned pattern
  if (item.source === 'learned' || item.source === 'learned_pattern') {
    hints.push(
      <span key="learned" className="flex items-center gap-1 text-xs font-medium text-indigo-600">
        <BookOpen size={11} />
        Modèle appris
      </span>
    )
  }

  return (
    <div className="flex flex-wrap gap-3 mt-1">
      {hints}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Pattern Insight block
// ─────────────────────────────────────────────────────────────────────────────

const PatternInsightBlock = ({ hypothesisId }: { hypothesisId: string }) => {
  const { data: insight, isLoading } = useQuery({
    queryKey: ['patternInsight', hypothesisId],
    queryFn: () => fetchPatternInsight(hypothesisId),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-gray-400 py-1">
        <Loader2 size={11} className="animate-spin" />
        Chargement insight…
      </div>
    )
  }

  if (!insight) return null

  const TrendIcon =
    insight.trend === 'up'   ? TrendingUp :
    insight.trend === 'down' ? TrendingDown :
                               Minus

  const trendCls =
    insight.trend === 'up'   ? 'text-green-600' :
    insight.trend === 'down' ? 'text-red-500' :
                               'text-gray-400'

  return (
    <div className="flex items-center flex-wrap gap-3 mt-2 px-3 py-2 bg-indigo-50 dark:bg-indigo-950 rounded-lg border border-indigo-100 dark:border-indigo-800">
      <span className="flex items-center gap-1 text-xs font-semibold text-indigo-700 dark:text-indigo-300">
        <Brain size={11} />
        Apparu {insight.appeared_count}×
      </span>
      <span className="text-xs text-green-600 font-medium">✅ {insight.confirmed_count}</span>
      <span className="text-xs text-red-500 font-medium">❌ {insight.rejected_count}</span>
      <span className={`flex items-center gap-0.5 text-xs font-medium ${trendCls}`}>
        <TrendIcon size={11} />
        {insight.trend === 'up' ? 'Hausse' : insight.trend === 'down' ? 'Baisse' : 'Stable'}
      </span>
      <span className="text-xs text-gray-500 font-mono">
        Score : {Math.round(insight.confidence_score * 100)}%
      </span>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Devil's Advocate block
// ─────────────────────────────────────────────────────────────────────────────

const DevilsAdvocateBlock = ({ data }: { data: DevilAdvocate }) => {
  const [open, setOpen] = useState(false)
  const pct = Math.round(data.alternative_confidence * 100)
  const deltaPct = Math.round(data.delta_vs_top * 100)

  return (
    <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-950 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900 transition"
      >
        <span className="flex items-center gap-1.5">
          <Swords size={12} />
          Avocat du diable — {data.alternative_hypothesis}
          <span className="ml-1 font-mono bg-amber-200 dark:bg-amber-800 px-1.5 py-0.5 rounded text-amber-800 dark:text-amber-200">
            {pct}%
          </span>
          <span className="text-amber-500 font-normal">(-{deltaPct}pp)</span>
        </span>
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-1.5">
          <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mt-1">Cause alternative</p>
          <p className="text-sm text-gray-800 dark:text-gray-200">{data.root_cause}</p>
          <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mt-1">Pourquoi moins probable</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 italic">{data.reason}</p>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

type CorrectionItemWithAdvocate = CorrectionItem & { devil_advocate?: DevilAdvocate }

interface Props {
  item: CorrectionItemWithAdvocate
  quickMode: boolean
}

export default function CorrectionCard({ item, quickMode }: Props) {
  const {
    confirmItem,
    suppressItem,
    skipItem,
    setEditedCause,
    setEditedActions,
    toggleErrorTag,
    actionStatus,
  } = useCorrectionStore()

  const [contextExpanded, setContextExpanded] = useState(!quickMode)
  const [actionsExpanded, setActionsExpanded] = useState(false)
  const causeRef = useRef<HTMLTextAreaElement>(null)

  const status = actionStatus[item.id] ?? 'idle'
  const done = item._localAction !== undefined
  const editedCause = item._editedCause ?? item.root_cause ?? ''
  const editedActions = item._editedActions ?? item.suggested_actions ?? []
  const errorTags = item._errorTags ?? []

  // Auto-focus cause field when expanded
  useEffect(() => {
    if (!quickMode && causeRef.current) {
      causeRef.current.focus()
    }
  }, [quickMode])

  // Keyboard shortcut: Enter to confirm when focused in cause field
  const handleCauseKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleConfirm()
    }
  }

  const handleConfirm = () =>
    confirmItem(item.id, editedCause, editedActions, errorTags)

  const handleSuppress = () =>
    suppressItem(item.id, editedCause, editedActions, errorTags)

  // ── Border color by tier ──────────────────────────────────────────────────
  const borderCls =
    item.validation_tier === 'LOW'    ? 'border-l-red-400' :
    item.validation_tier === 'MEDIUM' ? 'border-l-yellow-400' :
                                         'border-l-green-400'

  // ── Done state ────────────────────────────────────────────────────────────
  if (done) {
    const actionCls =
      item._localAction === 'confirmed'  ? 'bg-green-50 border-green-200 text-green-700' :
      item._localAction === 'suppressed' ? 'bg-red-50 border-red-200 text-red-700' :
                                           'bg-gray-50 border-gray-200 text-gray-400'
    const actionIcon =
      item._localAction === 'confirmed'  ? <CheckCircle2 size={14} /> :
      item._localAction === 'suppressed' ? <XCircle size={14} /> :
                                           <SkipForward size={14} />
    const actionLabel =
      item._localAction === 'confirmed'  ? 'Confirmé — IA renforcée ✓' :
      item._localAction === 'suppressed' ? 'Marqué erroné — IA corrigée ✓' :
                                           'Ignoré'
    return (
      <div className={`border-l-4 ${borderCls} rounded-r-xl px-4 py-3 opacity-60`}>
        <div className={`inline-flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-lg border ${actionCls}`}>
          {actionIcon} {actionLabel}
        </div>
      </div>
    )
  }

  return (
    <div className={`border-l-4 ${borderCls} bg-white dark:bg-gray-800 rounded-r-xl shadow-sm transition-all`}>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="px-4 pt-3 pb-2">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <TierBadge tier={item.validation_tier} />
            <span className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full font-mono">
              {item.entity_name}
            </span>
            <span className="text-xs text-gray-400">{item.entity_type}</span>
            <span className="text-xs text-gray-400 font-mono bg-gray-100 px-1.5 py-0.5 rounded">
              {item.hypothesis_id}
            </span>
          </div>
          <ScoreBar score={item.validation_score} />
        </div>

        {/* Smart hints */}
        <SmartHints item={item} />

        {/* Pattern Insight */}
        {item.hypothesis_id && (
          <PatternInsightBlock hypothesisId={item.hypothesis_id} />
        )}
      </div>

      {/* ── Context block (collapsible in quickMode) ─────────────────────── */}
      {!quickMode && (
        <div>
          <button
            className="w-full flex items-center justify-between px-4 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wide hover:bg-gray-50 dark:hover:bg-gray-700 transition"
            onClick={() => setContextExpanded((v) => !v)}
          >
            <span>Contexte de la requête</span>
            {contextExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
          {contextExpanded && (
            <div className="px-4 pb-3 space-y-1.5">
              <div className="bg-gray-50 dark:bg-gray-750 rounded-lg p-3 border border-gray-100 dark:border-gray-600">
                <p className="text-xs text-gray-400 mb-1 font-semibold uppercase tracking-wide">
                  Question utilisateur
                </p>
                <p className="text-sm text-gray-800 dark:text-gray-200">{item.query}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── AI Suggestion block ───────────────────────────────────────────── */}
      <div className="px-4 pb-2 space-y-3">
        {/* Root cause */}
        <div>
          <label className="text-xs font-semibold text-indigo-600 uppercase tracking-wide flex items-center gap-1 mb-1">
            <Pencil size={11} />
            Cause racine suggérée (éditable)
          </label>
          <textarea
            ref={causeRef}
            rows={quickMode ? 2 : 3}
            className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none transition"
            placeholder="Cause racine identifiée…"
            value={editedCause}
            onChange={(e) => setEditedCause(item.id, e.target.value)}
            onKeyDown={handleCauseKeyDown}
          />
          <p className="text-xs text-gray-400 mt-0.5">Ctrl+Entrée pour confirmer</p>
        </div>

        {/* Suggested actions (collapsible) */}
        {!quickMode && (
          <div>
            <button
              className="flex items-center gap-1 text-xs font-semibold text-gray-500 uppercase tracking-wide hover:text-gray-700 transition"
              onClick={() => setActionsExpanded((v) => !v)}
            >
              {actionsExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              Actions suggérées ({editedActions.length})
            </button>
            {actionsExpanded && (
              <div className="mt-2 space-y-1.5">
                {editedActions.map((action, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-xs font-mono text-gray-400 mt-1 w-5 shrink-0">{idx + 1}.</span>
                    <input
                      type="text"
                      className="flex-1 text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-400 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                      value={action}
                      onChange={(e) => {
                        const updated = [...editedActions]
                        updated[idx] = e.target.value
                        setEditedActions(item.id, updated)
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Error tags */}
        {!quickMode && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Tags d'erreur
            </p>
            <div className="flex flex-wrap gap-2">
              {ERROR_TAGS.map((tag) => {
                const active = errorTags.includes(tag.id)
                return (
                  <button
                    key={tag.id}
                    onClick={() => toggleErrorTag(item.id, tag.id)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition font-medium
                      ${active
                        ? 'bg-red-100 border-red-400 text-red-700'
                        : 'bg-gray-50 border-gray-200 text-gray-500 hover:border-red-300 hover:text-red-600'
                      }
                    `}
                  >
                    {tag.label}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Devil's Advocate block */}
        {item.devil_advocate && (
          <DevilsAdvocateBlock data={item.devil_advocate} />
        )}
      </div>

      {/* ── Action buttons ────────────────────────────────────────────────── */}
      <div className="px-4 pb-4 flex flex-wrap gap-2">
        <button
          onClick={handleConfirm}
          disabled={status === 'pending'}
          className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-40 transition"
        >
          {status === 'pending' ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <CheckCircle2 size={12} />
          )}
          Confirmer
        </button>
        <button
          onClick={handleSuppress}
          disabled={status === 'pending'}
          className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-40 transition"
        >
          {status === 'pending' ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <XCircle size={12} />
          )}
          Marquer erroné
        </button>
        <button
          onClick={() => skipItem(item.id)}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition"
        >
          <SkipForward size={12} />
          Ignorer
        </button>

        {status === 'error' && (
          <span className="text-xs text-red-500 self-center">
            ⚠ Erreur réseau
          </span>
        )}
      </div>
    </div>
  )
}
