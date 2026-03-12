/**
 * Page State Store (Zustand + persist)
 * Persists UI state for all pages across navigation.
 * All state is serializable — no File objects (those can't be serialized).
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ─── ClassificationML ───────────────────────────────────────────────────────
export interface UploadResponseSnapshot {
  session_id?: string;
  filename?: string;
  rows?: number;
  columns?: string[];
  preview?: Record<string, any>[];
  [key: string]: any;
}

interface MLState {
  uploadedData: UploadResponseSnapshot | null;
  sessionId: string | null;
  activeTab: string;
  threshold: number;
}

// ─── CollectionPage ──────────────────────────────────────────────────────────
interface DataSourceSnapshot {
  id: string;
  type: 'sql' | 'documents' | 'code';
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  itemsCount: number;
  lastUpdated: string;
  progress?: number;
  error?: string;
}

interface CollectionState {
  dataSources: DataSourceSnapshot[];
  stats: Record<string, any>;
}

// ─── SettingsPage ────────────────────────────────────────────────────────────
interface SettingsState {
  activeTab: 'llm' | 'database' | 'ui';
}

// ─── JiraSection ─────────────────────────────────────────────────────────────
interface JiraState {
  searchQuery: string;
  selectedProjectKey: string | null;
  currentPage: number;
}

// ─── Store ───────────────────────────────────────────────────────────────────
interface PageStateStore {
  // ClassificationML
  ml: MLState;
  setMLUploadedData: (data: UploadResponseSnapshot | null) => void;
  setMLSessionId: (id: string | null) => void;
  setMLActiveTab: (tab: string) => void;
  setMLThreshold: (v: number) => void;
  clearML: () => void;

  // Collection
  collection: CollectionState;
  setCollectionSources: (sources: DataSourceSnapshot[]) => void;
  setCollectionStats: (stats: Record<string, any>) => void;

  // Settings
  settings: SettingsState;
  setSettingsActiveTab: (tab: 'llm' | 'database' | 'ui') => void;

  // Jira
  jira: JiraState;
  setJiraSearchQuery: (q: string) => void;
  setJiraSelectedProject: (key: string | null) => void;
  setJiraPage: (page: number) => void;
}

const defaultML: MLState = {
  uploadedData: null,
  sessionId: null,
  activeTab: 'resume',
  threshold: 0.5,
};

const defaultCollection: CollectionState = {
  dataSources: [
    { id: '1', type: 'sql',       name: 'brasil_db.sql',        status: 'completed', itemsCount: 0, lastUpdated: '-' },
    { id: '2', type: 'documents', name: 'Fiches FR (001-999)',   status: 'completed', itemsCount: 0, lastUpdated: '-' },
    { id: '3', type: 'code',      name: 'Source Code BRASIL',    status: 'pending',   itemsCount: 0, lastUpdated: '-' },
  ],
  stats: {},
};

const defaultSettings: SettingsState = { activeTab: 'llm' };

const defaultJira: JiraState = { searchQuery: '', selectedProjectKey: null, currentPage: 0 };

export const usePageStateStore = create<PageStateStore>()(
  persist(
    (set) => ({
      // ML
      ml: defaultML,
      setMLUploadedData: (data) => set((s) => ({ ml: { ...s.ml, uploadedData: data } })),
      setMLSessionId: (id) => set((s) => ({ ml: { ...s.ml, sessionId: id } })),
      setMLActiveTab: (tab) => set((s) => ({ ml: { ...s.ml, activeTab: tab } })),
      setMLThreshold: (v) => set((s) => ({ ml: { ...s.ml, threshold: v } })),
      clearML: () => set({ ml: defaultML }),

      // Collection
      collection: defaultCollection,
      setCollectionSources: (sources) => set((s) => ({ collection: { ...s.collection, dataSources: sources } })),
      setCollectionStats: (stats) => set((s) => ({ collection: { ...s.collection, stats } })),

      // Settings
      settings: defaultSettings,
      setSettingsActiveTab: (tab) => set((s) => ({ settings: { ...s.settings, activeTab: tab } })),

      // Jira
      jira: defaultJira,
      setJiraSearchQuery: (q) => set((s) => ({ jira: { ...s.jira, searchQuery: q } })),
      setJiraSelectedProject: (key) => set((s) => ({ jira: { ...s.jira, selectedProjectKey: key } })),
      setJiraPage: (page) => set((s) => ({ jira: { ...s.jira, currentPage: page } })),
    }),
    {
      name: 'page-state-store',
      // Only persist serializable data, skip any transient loading/error state
      partialize: (state) => ({
        ml: state.ml,
        collection: state.collection,
        settings: state.settings,
        jira: state.jira,
      }),
    }
  )
);
