import KnowledgeGraph from '@/components/dashboard/KnowledgeGraph'

export default function KnowledgePage() {
  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Base de connaissances</h1>
        <p className="text-sm text-gray-500 mt-1">Intelligence et capacités du chatbot</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Capacités principales</h2>
        <ul className="space-y-2 text-sm text-gray-600">
          <li><span className="font-medium text-gray-800">Recherche RAG</span> — Embedding MiniLM-L12-v2 + index FAISS, récupère les chunks les plus proches avant chaque réponse.</li>
          <li><span className="font-medium text-gray-800">Explication Jira</span> — Détecte une clé Jira dans le message ou l&apos;historique et génère une analyse du ticket BRASIL.</li>
          <li><span className="font-medium text-gray-800">Inférence technique</span> — Reconnaît les symboles CamelCase / *Service / *Manager et répond par raisonnement LLM sans blocage.</li>
          <li><span className="font-medium text-gray-800">Classification ML</span> — Pipeline hybride TF-IDF + FAISS, 21 classes incidents, correction interactive et réentraînement.</li>
          <li><span className="font-medium text-gray-800">Diagnostic N3</span> — 5 procédures expertes inline, 30+ patterns BRASIL, activées automatiquement sur les logs.</li>
          <li><span className="font-medium text-gray-800">Anti-hallucination</span> — Trust gate 4 niveaux, le chatbot refuse de répondre si la confiance est insuffisante.</li>
        </ul>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Modes de pipeline</h2>
        <div className="space-y-2 text-sm">
          <div className="flex gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
            <span className="font-mono font-bold text-green-700 min-w-[80px]">FR_RICH</span>
            <span className="text-gray-600">Message long avec contexte réseau — RAG complet depuis la base vectorielle.</span>
          </div>
          <div className="flex gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
            <span className="font-mono font-bold text-yellow-700 min-w-[80px]">FR_WEAK</span>
            <span className="text-gray-600">Message court ou ambigu — clarification ou FAQ statiques.</span>
          </div>
          <div className="flex gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <span className="font-mono font-bold text-blue-700 min-w-[80px]">LOG_BASED</span>
            <span className="text-gray-600">Logs ou codes erreur détectés — moteur de diagnostic N3 activé.</span>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Niveaux de confiance (Trust Score)</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          {[
            { label: 'HIGH', range: '≥ 0.75', color: 'text-green-700 bg-green-50 border-green-200', dot: 'bg-green-500' },
            { label: 'MEDIUM', range: '0.50 – 0.75', color: 'text-blue-700 bg-blue-50 border-blue-200', dot: 'bg-blue-500' },
            { label: 'LOW', range: '0.35 – 0.50', color: 'text-orange-700 bg-orange-50 border-orange-200', dot: 'bg-orange-500' },
            { label: 'INSUFFISANT', range: '< 0.35', color: 'text-red-700 bg-red-50 border-red-200', dot: 'bg-red-500' },
          ].map((t) => (
            <div key={t.label} className={`p-3 rounded-lg border ${t.color}`}>
              <div className="flex items-center gap-1.5 mb-1">
                <span className={`w-2 h-2 rounded-full ${t.dot}`} />
                <span className="font-bold text-xs">{t.label}</span>
              </div>
              <span className="font-mono text-xs">{t.range}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Procédures N3 intégrées</h2>
        <div className="space-y-1.5 text-sm">
          {[
            ['DslamClosed', 'DSLAM fermé / hors service'],
            ['UnknownMRT', 'MRT inconnu ou absent'],
            ['BusinessRule', 'Violation règle métier'],
            ['ConnectorUnavailable', 'Connecteur indisponible'],
            ['DslamUnreachable', 'DSLAM injoignable'],
          ].map(([id, trigger]) => (
            <div key={id} className="flex items-center gap-3 py-1.5 border-b border-gray-100 last:border-0">
              <span className="font-mono text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded min-w-[170px]">{id}</span>
              <span className="text-gray-500">{trigger}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-800 mb-3">21 classes de classification ML</h2>
        <div className="flex flex-wrap gap-1.5">
          {[
            'Incident réseau DSLAM','Problème CPE client','Authentification RADIUS',
            'Configuration VLAN','Signal DSL / SNR','Provisioning auto',
            'Escalade N3 Transmission','Escalade N3 IP/MPLS','Escalade N3 Accès',
            'Maintenance planifiée','Fausse alarme','Demande de renseignement',
            'Incident critique P1','Incident majeur P2','Incident mineur P3',
            'Changement infra','Restauration service','Surveillance MRT',
            'Analyse CMDB','Qualité de service','Autre',
          ].map((cls, i) => (
            <span key={cls} className="text-xs px-2.5 py-1 rounded-full border font-medium"
              style={{
                background: `hsl(${(i * 17) % 360},65%,95%)`,
                borderColor: `hsl(${(i * 17) % 360},50%,82%)`,
                color: `hsl(${(i * 17) % 360},55%,35%)`,
              }}>
              {cls}
            </span>
          ))}
        </div>
      </div>

      <KnowledgeGraph />

    </div>
  )
}
