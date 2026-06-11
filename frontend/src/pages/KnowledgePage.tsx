import { useEffect, useState } from 'react'
import KnowledgeGraph from '@/components/dashboard/KnowledgeGraph'
import { getBrasilPresentation } from '@/services/api'
import {
  Server, Database, Network, AlertTriangle, BookOpen, Cpu,
  GitBranch, Zap, ChevronDown, ChevronRight, CheckCircle2,
  ArrowRight, Layers, Shield, RefreshCw, Info,
} from 'lucide-react'

// ─── Types ───────────────────────────────────────────────────────────────────

interface BrasilPresentation {
  meta: { title: string; version: string; generated_at: string }
  presentation: {
    nom_complet: string; nature: string; domaine: string
    description_courte: string; description_longue: string
    contexte_operationnel: string
  }
  architecture: {
    type_systeme: string
    composants_principaux: Array<{ nom: string; role: string; type: string }>
    base_de_donnees: { nom: string; serveur: string; type: string; tables_cles: string[] }
    messagerie: { type: string; queues_cles: string[]; monitoring: string }
  }
  entites_principales: Record<string, { description: string; etats?: string[]; attribut_cle?: string; role?: string; attributs?: string[] }>
  processus_metier: Array<{ code: string; nom: string; description: string; declencheur?: string; duree_typique?: string }>
  systemes_connectes: Record<string, { role: string; protocole?: string; direction?: string; utilisation?: string; problemes_connus?: string }>
  incidents_frequents: Array<{ type: string; description: string; action_n3: string }>
  procedures_cles: Array<{ ref: string; nom: string; description: string }>
  contraintes_techniques: Array<{ ref: string; description: string }>
  chatbot_knowledge_summary: string
}

// ─── Helpers UI ───────────────────────────────────────────────────────────────

function Section({ title, icon: Icon, children, color = 'blue' }: {
  title: string; icon: React.ElementType; children: React.ReactNode; color?: string
}) {
  const hdr: Record<string, string> = {
    blue:   'border-blue-200   bg-blue-50   text-blue-700',
    green:  'border-green-200  bg-green-50  text-green-700',
    purple: 'border-purple-200 bg-purple-50 text-purple-700',
    orange: 'border-orange-200 bg-orange-50 text-orange-700',
    red:    'border-red-200    bg-red-50    text-red-700',
    teal:   'border-teal-200   bg-teal-50   text-teal-700',
    indigo: 'border-indigo-200 bg-indigo-50 text-indigo-700',
  }
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
      <div className={`flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100 dark:border-gray-700 ${hdr[color] ?? hdr.blue}`}>
        <Icon className="w-4 h-4" />
        <h2 className="font-semibold text-sm">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

function Collapsible({ title, badge, children }: { title: string; badge?: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 text-sm font-medium text-left transition-colors"
      >
        <span className="flex items-center gap-2">
          {open ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          {title.replace(/_/g, ' ')}
          {badge && <span className="text-xs px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 rounded">{badge}</span>}
        </span>
      </button>
      {open && <div className="p-4 text-sm">{children}</div>}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function KnowledgePage() {
  const [data, setData] = useState<BrasilPresentation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'brasil' | 'correlations' | 'chatbot' | 'graph'>('brasil')

  useEffect(() => {
    getBrasilPresentation()
      .then(setData)
      .catch((e: any) => setError(e?.response?.data?.detail || e.message || 'Erreur chargement'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Base de connaissances</h1>
        <p className="text-sm text-gray-500 mt-1">Présentation BRASIL · Capacités du chatbot · Graphe</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl w-fit">
        {([
          { id: 'brasil', label: '🏗️ BRASIL' },
          { id: 'correlations', label: '🔗 Corrélations' },
          { id: 'chatbot', label: '🤖 Chatbot' },
          { id: 'graph', label: '🕸️ Graphe' },
        ] as { id: typeof activeTab; label: string }[]).map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === t.id
                ? 'bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-white'
                : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Corrélations ── */}
      <div className={activeTab === 'correlations' ? '' : 'hidden'}>
        <div className="space-y-4">
          <div className="bg-gradient-to-r from-indigo-600 to-cyan-600 rounded-xl p-5 text-white shadow">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 mt-0.5 flex-shrink-0 opacity-80" />
              <div className="space-y-2">
                <p className="text-sm leading-relaxed opacity-95">
                  Cet onglet présente les sources corrélées qui alimentent le chatbot BRASIL : tables SQL, relations FK,
                  contraintes, index, triggers, séquences, vues et fonctions.
                </p>
                <p className="text-xs opacity-80">
                  Les données sont extraites depuis la session `brasil_prod` et injectées dans la base de connaissances du chatbot.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {[
              {
                title: 'Tables de vérité', icon: Database, color: 'blue',
                items: ['130 tables indexées', 'Colonnes + types + defaults', 'PK/UK/CHECK consolidés'],
              },
              {
                title: 'Relations', icon: GitBranch, color: 'teal',
                items: ['193 FK extraites', 'Graphe parent → enfant', 'Corrélations équipement / EPC / MRT / VLAN'],
              },
              {
                title: 'Comportements métier', icon: Shield, color: 'green',
                items: ['100 triggers', '242 fonctions', 'États SMALLINT / VARCHAR(1)'],
              },
              {
                title: 'Performance', icon: Zap, color: 'orange',
                items: ['184 index', 'Statistiques de taille', 'Tables les plus volumineuses'],
              },
              {
                title: 'Injection chatbot', icon: Layers, color: 'purple',
                items: ['Pack généré automatiquement', 'KnowledgeLayer enrichi', 'Recherche canonique + corrélation'],
              },
              {
                title: 'Lecture opérationnelle', icon: Network, color: 'indigo',
                items: ['t_mrt_access_dslams', 't_res_prod_controlables', 't_epc_vers', 't_makingfiles'],
              },
            ].map(card => (
              <div key={card.title} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
                <div className={`px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2 ${
                  card.color === 'blue' ? 'bg-blue-50 text-blue-700' :
                  card.color === 'teal' ? 'bg-teal-50 text-teal-700' :
                  card.color === 'green' ? 'bg-green-50 text-green-700' :
                  card.color === 'orange' ? 'bg-orange-50 text-orange-700' :
                  card.color === 'purple' ? 'bg-purple-50 text-purple-700' :
                  'bg-indigo-50 text-indigo-700'
                }`}>
                  <card.icon className="w-4 h-4" />
                  <h3 className="text-sm font-semibold">{card.title}</h3>
                </div>
                <ul className="p-4 space-y-2 text-sm text-gray-600 dark:text-gray-300">
                  {card.items.map(item => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1 w-1.5 h-1.5 rounded-full bg-current opacity-70" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h2 className="font-semibold mb-3">Chaîne de corrélation</h2>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-sm">
              {[
                'Session SQL',
                'JSON brut',
                'brasil_schema_knowledge.py',
                'KnowledgeLayer',
                'UI Knowledge',
              ].map((step, i) => (
                <div key={step} className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 bg-gray-50 dark:bg-gray-700/40">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-bold">{i + 1}</span>
                    <span className="font-medium text-gray-800 dark:text-gray-100">{step}</span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Étape de corrélation et d’injection dans la base de connaissances.
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── BRASIL ── */}
      <div className={activeTab === 'brasil' ? '' : 'hidden'}>
        {loading && (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mr-3" />
            <span className="text-gray-500">Chargement…</span>
          </div>
        )}
        {error && (
          <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {data && (
          <div className="space-y-4">

            {/* Résumé chatbot */}
            <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl p-5 text-white shadow">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 mt-0.5 flex-shrink-0 opacity-80" />
                <p className="text-sm leading-relaxed opacity-95">{data.chatbot_knowledge_summary}</p>
              </div>
            </div>

            {/* Présentation générale */}
            <Section title="Présentation générale" icon={BookOpen} color="blue">
              <div className="space-y-3">
                <p className="font-semibold text-gray-800 dark:text-gray-100">{data.presentation.nom_complet}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                    <span className="text-xs text-gray-400">Nature</span>
                    <p className="text-sm font-medium mt-0.5">{data.presentation.nature}</p>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                    <span className="text-xs text-gray-400">Domaine</span>
                    <p className="text-sm font-medium mt-0.5">{data.presentation.domaine}</p>
                  </div>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{data.presentation.description_longue}</p>
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-3 text-sm text-amber-800 dark:text-amber-200">
                  <span className="font-semibold">Contexte opérationnel : </span>{data.presentation.contexte_operationnel}
                </div>
              </div>
            </Section>

            {/* Architecture */}
            <Section title="Architecture technique" icon={Cpu} color="purple">
              <div className="space-y-4">
                <p className="text-sm flex items-center gap-2"><Layers className="w-4 h-4 text-purple-500" />{data.architecture.type_systeme}</p>
                <div>
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Composants</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {data.architecture.composants_principaux.map(c => (
                      <div key={c.nom} className="border border-gray-200 dark:border-gray-600 rounded-lg p-3 text-sm">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono font-semibold text-purple-700 dark:text-purple-300 text-xs">{c.nom}</span>
                          <span className="text-xs px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-600 rounded">{c.type}</span>
                        </div>
                        <p className="text-gray-500 text-xs">{c.role}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                    <div className="flex items-center gap-1.5 mb-1"><Database className="w-3.5 h-3.5 text-gray-400" /><span className="text-xs font-semibold text-gray-400">Base de données</span></div>
                    <p className="text-sm font-medium">{data.architecture.base_de_donnees.nom} <span className="text-gray-400 text-xs">@{data.architecture.base_de_donnees.serveur}</span></p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {data.architecture.base_de_donnees.tables_cles.map(t => <span key={t} className="text-xs font-mono bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 px-1.5 py-0.5 rounded">{t}</span>)}
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                    <div className="flex items-center gap-1.5 mb-1"><Network className="w-3.5 h-3.5 text-gray-400" /><span className="text-xs font-semibold text-gray-400">Messagerie</span></div>
                    <p className="text-sm font-medium">{data.architecture.messagerie.type}</p>
                    <p className="text-xs text-gray-400 mt-0.5">Monitoring : {data.architecture.messagerie.monitoring}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {data.architecture.messagerie.queues_cles.map(q => <span key={q} className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded">{q}</span>)}
                    </div>
                  </div>
                </div>
              </div>
            </Section>

            {/* Entités */}
            <Section title="Entités principales" icon={GitBranch} color="teal">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(data.entites_principales).map(([name, ent]) => (
                  <div key={name} className="border border-gray-200 dark:border-gray-600 rounded-lg p-3 text-sm">
                    <span className="font-mono font-bold text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/30 px-2 py-0.5 rounded text-xs">{name}</span>
                    <p className="text-gray-600 dark:text-gray-300 text-xs mt-1.5 leading-relaxed">{ent.description}</p>
                    {ent.attribut_cle && <p className="mt-1 text-xs text-gray-400"><span className="font-semibold">Clé :</span> {ent.attribut_cle}</p>}
                    {ent.etats && ent.etats.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {ent.etats.map(e => <span key={e} className="text-xs bg-teal-50 dark:bg-teal-900/20 text-teal-700 dark:text-teal-300 px-1.5 py-0.5 rounded border border-teal-200 dark:border-teal-700">{e}</span>)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Section>

            {/* Processus */}
            <Section title="Processus métier" icon={Zap} color="orange">
              <div className="space-y-2">
                {data.processus_metier.map(p => (
                  <div key={p.code} className="flex gap-3 p-3 rounded-lg border border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <span className="font-mono font-bold text-orange-600 dark:text-orange-400 text-sm min-w-[80px]">{p.code}</span>
                    <div className="flex-1">
                      <p className="font-medium text-sm">{p.nom}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>
                      {p.declencheur && <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1"><ArrowRight className="w-3 h-3" />{p.declencheur}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </Section>

            {/* Systèmes connectés */}
            <Section title="Systèmes connectés" icon={Network} color="indigo">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(data.systemes_connectes).map(([name, sys]) => (
                  <div key={name} className="border border-gray-200 dark:border-gray-600 rounded-lg p-3 text-sm">
                    <p className="font-semibold mb-1">{name}</p>
                    <p className="text-xs text-gray-500">{sys.role}</p>
                    {sys.protocole && <p className="text-xs text-gray-400 mt-1"><span className="font-medium">Protocole :</span> {sys.protocole}</p>}
                    {sys.direction && <p className="text-xs text-indigo-600 dark:text-indigo-400 mt-1 font-mono">{sys.direction}</p>}
                    {sys.problemes_connus && <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">⚠ {sys.problemes_connus}</p>}
                  </div>
                ))}
              </div>
            </Section>

            {/* Incidents + Procédures */}
            <Section title="Incidents fréquents & Procédures N3" icon={AlertTriangle} color="red">
              <div className="space-y-2">
                {data.incidents_frequents.map(inc => (
                  <Collapsible key={inc.type} title={inc.type} badge="INCIDENT">
                    <p className="text-gray-600 dark:text-gray-300 mb-2">{inc.description}</p>
                    <div className="flex items-start gap-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded p-2 text-green-800 dark:text-green-200 text-xs">
                      <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                      <span><span className="font-semibold">Action N3 :</span> {inc.action_n3}</span>
                    </div>
                  </Collapsible>
                ))}
                <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Procédures clés</h3>
                  {data.procedures_cles.map(p => (
                    <div key={p.ref} className="flex gap-3 items-start text-sm py-1.5 border-b border-gray-100 dark:border-gray-700 last:border-0">
                      <span className="font-mono text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-0.5 rounded min-w-[120px]">{p.ref}</span>
                      <div>
                        <span className="font-medium">{p.nom}</span>
                        <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Section>

            {/* Contraintes */}
            <Section title="Contraintes techniques (CSTR-*)" icon={Shield} color="green">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {data.contraintes_techniques.map(c => (
                  <div key={c.ref} className="flex gap-3 items-start p-2.5 rounded-lg border border-gray-100 dark:border-gray-700 text-sm hover:bg-gray-50 dark:hover:bg-gray-700/40">
                    <span className="font-mono text-xs bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 px-1.5 py-0.5 rounded min-w-[130px]">{c.ref}</span>
                    <span className="text-xs text-gray-500">{c.description}</span>
                  </div>
                ))}
              </div>
            </Section>

          </div>
        )}
      </div>

      {/* ── Chatbot ── */}
      <div className={activeTab === 'chatbot' ? '' : 'hidden'}>
        <div className="space-y-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h2 className="font-semibold mb-3">Capacités principales</h2>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
              {[
                ['Recherche RAG', 'Embedding MiniLM-L12-v2 + index FAISS, récupère les chunks les plus proches avant chaque réponse.'],
                ['Explication Jira', "Détecte une clé Jira dans le message ou l'historique et génère une analyse du ticket BRASIL."],
                ['Inférence technique', 'Reconnaît les symboles CamelCase / *Service / *Manager et répond par raisonnement LLM sans blocage.'],
                ['Classification ML', 'Pipeline hybride TF-IDF + FAISS, 21 classes incidents, correction interactive et réentraînement.'],
                ['Diagnostic N3', '5 procédures expertes inline, 30+ patterns BRASIL, activées automatiquement sur les logs.'],
                ['Anti-hallucination', 'Trust gate 4 niveaux, le chatbot refuse de répondre si la confiance est insuffisante.'],
              ].map(([k, v]) => (
                <li key={k}><span className="font-medium text-gray-800 dark:text-gray-100">{k}</span> — {v}</li>
              ))}
            </ul>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h2 className="font-semibold mb-3">Niveaux de confiance</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              {[
                { label: 'HIGH', range: '≥ 0.75', cls: 'text-green-700 bg-green-50 border-green-200', dot: 'bg-green-500' },
                { label: 'MEDIUM', range: '0.50–0.75', cls: 'text-blue-700 bg-blue-50 border-blue-200', dot: 'bg-blue-500' },
                { label: 'LOW', range: '0.35–0.50', cls: 'text-orange-700 bg-orange-50 border-orange-200', dot: 'bg-orange-500' },
                { label: 'INSUFFISANT', range: '< 0.35', cls: 'text-red-700 bg-red-50 border-red-200', dot: 'bg-red-500' },
              ].map(t => (
                <div key={t.label} className={`p-3 rounded-lg border ${t.cls}`}>
                  <div className="flex items-center gap-1.5 mb-1"><span className={`w-2 h-2 rounded-full ${t.dot}`} /><span className="font-bold text-xs">{t.label}</span></div>
                  <span className="font-mono text-xs">{t.range}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h2 className="font-semibold mb-3">21 classes de classification ML</h2>
            <div className="flex flex-wrap gap-1.5">
              {['Incident réseau DSLAM','Problème CPE client','Authentification RADIUS','Configuration VLAN','Signal DSL / SNR','Provisioning auto','Escalade N3 Transmission','Escalade N3 IP/MPLS','Escalade N3 Accès','Maintenance planifiée','Fausse alarme','Demande de renseignement','Incident critique P1','Incident majeur P2','Incident mineur P3','Changement infra','Restauration service','Surveillance MRT','Analyse CMDB','Qualité de service','Autre'].map((cls, i) => (
                <span key={cls} className="text-xs px-2.5 py-1 rounded-full border font-medium" style={{ background: `hsl(${(i*17)%360},65%,95%)`, borderColor: `hsl(${(i*17)%360},50%,82%)`, color: `hsl(${(i*17)%360},55%,35%)` }}>{cls}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Graphe ── */}
      <div className={activeTab === 'graph' ? '' : 'hidden'}>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-5 py-3.5 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2">
            <Server className="w-4 h-4 text-gray-500" />
            <h2 className="font-semibold text-sm text-gray-700 dark:text-gray-300">Graphe de connaissance Neo4j</h2>
          </div>
          <div className="p-5"><KnowledgeGraph /></div>
        </div>
      </div>

    </div>
  )
}
