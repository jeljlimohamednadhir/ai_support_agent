/**
 * Correction Store (Zustand)
 * Manages state for the AI Training / Correction Interface
 */
import { create } from 'zustand'
import type { WeakPattern, CorrectionRequest } from '../services/correctionService'
import {
  submitCorrection,
  fetchWeakPatterns,
} from '../services/correctionService'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type TierFilter = 'ALL' | 'LOW' | 'MEDIUM' | 'HIGH'

export type ActionStatus = 'idle' | 'pending' | 'done' | 'error'

export interface CorrectionItem extends WeakPattern {
  /** Local UI state: has the operator already acted on this item? */
  _localAction?: 'confirmed' | 'suppressed' | 'skipped'
  /** Inline-edited cause (operator override) */
  _editedCause?: string
  /** Inline-edited actions (operator override) */
  _editedActions?: string[]
  /** Selected error tags */
  _errorTags?: string[]
}

interface CorrectionState {
  items: CorrectionItem[]
  quickMode: boolean
  filter: TierFilter
  showHigh: boolean
  loadStatus: 'idle' | 'loading' | 'loaded' | 'error'
  actionStatus: Record<string, ActionStatus>  // keyed by item.id

  // ── Actions ──────────────────────────────────────────────────────────────
  loadItems: () => Promise<void>

  /** Mark as confirmed → POST /corrections/ with correction_type=reinforce */
  confirmItem: (
    id: string,
    editedCause?: string,
    editedActions?: string[],
    errorTags?: string[]
  ) => Promise<void>

  /** Mark as wrong → POST /corrections/ with correction_type=suppress */
  suppressItem: (
    id: string,
    editedCause?: string,
    editedActions?: string[],
    errorTags?: string[]
  ) => Promise<void>

  /** Skip (dismiss without learning) */
  skipItem: (id: string) => void

  /** Update inline-edited cause for an item */
  setEditedCause: (id: string, cause: string) => void

  /** Update inline-edited actions for an item */
  setEditedActions: (id: string, actions: string[]) => void

  /** Toggle an error tag on/off */
  toggleErrorTag: (id: string, tag: string) => void

  toggleQuickMode: () => void
  setFilter: (f: TierFilter) => void
  setShowHigh: (v: boolean) => void
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const TIER_ORDER: Record<string, number> = { LOW: 0, MEDIUM: 1, HIGH: 2 }

const sortItems = (items: CorrectionItem[]): CorrectionItem[] =>
  [...items].sort((a, b) => {
    const ta = TIER_ORDER[a.validation_tier] ?? 3
    const tb = TIER_ORDER[b.validation_tier] ?? 3
    if (ta !== tb) return ta - tb
    // Secondary: lowest score first (least confident first)
    return a.validation_score - b.validation_score
  })

const getOperatorId = (): string => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) {
      const p = JSON.parse(raw)
      return p?.username || p?.login || 'n3_operator'
    }
  } catch {}
  return 'n3_operator'
}

const buildRequest = (
  item: CorrectionItem,
  correctionType: 'reinforce' | 'suppress',
  editedCause?: string,
  editedActions?: string[],
  errorTags?: string[]
): CorrectionRequest => ({
  query: item.query,
  original_response: item.root_cause ?? '',
  corrected_response: editedCause ?? item.root_cause ?? '',
  entity_name: item.entity_name,
  entity_type: item.entity_type,
  hypothesis_id: item.hypothesis_id,
  correction_type: correctionType,
  corrected_root_cause: editedCause ?? '',
  corrected_actions: editedActions ?? item.suggested_actions ?? [],
  operator_id: getOperatorId(),
  error_tags: errorTags ?? [],
})

// ─────────────────────────────────────────────────────────────────────────────
// Store
// ─────────────────────────────────────────────────────────────────────────────

export const useCorrectionStore = create<CorrectionState>((set, get) => ({
  items: [],
  quickMode: false,
  filter: 'ALL',
  showHigh: false,
  loadStatus: 'idle',
  actionStatus: {},

  loadItems: async () => {
    set({ loadStatus: 'loading' })
    try {
      const raw = await fetchWeakPatterns()
      set({ items: sortItems(raw as CorrectionItem[]), loadStatus: 'loaded' })
    } catch {
      set({ loadStatus: 'error' })
    }
  },

  confirmItem: async (id, editedCause, editedActions, errorTags) => {
    const item = get().items.find((i) => i.id === id)
    if (!item) return

    set((s) => ({ actionStatus: { ...s.actionStatus, [id]: 'pending' } }))
    try {
      await submitCorrection(buildRequest(item, 'reinforce', editedCause, editedActions, errorTags))
      set((s) => ({
        items: s.items.map((i) =>
          i.id === id ? { ...i, _localAction: 'confirmed' } : i
        ),
        actionStatus: { ...s.actionStatus, [id]: 'done' },
      }))
    } catch {
      set((s) => ({ actionStatus: { ...s.actionStatus, [id]: 'error' } }))
    }
  },

  suppressItem: async (id, editedCause, editedActions, errorTags) => {
    const item = get().items.find((i) => i.id === id)
    if (!item) return

    set((s) => ({ actionStatus: { ...s.actionStatus, [id]: 'pending' } }))
    try {
      await submitCorrection(buildRequest(item, 'suppress', editedCause, editedActions, errorTags))
      set((s) => ({
        items: s.items.map((i) =>
          i.id === id ? { ...i, _localAction: 'suppressed' } : i
        ),
        actionStatus: { ...s.actionStatus, [id]: 'done' },
      }))
    } catch {
      set((s) => ({ actionStatus: { ...s.actionStatus, [id]: 'error' } }))
    }
  },

  skipItem: (id) =>
    set((s) => ({
      items: s.items.map((i) =>
        i.id === id ? { ...i, _localAction: 'skipped' } : i
      ),
    })),

  setEditedCause: (id, cause) =>
    set((s) => ({
      items: s.items.map((i) =>
        i.id === id ? { ...i, _editedCause: cause } : i
      ),
    })),

  setEditedActions: (id, actions) =>
    set((s) => ({
      items: s.items.map((i) =>
        i.id === id ? { ...i, _editedActions: actions } : i
      ),
    })),

  toggleErrorTag: (id, tag) =>
    set((s) => ({
      items: s.items.map((i) => {
        if (i.id !== id) return i
        const tags = i._errorTags ?? []
        return {
          ...i,
          _errorTags: tags.includes(tag)
            ? tags.filter((t) => t !== tag)
            : [...tags, tag],
        }
      }),
    })),

  toggleQuickMode: () => set((s) => ({ quickMode: !s.quickMode })),
  setFilter: (f) => set({ filter: f }),
  setShowHigh: (v) => set({ showHigh: v }),
}))
