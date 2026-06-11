"""
Layer 5 — Correlation Engine
==============================
Multi-source evidence correlation for N3-level BRASIL diagnostics.

Sources (in priority order):
  1. INCIDENTS — historical patterns (semantic + keyword)
  2. FR documents — procedures and known errors
  3. Logs — error patterns
  4. SFD — constraint violations
  5. Diagnostic rules — pre-built DIAG rules

Input:
  - user query + ConversationState
  - retrieved knowledge blocks (from vector store / RAG)
  - existing log patterns
  - diagnostic rules

Output: CorrelationResult with ranked hypotheses, root cause, evidence trail.

JIRA: NEVER used for correlation or response generation.
"""
from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from app.services.chatbot.conversation_state import ConversationState, EntityType
from app.services.chatbot.sfd_parser import sfd_parser
from app.services.chatbot.incident_graph import incident_graph, GraphReasoning


# ─────────────────────────────────────────────────────────────────────────────
# Evidence & Hypothesis
# ─────────────────────────────────────────────────────────────────────────────

SOURCE_INCIDENT  = "incident"
SOURCE_FR        = "fr_document"
SOURCE_LOG       = "log_pattern"
SOURCE_SFD       = "sfd_constraint"
SOURCE_DIAG_RULE = "diagnostic_rule"
SOURCE_BRASIL_KB = "brasil_knowledge_base"
SOURCE_LEARNED   = "learned_pattern"

# ── Truth Hierarchy Source Weights ────────────────────────────────────────────
# SFD and FR documents are authoritative ground truth.
# Learned patterns are valuable but MUST NEVER outrank SFD.
# LEARNED weight is dynamic (function of pattern score) and capped at 1.2 < SFD.
SOURCE_WEIGHT: Dict[str, float] = {
    SOURCE_SFD:       1.5,   # ① Highest authority: normative SFD documents
    SOURCE_FR:        1.3,   # ② Procedure manuals
    SOURCE_INCIDENT:  1.0,   # ③ Historical incidents (baseline)
    SOURCE_LEARNED:   1.0,   # ④ Learned: base — dynamically adjusted below (max 1.2)
    SOURCE_LOG:       0.85,  # ⑤ Log patterns
    SOURCE_DIAG_RULE: 0.80,  # ⑥ Diagnostic rules
    SOURCE_BRASIL_KB: 0.70,  # ⑦ General KB
}

# LEARNED weight cap — must always be below SFD (1.5) to prevent override
_LEARNED_WEIGHT_MAX = 1.2
_LEARNED_WEIGHT_MIN = 0.7


def _dynamic_learned_weight(pattern_score: float) -> float:
    """
    Compute a dynamic source weight for a learned pattern based on its
    anti-bias score (0–1 from LearningLoop.compute_pattern_score).

    Maps score [0, 1] → weight [0.7, 1.2].
    Guarantees: weight is ALWAYS strictly below SOURCE_WEIGHT[SOURCE_SFD] = 1.5.
    """
    clamped = max(0.0, min(1.0, pattern_score))
    weight = _LEARNED_WEIGHT_MIN + clamped * (_LEARNED_WEIGHT_MAX - _LEARNED_WEIGHT_MIN)
    return round(min(weight, _LEARNED_WEIGHT_MAX), 4)


@dataclass
class CorrelationEvidence:
    source_type: str
    snippet: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationHypothesis:
    id: str
    label: str
    confidence: float
    evidence: List[CorrelationEvidence] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    root_cause: str = ""
    related_entities: List[str] = field(default_factory=list)
    related_constraints: List[str] = field(default_factory=list)

    @property
    def supporting_sources(self) -> List[str]:
        return list({e.source_type for e in self.evidence})

    @property
    def is_multi_source(self) -> bool:
        return len(self.supporting_sources) >= 2

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "confidence": round(self.confidence, 3),
            "root_cause": self.root_cause,
            "recommended_actions": self.recommended_actions,
            "related_entities": self.related_entities,
            "related_constraints": self.related_constraints,
            "supporting_sources": self.supporting_sources,
            "evidence_count": len(self.evidence),
        }


@dataclass
class CorrelationResult:
    query: str
    hypotheses: List[CorrelationHypothesis] = field(default_factory=list)
    top_hypothesis: Optional[CorrelationHypothesis] = None
    sfd_violations: List[str] = field(default_factory=list)
    context_entities: List[str] = field(default_factory=list)
    confidence: float = 0.0
    graph_reasoning: Optional[GraphReasoning] = None  # UPGRADE: causal graph

    def to_context_block(self) -> str:
        """Compact LLM-injectable context block — now includes causal chain."""
        lines = ["## CORRELATION ANALYSIS"]
        if self.top_hypothesis:
            h = self.top_hypothesis
            lines.append(f"### Top Hypothesis: {h.label} (confidence={h.confidence:.0%})")
            lines.append(f"Root cause: {h.root_cause}")
            if h.recommended_actions:
                lines.append("Recommended actions:")
                for a in h.recommended_actions[:5]:
                    lines.append(f"  - {a}")
            if h.related_constraints:
                lines.append(f"Constraints: {', '.join(h.related_constraints[:3])}")
            lines.append(f"Sources: {', '.join(h.supporting_sources)}")

        # UPGRADE: causal graph reasoning
        if self.graph_reasoning and self.graph_reasoning.root_cause:
            gr = self.graph_reasoning
            lines.append("\n### CAUSAL CHAIN (graph-based):")
            lines.append(f"Root cause: {gr.root_cause.label}")
            if gr.blocking_constraints:
                lines.append("Blocking SFD rules:")
                for c in gr.blocking_constraints[:2]:
                    lines.append(f"  - [{c.metadata.get('rule_id','')}] {c.label}")
            if gr.fr_references:
                lines.append(f"FR references: {', '.join(gr.fr_references[:3])}")

        if self.sfd_violations:
            lines.append("### ⚠️ SFD VIOLATIONS:")
            for v in self.sfd_violations[:3]:
                lines.append(f"  - {v}")

        if len(self.hypotheses) > 1:
            lines.append(f"### Other hypotheses ({len(self.hypotheses) - 1}):")
            for h in self.hypotheses[1:4]:
                lines.append(f"  - {h.label} ({h.confidence:.0%})")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Signal patterns for hypothesis building
# ─────────────────────────────────────────────────────────────────────────────

_HYPOTHESES_CATALOG: List[Dict] = [
    {
        "id": "HYP-001",
        "label": "DSLAM fermé à la production",
        "patterns": [r"ferm[eé]\s+(à|a)\s+la\s+production", r"closed\s+for\s+production", r"prod_status.*fermé"],
        "root_cause": "Le DSLAM cible est fermé à la production (eqpt_prod_status='F')",
        "entities": ["DSLAM"],
        "constraints": ["CSTR-FR-001"],
        "actions": [
            "Vérifier eqpt_prod_status dans t_equipments",
            "Ouvrir le DSLAM via IHM BRASIL si autorisé",
            "Vérifier statut dans Orchestra NE Repository",
            "Contrôler s'il y a un ticket de maintenance actif",
        ],
    },
    {
        "id": "HYP-002",
        "label": "Aucun port disponible (TOC 100%)",
        "patterns": [r"no\s+port\s+found", r"no\s+port\s+available", r"recherche\s+broche.*[eé]chec", r"toc\s*=?\s*100", r"aucune\s+broche"],
        "root_cause": "Tous les ports du DSLAM sont saturés ou le champ port_attribuable est incorrectement à 0",
        "entities": ["DSLAM", "PORT", "CARD"],
        "constraints": ["CSTR-FR-007", "CSTR-SQL-005"],
        "actions": [
            "Lancer CalculerToc.ksh (FR 001) pour mesurer le TOC réel",
            "Vérifier port_attribuable dans t_ports",
            "Contrôler dxcd_auto_available_port_count dans t_d_dslam_xdsl_cards",
            "Appliquer procédure FR 1583B si compteurs suspects",
        ],
    },
    {
        "id": "HYP-003",
        "label": "Carte fermée à la production",
        "patterns": [r"cart[e]?\s+ferm[eé]e?\s+(à|a)\s+la\s+production", r"card.*closed.*production"],
        "root_cause": "Une carte du DSLAM est fermée (card_prod_status='F')",
        "entities": ["CARD", "PORT"],
        "constraints": ["CSTR-FR-002"],
        "actions": [
            "Vérifier card_prod_status dans t_cards pour la carte cible",
            "Identifier les cartes alternatives disponibles",
            "Ouvrir la carte si la maintenance est terminée",
        ],
    },
    {
        "id": "HYP-004",
        "label": "MRT introuvable ou inconnu",
        "patterns": [r"mrt.*inconnu", r"aucune\s+mrt", r"mrt.*not\s+found", r"identifiant.*macro.*ressource.*inconnu"],
        "root_cause": "L'identifiant MRT est absent de t_mrt_access_dslams ou a été supprimé",
        "entities": ["MRT", "DSLAM"],
        "constraints": ["CSTR-FR-005"],
        "actions": [
            "SELECT * FROM t_mrt_access_dslams WHERE mrtd_id=<ID>",
            "Vérifier si une migration de données a eu lieu",
            "Comparer avec le référentiel BRASIL/SEBA",
            "Recréer le MRT si absent via procédure admin",
        ],
    },
    {
        "id": "HYP-005",
        "label": "Dossier de réalisation inconnu",
        "patterns": [r"dossier.*r[eé]alisation.*inconnu", r"nifolderid", r"erreur\s*1002", r"making.*file.*unknown"],
        "root_cause": "L'ID du dossier de réalisation est absent ou le champ NIFolderID est manquant",
        "entities": ["MAKING_FILE", "EPC"],
        "constraints": ["CSTR-FR-006", "CSTR-FR-014"],
        "actions": [
            "SELECT * FROM t_making_files WHERE mkfl_file_id='<ID>'",
            "Vérifier le format du message UMI-EPC (NIFolderID présent)",
            "Appliquer procédure FR 012",
        ],
    },
    {
        "id": "HYP-006",
        "label": "CCL manquant pour offre CEV",
        "patterns": [r"numeroccl.*obligatoire", r"ccl.*cev", r"offre\s+cev.*ccl"],
        "root_cause": "Le NumeroCCL est obligatoire pour les offres CEV et est absent de la commande",
        "entities": ["CCL", "MAKING_FILE"],
        "constraints": ["CSTR-FR-003"],
        "actions": [
            "Vérifier rpct_ccl_name dans t_res_prod_controlables",
            "Confirmer le type d'offre (CEV/GE)",
            "Corriger le message de commande pour inclure NumeroCCL",
        ],
    },
    {
        "id": "HYP-007",
        "label": "Deadlock base de données",
        "patterns": [r"deadlock", r"verrou.*mort", r"lock.*acquisition", r"pgsql.*deadlock"],
        "root_cause": "Transactions concurrentes sur le même DSLAM causent un deadlock PostgreSQL",
        "entities": ["MAKING_FILE", "PORT"],
        "constraints": ["CSTR-FR-010"],
        "actions": [
            "Le système effectue 3 tentatives automatiques avec 55s de délai",
            "Vérifier pg_locks pour sessions bloquantes",
            "Surveiller t_making_files pour commandes bloquées après deadlock",
            "Réduire le parallélisme si problème récurrent",
        ],
    },
    {
        "id": "HYP-008",
        "label": "Compteurs VP/VC/VLAN incorrects",
        "patterns": [r"compteur.*incorrect", r"vc.*occup[eé]\s+à\s+tort", r"vlan.*occup[eé]\s+à\s+tort", r"counter.*mismatch"],
        "root_cause": "Les compteurs de ressources logiques ne reflètent pas l'état réel",
        "entities": ["CCL", "VLAN", "VP_VC"],
        "constraints": ["CSTR-FR-013"],
        "actions": [
            "Appliquer FR 136b (Libérer ports occupés à tort)",
            "Appliquer FR 136c (Correction compteurs VP/VLAN/VC)",
            "Recalculer les compteurs via script N3",
        ],
    },
    {
        "id": "HYP-009",
        "label": "Modification concurrente en cours",
        "patterns": [r"en\s+cours\s+de\s+modification", r"accès.*déjà.*modification", r"dossier\s+en\s+cours", r"concurrent.*modification"],
        "root_cause": "Un autre dossier de réalisation est déjà en cours de traitement pour ce ND/EPC",
        "entities": ["MAKING_FILE", "EPC", "MRT"],
        "constraints": ["CSTR-FR-008"],
        "actions": [
            "Attendre la fin du dossier en cours avant de réessayer",
            "SELECT * FROM t_making_files WHERE mkfl_nd='<ND>' AND mkfl_status='IN_PROGRESS'",
            "Vérifier si un deadlock a laissé un dossier bloqué",
        ],
    },
    {
        "id": "HYP-010",
        "label": "Suppression d'équipement bloquée (dépendances)",
        "patterns": [r"supprimer.*[eé]quipement", r"delete.*equipment", r"suppression.*dslam", r"ne\s+peut\s+pas\s+supprimer"],
        "root_cause": "L'équipement ne peut pas être supprimé car des CARTES ou SERVICES y sont encore rattachés",
        "entities": ["EQUIPMENT", "DSLAM", "CARD"],
        "constraints": ["CSTR-SQL-001", "CSTR-SQL-002"],
        "actions": [
            "Vérifier les cartes associées: SELECT * FROM t_cards WHERE eqpt_id=<ID>",
            "Vérifier les ports actifs: SELECT * FROM t_ports WHERE card_id IN (...)",
            "Désaffecter tous les services actifs avant suppression",
            "Fermer le DSLAM à la production en premier",
            "Valider avec Orchestra que le NE est décommissionné",
        ],
    },
    {
        "id": "HYP-011",
        "label": "Nœud absent ou non synchronisé",
        "patterns": [r"nœud.*absent", r"node.*absent", r"r[eé]f[eé]rentiel.*sites.*absent", r"nœud.*n.?exist"],
        "root_cause": "Le nœud existe dans le Référentiel Sites mais est absent de BRASIL",
        "entities": ["NODE"],
        "constraints": ["CSTR-FR-012"],
        "actions": [
            "Appliquer FR 148/FR 151 (Contrôler nœud Brasil vs Référentiel Sites)",
            "Créer le nœud dans BRASIL si absent",
            "Vérifier code42C et DR code",
        ],
    },
    {
        "id": "HYP-012",
        "label": "Ressources TSF indisponibles",
        "patterns": [r"tech.*service.*function.*not\s+found", r"tsf.*resources.*not.*found", r"brasili?nternaler?ror"],
        "root_cause": "Les fonctions de service technique (TSF) ne sont pas provisionnées sur ce DSLAM",
        "entities": ["TSF", "CCL", "DSLAM"],
        "constraints": ["CSTR-FR-019"],
        "actions": [
            "Vérifier t_d_rsc_dslam_tsfs pour le DSLAM cible",
            "Contrôler t_res_prod_controlables status pour le CCL lié",
            "Appliquer procédure FR 137 (routage ressources logiques)",
        ],
    },
]

# Pre-compile patterns
for _h in _HYPOTHESES_CATALOG:
    _h["_compiled"] = [re.compile(p, re.I) for p in _h["patterns"]]


def _text_score(text: str, patterns: List[re.Pattern]) -> float:
    """Simple scoring: ratio of matching patterns."""
    if not patterns:
        return 0.0
    hits = sum(1 for p in patterns if p.search(text))
    return hits / len(patterns)


# ─────────────────────────────────────────────────────────────────────────────
# Correlation Engine
# ─────────────────────────────────────────────────────────────────────────────

class CorrelationEngine:
    """
    Multi-source correlation engine.

    Processes:
      1. User query + conversation context
      2. Retrieved knowledge blocks (incidents, FR, logs)
      3. Diagnostic rules from brasil_diagnostic_rules.json
      4. SFD constraints
    """

    def __init__(self):
        self._diagnostic_rules: Optional[List[Dict]] = None
        self._structured_frs: Optional[List[Dict]] = None

    # ── Structured FR helpers ──────────────────────────────────────────────

    def _load_structured_frs(self) -> List[Dict]:
        """Lazy-load brasil_fr_structured.json produced by fr_structurer.py."""
        if self._structured_frs is not None:
            return self._structured_frs
        path = (
            __import__("pathlib").Path(__file__).parents[3]
            / "data" / "brasil_fr_structured.json"
        )
        if path.exists():
            try:
                self._structured_frs = __import__("json").loads(
                    path.read_text(encoding="utf-8")
                )
            except Exception:
                self._structured_frs = []
        else:
            self._structured_frs = []
        return self._structured_frs

    # Intent keyword mapping — maps structured intent names to user-facing French tokens
    _INTENT_KEYWORDS: Dict[str, List[str]] = {
        "delete_equipment":  ["supprim", "effac", "retir", "enlev", "supprimer"],
        "update_service":    ["modif", "chang", "mis à jour", "update", "changer"],
        "diagnose":          ["diagn", "analys", "vérif", "probl", "erreur", "panne"],
        "check_status":      ["état", "status", "vérif", "check", "consulter"],
        "install":           ["install", "déploy", "configur", "paramét"],
        "transfer":          ["transfer", "migr", "déplac", "mover"],
        "reset":             ["reset", "réinit", "redémarr", "reboot"],
    }

    def _match_structured_fr(
        self,
        combined_text: str,
        top: Optional[CorrelationHypothesis],
    ) -> List[CorrelationEvidence]:
        """
        Score structured FRs against the combined query+KB text.
        Returns up to 3 evidence items from the best-matching FRs.
        Returns an empty list if brasil_fr_structured.json is not present.
        """
        frs = self._load_structured_frs()
        if not frs:
            return []

        scored: List[tuple[float, Dict]] = []
        text_lower = combined_text.lower()
        for fr in frs:
            score = 0.0

            # 1. trigger_signals — exact phrase match on real user wording (highest signal)
            for signal in fr.get("trigger_signals", []):
                sig = signal.lower()
                if sig in text_lower:
                    score += 0.35  # exact phrase match
                elif any(w in text_lower for w in sig.split() if len(w) > 4):
                    score += 0.12  # partial word match

            # 2. intents — map structured intent to French user tokens
            for intent in fr.get("intents", []):
                kws = self._INTENT_KEYWORDS.get(intent, [intent.replace("_", " ")])
                for kw in kws:
                    if kw in text_lower:
                        score += 0.20
                        break  # one hit per intent is enough

            # 3. evidence_tags — technical terms in query
            for tag in fr.get("evidence_tags", []):
                if str(tag).lower() in text_lower:
                    score += 0.15

            # 4. entities — EQUIPMENT type gets boosted
            for ent in fr.get("entities", []):
                boost = 0.25 if ent.get("type") == "EQUIPMENT" else 0.10
                for ex in ent.get("examples", []):
                    if str(ex).lower() in text_lower:
                        score += boost

            # 5. symptoms text — partial word match
            for sym in fr.get("symptoms", []):
                sym_text = sym.get("text", "").lower()
                if any(w in text_lower for w in sym_text.split() if len(w) > 4):
                    score += 0.10

            # 6. pattern_signature — each segment
            sig = fr.get("pattern_signature", "")
            if sig:
                for segment in sig.split("|"):
                    seg = segment.lower().replace("_", " ")
                    if len(seg) > 3 and seg in text_lower:
                        score += 0.08

            # 7. title significant words
            title_words = [w for w in fr.get("title", "").lower().split() if len(w) > 4]
            title_hits = sum(1 for w in title_words if w in text_lower)
            score += title_hits * 0.06

            if score > 0.08:  # lowered threshold (was implicitly ~0.1+)
                scored.append((score, fr))

        scored.sort(key=lambda x: x[0], reverse=True)
        evidence: List[CorrelationEvidence] = []
        for score, fr in scored[:3]:
            # Build snippet from first diagnostic step
            diag_steps = fr.get("diagnostic", [])
            snippet = diag_steps[0].get("step", fr.get("title", ""))[:180] if diag_steps else fr.get("title", "")
            conf = min(score * SOURCE_WEIGHT[SOURCE_FR], 1.0)

            # If structured FR root_cause matches top hypothesis class, boost
            rc_class = fr.get("root_cause", {}).get("class", "")
            if top and rc_class:
                conf = min(conf + 0.1, 1.0)

            evidence.append(CorrelationEvidence(
                source_type=SOURCE_FR,
                snippet=f"[{fr.get('id', '')}] {fr.get('title', '')}: {snippet}",
                confidence=conf,
                metadata={
                    "fr_id":      fr.get("id", ""),
                    "fr_title":   fr.get("title", ""),
                    "rc_class":   rc_class,
                    "rc_label":   fr.get("root_cause", {}).get("label", ""),
                    "sfd_rules":  [r.get("rule", "") for r in fr.get("sfd_rules", [])[:2]],
                    "resolution": [r.get("action", "") for r in fr.get("resolution", [])[:3]],
                    "source_file": fr.get("_source_file", ""),
                },
            ))
        return evidence

    def correlate(
        self,
        query: str,
        state: ConversationState,
        kb_blocks: Optional[List[Dict]] = None,
        incident_blocks: Optional[List[Dict]] = None,
        log_patterns: Optional[List[Dict]] = None,
        intent: str = "",
    ) -> CorrelationResult:

        kb_blocks = kb_blocks or []
        incident_blocks = incident_blocks or []
        log_patterns = log_patterns or []

        # Build combined text corpus for scoring
        combined_text = query + " "
        combined_text += " ".join(b.get("content", "") + " " + b.get("text", "") for b in kb_blocks)
        combined_text += " ".join(b.get("content", "") + " " + b.get("description", "") for b in incident_blocks)
        combined_text += " ".join(b.get("error_type", "") + " " + b.get("pattern_regex", "") for b in log_patterns)

        # Add entity context
        entities_str = " ".join(e.name for e in state.entities.values())
        combined_text += " " + entities_str

        # ── Score each hypothesis ──────────────────────────────────────────
        hypotheses: List[CorrelationHypothesis] = []
        for hdata in _HYPOTHESES_CATALOG:
            base_score = _text_score(combined_text, hdata["_compiled"])
            if base_score < 0.05:
                continue

            evidence_list: List[CorrelationEvidence] = []

            # Evidence from KB blocks (includes learned blocks injected by knowledge_layer)
            for block in kb_blocks:
                block_text = block.get("content", block.get("text", ""))
                s = _text_score(block_text, hdata["_compiled"])
                if s > 0:
                    is_learned = block.get("_source") == "learned"
                    src_type = SOURCE_LEARNED if is_learned else (
                        SOURCE_INCIDENT if block.get("source") == "incident" else SOURCE_FR
                    )
                    # For LEARNED blocks, use dynamic weight capped at 1.2 (below SFD=1.5)
                    if is_learned:
                        pattern_score = block.get("_computed_score", 0.5)
                        src_weight = _dynamic_learned_weight(pattern_score)
                    else:
                        src_weight = SOURCE_WEIGHT.get(src_type, 1.0)
                    # Learned blocks matching hypothesis get a direct confidence boost
                    hyp_match_bonus = (
                        0.25 if is_learned and block.get("hypothesis_id") == hdata["id"] else 0.0
                    )
                    evidence_list.append(CorrelationEvidence(
                        source_type=src_type,
                        snippet=block_text[:150],
                        confidence=s * src_weight + hyp_match_bonus,
                        metadata={"source_id": block.get("id", ""), "learned": is_learned},
                    ))

            # Evidence from log patterns
            for lp in log_patterns:
                lp_text = lp.get("error_type", "") + " " + lp.get("pattern_regex", "")
                s = _text_score(lp_text, hdata["_compiled"])
                if s > 0:
                    evidence_list.append(CorrelationEvidence(
                        source_type=SOURCE_LOG,
                        snippet=lp_text[:100],
                        confidence=s * SOURCE_WEIGHT[SOURCE_LOG],
                        metadata={"log_id": lp.get("id", "")},
                    ))

            # Evidence from SFD constraints
            sfd_constraints = sfd_parser.get_all_constraints()
            for cstr_id in hdata.get("related_constraints", hdata.get("constraints", [])):
                matching = [c for c in sfd_constraints if c.rule_id == cstr_id]
                if matching:
                    evidence_list.append(CorrelationEvidence(
                        source_type=SOURCE_SFD,
                        snippet=matching[0].description[:100],
                        confidence=SOURCE_WEIGHT[SOURCE_SFD],
                        metadata={"constraint_id": cstr_id},
                    ))

            # Boost if entity match
            entity_boost = 0.0
            for ent_name in hdata.get("entities", []):
                if any(e.name.upper() == ent_name.upper() or e.type.value == ent_name for e in state.entities.values()):
                    entity_boost += 0.1

            # Combined confidence
            if evidence_list:
                confidence = min(1.0, base_score + entity_boost + (len(evidence_list) * 0.05))
            else:
                confidence = min(0.7, base_score + entity_boost)

            hypotheses.append(CorrelationHypothesis(
                id=hdata["id"],
                label=hdata["label"],
                confidence=confidence,
                evidence=evidence_list,
                recommended_actions=hdata.get("actions", []),
                root_cause=hdata.get("root_cause", ""),
                related_entities=hdata.get("entities", []),
                related_constraints=hdata.get("constraints", hdata.get("related_constraints", [])),
            ))

        # Sort by confidence descending
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)

        # ── Enrich top hypothesis with structured FR evidence ─────────────
        top_before_learning = hypotheses[0] if hypotheses else None
        fr_evidence = self._match_structured_fr(combined_text, top_before_learning)
        if fr_evidence and top_before_learning:
            for ev in fr_evidence:
                top_before_learning.evidence.append(ev)
            # Re-calculate confidence with FR boost
            top_before_learning.confidence = min(
                1.0,
                top_before_learning.confidence + len(fr_evidence) * 0.04,
            )

        # ── LEARNING: Apply suppression from repeated bug suggestions ────────
        try:
            from app.services.chatbot.learning_loop import learning_loop  # deferred
            suppressed = learning_loop.get_suppressed_hypotheses(threshold=3)
            for h in hypotheses:
                if h.id in suppressed:
                    h.confidence = max(0.0, h.confidence + suppressed[h.id])

            # Also apply graph-level suppression (persisted weights)
            for h in hypotheses:
                graph_suppression = incident_graph.get_node_suppression(h.id)
                if graph_suppression < 0:
                    h.confidence = max(0.0, h.confidence + graph_suppression)

            # Re-sort after suppression
            hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        except Exception:
            pass

        # Check SFD violations for requested operation
        sfd_violations: List[str] = []
        if intent in ("delete_equipment", "delete"):
            primary = state.get_primary_equipment()
            if primary:
                valid, reason = sfd_parser.validate_operation("DELETE", primary.name)
                if not valid:
                    sfd_violations.append(f"SFD violation: {reason}")

        top = hypotheses[0] if hypotheses else None

        # ── UPGRADE: Graph-based causal reasoning ─────────────────────────
        entity_names = [e.name for e in state.entities.values()]
        graph_reasoning = incident_graph.reason(
            query=query,
            hypothesis_id=top.id if top else None,
            entity_names=entity_names,
        )

        # Boost top hypothesis confidence if graph corroborates it
        if top and graph_reasoning.root_cause and graph_reasoning.confidence > 0:
            top.confidence = min(1.0, top.confidence + graph_reasoning.confidence * 0.15)

        result = CorrelationResult(
            query=query,
            hypotheses=hypotheses,
            top_hypothesis=top,
            sfd_violations=sfd_violations,
            context_entities=list(state.entities.keys()),
            confidence=top.confidence if top else 0.0,
            graph_reasoning=graph_reasoning,
        )
        return result

    def _load_diagnostic_rules(self) -> List[Dict]:
        """Lazy-load brasil_diagnostic_rules.json."""
        if self._diagnostic_rules is not None:
            return self._diagnostic_rules
        rules_path = (
            __import__("pathlib").Path(__file__).parents[3] / "data" / "brasil_diagnostic_rules.json"
        )
        if rules_path.exists():
            try:
                data = __import__("json").loads(rules_path.read_text(encoding="utf-8"))
                self._diagnostic_rules = data.get("rules", [])
            except Exception:
                self._diagnostic_rules = []
        else:
            self._diagnostic_rules = []
        return self._diagnostic_rules

    # ─────────────────────────────────────────────────────────────────────────
    # LIVE DIAGNOSTIC EVIDENCE FUSION
    # Weighted truth hierarchy:
    #   LIVE_DB (100) > LIVE_LOG (90) > SSH (85) > CODE (80) >
    #   SFD (70) > FR (60) > INCIDENT (50) > LEARNED (30)
    # ─────────────────────────────────────────────────────────────────────────

    def fuse_live_evidence(
        self,
        result: "CorrelationResult",
        diagnostic_bundle: "object | None",
    ) -> "CorrelationResult":
        """
        Fuse live diagnostic evidence (DB / Log / SSH / Code) into
        an existing CorrelationResult.

        The live evidence has higher trust than KB-derived evidence,
        so it is prepended to the context_blocks and boosts confidence.

        Parameters
        ----------
        result           : existing CorrelationResult from correlate()
        diagnostic_bundle: DiagnosticBundle from LiveDiagnosticOrchestrator.run()
                           (None if live diagnostics are disabled)
        """
        if diagnostic_bundle is None:
            return result

        try:
            # Convert bundle evidence to context blocks
            live_blocks = diagnostic_bundle.to_context_blocks()

            # Resolution blocks (highest trust — go first)
            resolution_blocks = diagnostic_bundle.reasoning_trace.get("resolution_blocks", [])

            # Merge: resolution > live_db/log/ssh > existing KB blocks
            existing = result.context_blocks or []
            result.context_blocks = resolution_blocks + live_blocks + existing

            # Boost confidence if strong live evidence found
            highest = diagnostic_bundle.highest_confidence()
            if highest > 0.8:
                result.confidence = min(1.0, result.confidence + 0.05)

            # Inject evidence types into result for debug/trace
            ev_types = set()
            for ev in diagnostic_bundle.all_evidence():
                ev_types.add(ev.evidence_type.value if hasattr(ev.evidence_type, "value") else str(ev.evidence_type))
            if ev_types:
                result.graph_reasoning = (result.graph_reasoning or []) + [
                    f"[LiveDiag] Evidence types fused: {', '.join(sorted(ev_types))}",
                    f"[LiveDiag] Highest confidence: {highest:.2f}",
                ]

        except Exception as e:
            import logging as _log
            _log.getLogger(__name__).warning(f"[CorrelationEngine] Evidence fusion failed: {e}")

        return result


# Singleton
correlation_engine = CorrelationEngine()
