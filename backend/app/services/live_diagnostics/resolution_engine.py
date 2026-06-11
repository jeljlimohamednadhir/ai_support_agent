"""
resolution_engine.py
━━━━━━━━━━━━━━━━━━━━
Deterministic resolution engine.

Maps:
  root_cause  ->  ranked list of FR-based resolution actions

Resolution sources (by priority):
  1. LIVE_DB evidence  (highest trust)
  2. LIVE_LOG evidence
  3. SSH evidence
  4. CODE evidence (Phase 2)
  5. SFD constraints
  6. FR structured knowledge (always present)
  7. Incident history

No LLM decision allowed.
The LLM only formats the structured output AFTER resolution is complete.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.live_diagnostics.models.evidence import (
    DbEvidence,
    DiagnosticBundle,
    EvidenceType,
    EVIDENCE_WEIGHTS,
    LogEvidence,
    SshEvidence,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Resolution rule registry
# Maps root_cause -> resolution procedure
# ─────────────────────────────────────────────────────────────────────────────

RESOLUTION_RULES: Dict[str, Dict[str, Any]] = {

    "equipment_has_residual_data": {
        "fr_id":      "FR-DSLAM-DELETION-189",
        "confidence": 0.97,
        "steps": [
            "Identifier les tables avec des données résiduelles via les requêtes de diagnostic",
            "Libérer les services actifs liés à l'équipement (t_services)",
            "Supprimer les liens MRT résiduels (t_mrtdslam)",
            "Supprimer les cartes résiduelles (t_cards)",
            "Relancer la suppression depuis l'IHM BRASIL",
        ],
        "sql_hints": [
            "SELECT * FROM t_services WHERE eqpt_id = <eqpt_id> AND svc_status NOT IN ('C','S');",
            "SELECT * FROM t_mrtdslam WHERE eqpt_id = <eqpt_id>;",
        ],
        "tags": ["delete_equipment", "residual_data"],
    },

    "equipment_closed_to_production": {
        "fr_id":      "FR-NOEUD-IP-ABSENT-1300",
        "confidence": 0.95,
        "steps": [
            "Vérifier le statut de l'équipement : eqpt_status doit être différent de 'F'",
            "Consulter les logs pour la contrainte ConstraintViolationException",
            "Rouvrir l'équipement si justifié (procédure métier)",
        ],
        "sql_hints": [
            "SELECT eqpt_status FROM t_equipments WHERE eqpt_name = '<equipment>';",
        ],
        "tags": ["delete_equipment", "error_1300"],
    },

    "vlan_residual_resources": {
        "fr_id":      "FR-VLAN-DELETION-190",
        "confidence": 0.96,
        "steps": [
            "Identifier les ressources résiduelles dans t_res_prod_controlables",
            "Identifier les ressources dans t_d_controlable_rscs",
            "Libérer toutes les ressources logiques VP/VLAN/VC liées au VLAN",
            "Relancer la suppression du VLAN depuis l'IHM BRASIL",
        ],
        "sql_hints": [
            "SELECT * FROM t_res_prod_controlables WHERE vlan_id = <vlan_id>;",
            "SELECT * FROM t_d_controlable_rscs WHERE vlan_id = <vlan_id>;",
        ],
        "tags": ["delete_vlan", "residual_data"],
    },

    "tp_blocked_status_1": {
        "fr_id":      "FR-TP-ETAT-MODIFICATION-176",
        "confidence": 0.97,
        "steps": [
            "Identifier le TP bloqué via : SELECT * FROM t_tps WHERE tp_dslam_n='<DSLAM>' AND tp_status='1'",
            "Récupérer le tp_id",
            "Modifier l'état : UPDATE t_tps SET tp_status='5' WHERE tp_id='<tp_id>'",
            "Vérifier les ND du TP : SELECT * FROM t_tp_initial_states WHERE tp_id='<tp_id>'",
            "Vérifier l'IHM BRASIL après correction",
        ],
        "sql_hints": [
            "SELECT * FROM t_tps WHERE tp_dslam_n='<DSLAM>' AND tp_status='1';",
            "UPDATE t_tps SET tp_status='5' WHERE tp_status='1' AND tp_id='<tp_id>';",
        ],
        "tags": ["fix_blocked_tp"],
    },

    "vc_counters_incorrect": {
        "fr_id":      "FR-VC-OCCUPATION-135",
        "confidence": 0.94,
        "steps": [
            "Identifier les VC occupés à tort via check_vc_counters",
            "Libérer les VC incorrectement occupés",
            "Réinitialiser les compteurs de ressources logiques",
        ],
        "tags": ["fix_vc_counters", "counters"],
    },

    "port_shared_between_links": {
        "fr_id":      "FR-PORT-RESEAU-SANS-SERVICE-114",
        "confidence": 0.95,
        "steps": [
            "Identifier les DSLAM partageant un même b_port_id via la requête de détection",
            "Récupérer les liens en BDD pour le couple de DSLAM incriminé",
            "Identifier le port_id correct via SELECT port_num, port_id FROM t_ports WHERE card_id=<id>",
            "Corriger : UPDATE t_media_links SET b_port_id=<port_id_correct> WHERE mdlk_id=<mdlk_id>",
        ],
        "tags": ["fix_port_assignment", "shared_port"],
    },

    "charset_anomaly_t_remarks": {
        "fr_id":      "FR-BRASIL-CHARS-077",
        "confidence": 0.90,
        "steps": [
            "Exécuter la requête de détection des caractères non-ASCII dans t_ports.t_remarks",
            "Appliquer le script de correction SQL : Correction t_ports.t_remarks.sql",
            "Relancer l'intégration Thoutmosis",
        ],
        "tags": ["fix_port_remarks", "charset"],
    },

    "dlm_blocked": {
        "fr_id":      "FR-DLM-RECOVERY-101",
        "confidence": 0.93,
        "steps": [
            "Identifier les DLM bloqués (dlm_status='E') via check_blocked_dlm",
            "Analyser la cause du blocage pour chaque DLM",
            "Appliquer la procédure de reprise DLM selon la FR-DLM-RECOVERY-101",
        ],
        "tags": ["fix_blocked_dlm"],
    },

    "ihm_blocked_dsm_param": {
        "fr_id":      "FR-IHM-BLOQUEE-DSM-PARAM-182",
        "confidence": 0.95,
        "steps": [
            "Se connecter sur le serveur DSM PARAM via SSH",
            "Exécuter who -T pour identifier la session bloquée venant de dv49mwb31",
            "Exécuter ps -ft pts/<N> pour trouver le PID bloqué",
            "Tuer le process : kill -9 <PID>",
            "Vérifier la disponibilité de l'IHM BRASIL DSM PARAM",
        ],
        "tags": ["fix_ihm_blocked"],
    },

    "bas_residual_data": {
        "fr_id":      "FR-BAS-DELETION-188",
        "confidence": 0.96,
        "steps": [
            "Identifier les données résiduelles via check_bas_residual_data",
            "Libérer les services, MRT et VLANs liés au BAS/ROUTER",
            "Relancer la suppression depuis l'IHM BRASIL",
        ],
        "tags": ["delete_bas"],
    },

    "operator_has_mrt_links": {
        "fr_id":      "FR-OPERATOR-DELETION-192",
        "confidence": 0.96,
        "steps": [
            "Vérifier les liens MRT de l'opérateur : check_operator_mrt_links",
            "Libérer ou supprimer les liens MRT associés avant la suppression",
            "Relancer la suppression de l'opérateur",
        ],
        "tags": ["delete_operator"],
    },

    "card_deletion_blocked": {
        "fr_id":      "FR-CARTE-SUPPRESSION-165",
        "confidence": 0.93,
        "steps": [
            "CAS 1 (Ressources résiduelles) : Vérifier t_mrtdslam, t_port_groups, t_res_prod_controlables",
            "CAS 2 (FTTH) : Via IHM BRASIL, mettre le champ 'restriction carte' à 'aucun' pour tous les services",
            "Relancer la suppression de la carte",
        ],
        "tags": ["delete_card"],
    },

    "generic_missing_data": {
        "fr_id":      None,
        "confidence": 0.50,
        "steps": [
            "Analyser les données résiduelles dans la base BRASIL",
            "Consulter les logs d'erreur de l'application",
            "Contacter le support N3 si le problème persiste",
        ],
        "tags": [],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Resolution candidate
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ResolutionCandidate:
    root_cause:  str
    fr_id:       Optional[str]
    steps:       List[str]
    sql_hints:   List[str]
    confidence:  float
    sources:     List[str]   # evidence types that triggered this candidate
    tags:        List[str]
    rank:        int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_cause": self.root_cause,
            "fr_id":      self.fr_id,
            "steps":      self.steps,
            "sql_hints":  self.sql_hints,
            "confidence": round(self.confidence, 3),
            "sources":    self.sources,
            "tags":       self.tags,
            "rank":       self.rank,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Resolution Engine
# ─────────────────────────────────────────────────────────────────────────────

class ResolutionEngine:
    """
    Maps evidence -> ranked resolution candidates.

    Algorithm:
      1. Read all evidence from DiagnosticBundle
      2. Match evidence patterns to root_cause keys
      3. Load resolution rule for each root_cause
      4. Boost confidence based on evidence trust weight
      5. Return ranked candidates (highest confidence first)
    """

    def __init__(self, fr_data_path: str | None = None):
        self._fr_cache: Dict[str, Dict] = {}
        if fr_data_path:
            self._load_fr_cache(fr_data_path)

    def _load_fr_cache(self, path: str) -> None:
        try:
            frs = json.loads(Path(path).read_text(encoding="utf-8"))
            for fr in frs:
                self._fr_cache[fr.get("id", "")] = fr
            logger.info(f"[ResolutionEngine] Loaded {len(self._fr_cache)} FRs from {path}")
        except Exception as e:
            logger.warning(f"[ResolutionEngine] Could not load FR cache: {e}")

    def resolve(
        self,
        bundle: DiagnosticBundle,
        normalized_db: Dict[str, Dict[str, Any]] | None = None,
    ) -> List[ResolutionCandidate]:
        """
        Produce ranked resolution candidates from a DiagnosticBundle.
        """
        candidates: List[ResolutionCandidate] = []
        normalized_db = normalized_db or {}

        # ── DB evidence routing ───────────────────────────────────────────────
        for qname, ev in bundle.db_evidence.items():
            norm = normalized_db.get(qname, {})

            if qname == "check_residual_references" and norm.get("has_residuals"):
                c = self._make_candidate(
                    "equipment_has_residual_data",
                    sources=["live_db"],
                    boost=0.02,
                )
                if c:
                    candidates.append(c)

            elif qname == "check_active_services" and norm.get("has_active_services"):
                c = self._make_candidate(
                    "equipment_has_residual_data",
                    sources=["live_db"],
                    boost=0.01,
                )
                if c:
                    candidates.append(c)

            elif qname == "check_vlan_residual_resources" and ev.has_data:
                c = self._make_candidate("vlan_residual_resources", sources=["live_db"])
                if c:
                    candidates.append(c)

            elif qname == "get_blocked_tps" and norm.get("has_blocked_tp"):
                c = self._make_candidate("tp_blocked_status_1", sources=["live_db"])
                if c:
                    candidates.append(c)

            elif qname == "check_vc_counters" and norm.get("has_occupied_vc"):
                c = self._make_candidate("vc_counters_incorrect", sources=["live_db"])
                if c:
                    candidates.append(c)

            elif qname == "check_shared_port_links" and norm.get("has_shared_ports"):
                c = self._make_candidate("port_shared_between_links", sources=["live_db"])
                if c:
                    candidates.append(c)

            elif qname == "check_port_remarks_anomaly" and ev.has_data:
                c = self._make_candidate("charset_anomaly_t_remarks", sources=["live_db"])
                if c:
                    candidates.append(c)

            elif qname == "check_blocked_dlm" and ev.has_data:
                c = self._make_candidate("dlm_blocked", sources=["live_db"])
                if c:
                    candidates.append(c)

            elif qname == "check_bas_residual_data" and ev.has_data:
                c = self._make_candidate("bas_residual_data", sources=["live_db"])
                if c:
                    candidates.append(c)

            elif qname == "check_operator_mrt_links" and ev.has_data:
                c = self._make_candidate("operator_has_mrt_links", sources=["live_db"])
                if c:
                    candidates.append(c)

        # ── Log evidence routing ──────────────────────────────────────────────
        for log_ev in bundle.log_evidence:
            for code in log_ev.error_codes:
                if code == "1300":
                    c = self._make_candidate(
                        "equipment_closed_to_production",
                        sources=["live_log"],
                        boost=0.03,
                    )
                    if c:
                        candidates.append(c)

        # ── SSH evidence routing ──────────────────────────────────────────────
        for ssh_ev in bundle.ssh_evidence:
            if "DSM PARAM" in ssh_ev.command_name or "ihm" in ssh_ev.command_name.lower():
                c = self._make_candidate("ihm_blocked_dsm_param", sources=["ssh"])
                if c:
                    candidates.append(c)

        # ── Intent-based fallback ─────────────────────────────────────────────
        intent_fallbacks = {
            "delete_equipment": "equipment_has_residual_data",
            "delete_vlan":      "vlan_residual_resources",
            "fix_blocked_tp":   "tp_blocked_status_1",
            "fix_ihm_blocked":  "ihm_blocked_dsm_param",
            "delete_bas":       "bas_residual_data",
            "delete_operator":  "operator_has_mrt_links",
            "delete_card":      "card_deletion_blocked",
        }
        fb_root = intent_fallbacks.get(bundle.intent)
        logger.debug(f"[ResolutionEngine] Intent: {bundle.intent}, Fallback Root Cause: {fb_root}")
        if fb_root:
            logger.debug(f"[ResolutionEngine] Checking fallback for intent: {bundle.intent}, root cause: {fb_root}")
            # Add only if not already in candidates and passes similarity threshold
            existing = {c.root_cause for c in candidates}
            logger.debug(f"[ResolutionEngine] Existing candidates: {existing}")
            if fb_root not in existing:
                if self._validate_causal_relevance(bundle, fb_root):
                    logger.debug(f"[ResolutionEngine] Adding fallback candidate for root cause: {fb_root}")
                    c = self._make_candidate(fb_root, sources=["intent_fallback"], boost=-0.10)
                    if c and c.confidence >= 0.5:  # Apply similarity threshold
                        candidates.append(c)
                        logger.debug(f"[ResolutionEngine] Fallback candidate added: {c}")
                else:
                    logger.debug(f"[ResolutionEngine] Fallback root cause {fb_root} failed causal relevance validation.")

        # ── Deduplicate + rank ────────────────────────────────────────────────
        candidates = self._deduplicate(candidates)
        logger.debug(f"[ResolutionEngine] Candidates after deduplication: {candidates}")
        candidates.sort(key=lambda x: (x.confidence, x.sources[0] if x.sources else "", x.root_cause), reverse=True)
        for i, c in enumerate(candidates):
            c.rank = i + 1

        logger.info(
            f"[ResolutionEngine] {len(candidates)} candidate(s) for intent={bundle.intent}"
        )
        return candidates

    def _make_candidate(
        self,
        root_cause: str,
        sources:    List[str],
        boost:      float = 0.0,
    ) -> Optional[ResolutionCandidate]:
        rule = RESOLUTION_RULES.get(root_cause)
        if not rule:
            return None

        confidence = min(1.0, rule["confidence"] + boost)

        # Boost from FR cache if available
        fr_id = rule.get("fr_id")
        fr_resolution_steps = []
        if fr_id and fr_id in self._fr_cache:
            fr = self._fr_cache[fr_id]
            fr_resolution_steps = fr.get("resolution_steps", []) or [
                a.get("action", "") for a in fr.get("resolution", [])
            ]

        steps = fr_resolution_steps or rule.get("steps", [])

        return ResolutionCandidate(
            root_cause=root_cause,
            fr_id=fr_id,
            steps=steps,
            sql_hints=rule.get("sql_hints", []),
            confidence=confidence,
            sources=sources,
            tags=rule.get("tags", []),
        )

    @staticmethod
    def _deduplicate(
        candidates: List[ResolutionCandidate],
    ) -> List[ResolutionCandidate]:
        """Keep highest-confidence candidate per root_cause."""
        seen: Dict[str, ResolutionCandidate] = {}
        for c in candidates:
            if c.root_cause not in seen or c.confidence > seen[c.root_cause].confidence:
                seen[c.root_cause] = c
        return list(seen.values())

    def can_execute_resolution(
        self,
        candidate: ResolutionCandidate,
        bundle: DiagnosticBundle,
    ) -> bool:
        """
        Safety check: can this resolution be executed?
        Returns False if any evidence contradicts the resolution.
        """
        # Never execute resolution if DB evidence shows active services still present
        if candidate.root_cause == "equipment_has_residual_data":
            active_svc = bundle.db_evidence.get("check_active_services")
            if active_svc and active_svc.has_data:
                logger.warning(
                    "[ResolutionEngine] Active services still present — "
                    "deletion blocked until services are closed."
                )
                return False
        return True

    def to_context_blocks(
        self,
        candidates: List[ResolutionCandidate],
        entity: Optional[str] = None,
        eqpt_id: Optional[str] = None,
        runtime_capabilities: Optional[Dict[str, bool]] = None,
    ) -> List[Dict[str, Any]]:
        """Convert resolution candidates to chatbot context_blocks.

        Args:
            candidates: scored resolution candidates
            entity:     equipment name (e.g. DSROB362) — substituted into SQL placeholders
            eqpt_id:    numeric equipment ID from DB — substituted into SQL placeholders
            runtime_capabilities: availability flags (e.g. ssh/db/logs/mq)
        """
        capabilities = {
            "ssh_available": True,
            "db_available": True,
            "logs_available": True,
            "mq_available": True,
        }
        if runtime_capabilities:
            capabilities.update({k: bool(v) for k, v in runtime_capabilities.items()})

        def _sub(text: str) -> str:
            """Replace generic placeholders with real values when available."""
            if entity:
                text = text.replace("<equipment>", entity)
                text = text.replace("<DSLAM>", entity)
                text = text.replace("<entity>", entity)
            if eqpt_id is not None:
                text = text.replace("<eqpt_id>", str(eqpt_id))
            return text

        def _is_step_runtime_supported(step_text: str) -> bool:
            lower_step = step_text.lower()
            if (not capabilities["ssh_available"]) and any(
                token in lower_step
                for token in (
                    "ssh",
                    "who -t",
                    "ps -ft",
                    "kill -9",
                    "serveur",
                )
            ):
                return False

            if (not capabilities["logs_available"]) and any(
                token in lower_step for token in ("log", "grep", "tomcat", "trace")
            ):
                return False

            if (not capabilities["db_available"]) and any(
                token in lower_step
                for token in (
                    "sql",
                    "requête",
                    "select ",
                    "update ",
                    "insert ",
                    "delete ",
                    "t_",
                )
            ):
                return False

            if (not capabilities["mq_available"]) and any(
                token in lower_step for token in ("mq", "broker", "dlq", "ack")
            ):
                return False
            return True

        def _is_generic_operational_filler(step_text: str) -> bool:
            lower_step = step_text.lower().strip()
            filler_patterns = (
                "vérifier les logs",
                "verifier les logs",
                "check logs",
                "consulter les logs",
                "analyser les logs",
                "identifier la cause",
                "investiguer le problème",
                "relancer et vérifier",
            )
            concrete_tokens = (
                "fr-",
                "select ",
                "update ",
                "delete ",
                "insert ",
                "t_",
                "code ",
                "constraint",
                "eqpt",
                "vlan",
                "tp",
                "dsm",
                "mq",
                "dlq",
                "broker",
                "who -t",
                "ps -ft",
                "kill -9",
            )
            return any(p in lower_step for p in filler_patterns) and not any(
                t in lower_step for t in concrete_tokens
            )

        def _is_step_evidence_backed(step_text: str, source_set: set[str]) -> bool:
            lower_step = step_text.lower()
            if any(t in lower_step for t in ("log", "grep", "tomcat", "trace")):
                if "live_log" not in source_set:
                    return False
            if any(t in lower_step for t in ("sql", "select ", "update ", "insert ", "delete ", "t_")):
                if "live_db" not in source_set:
                    return False
            if any(t in lower_step for t in ("ssh", "who -t", "ps -ft", "kill -9")):
                if "ssh" not in source_set:
                    return False
            return True

        blocks = []
        for c in candidates[:3]:   # top 3 only
            source_set = set(c.sources or [])
            filtered_steps = [
                s
                for s in c.steps
                if _is_step_runtime_supported(s)
                and _is_step_evidence_backed(s, source_set)
                and not _is_generic_operational_filler(s)
            ]
            if not filtered_steps:
                filtered_steps = [
                    "Actions opérationnelles limitées: certaines capacités runtime requises ne sont pas disponibles."
                ]

            steps_text = "\n".join(f"  {i+1}. {_sub(s)}" for i, s in enumerate(filtered_steps))
            # Only include SQL hints if they contain real values (no unresolved placeholders left)
            _sql_allowed = capabilities["db_available"]
            resolved_hints = [_sub(h) for h in c.sql_hints] if (_sql_allowed and c.sql_hints) else []
            # Flag whether any placeholder remains unresolved — if so, omit from user-facing output
            _has_unresolved = any(
                tok in h for h in resolved_hints for tok in ("<eqpt_id>", "<equipment>", "<DSLAM>", "<vlan_id>", "<tp_id>")
            )
            content = f"**Procédure de résolution ({c.fr_id or 'N/A'}):**\n{steps_text}"
            if resolved_hints and not _has_unresolved:
                sql_text = "\n".join(resolved_hints)
                content += f"\n\n**Requêtes SQL de référence:**\n{sql_text}"

            blocks.append({
                "title":       f"Résolution: {c.root_cause.replace('_', ' ').title()}",
                "content":     content,
                "trust_score": round(c.confidence * 100),
                "source_type": "resolution_engine",
                "type":        "procedure",
                "fr_id":       c.fr_id,
                "sources":     c.sources,
                # Keep raw hints for the follow-up evidence bubble (always with real IDs)
                "sql_hints_raw": resolved_hints,
                "sql_resolved":  _sql_allowed and bool(resolved_hints) and (not _has_unresolved),
                "runtime_capabilities": capabilities,
            })
        return blocks

    def _validate_causal_relevance(self, bundle, root_cause):
        """Validate that the fallback root cause is supported by fresh evidence."""
        logger.debug(
            "[ResolutionEngine] Validating causal relevance for root_cause=%s",
            root_cause,
        )

        db_evidence = getattr(bundle, "db_evidence", None) or {}
        log_evidence = getattr(bundle, "log_evidence", None) or {}

        evidence = None
        if isinstance(db_evidence, dict):
            evidence = db_evidence.get(root_cause)
        if not evidence and isinstance(log_evidence, dict):
            evidence = log_evidence.get(root_cause)

        if not evidence:
            logger.warning(
                "[ResolutionEngine] Missing evidence for root_cause=%s",
                root_cause,
            )
            return False

        if not isinstance(evidence, dict):
            logger.warning(
                "[ResolutionEngine] Unsupported evidence type for root_cause=%s: %s",
                root_cause,
                type(evidence).__name__,
            )
            return False

        evidence_time = evidence.get("timestamp")
        if evidence_time is None:
            logger.warning(
                "[ResolutionEngine] Missing timestamp for root_cause=%s",
                root_cause,
            )
            return False

        if isinstance(evidence_time, str):
            raw_timestamp = evidence_time.strip()
            try:
                evidence_time = datetime.fromisoformat(
                    raw_timestamp.replace("Z", "+00:00")
                )
            except ValueError:
                logger.warning(
                    "[ResolutionEngine] Invalid timestamp format for root_cause=%s: %s",
                    root_cause,
                    raw_timestamp,
                )
                return False

        if not isinstance(evidence_time, datetime):
            logger.warning(
                "[ResolutionEngine] Non-datetime timestamp for root_cause=%s: %s",
                root_cause,
                type(evidence_time).__name__,
            )
            return False

        now = (
            datetime.now(tz=evidence_time.tzinfo)
            if evidence_time.tzinfo is not None
            else datetime.now()
        )
        age_seconds = (now - evidence_time).total_seconds()

        if age_seconds < 0:
            logger.warning(
                "[ResolutionEngine] Future timestamp detected for root_cause=%s",
                root_cause,
            )
            return False

        max_age_seconds = 3600
        if age_seconds > max_age_seconds:
            logger.info(
                "[ResolutionEngine] Stale evidence for root_cause=%s (age=%ss)",
                root_cause,
                int(age_seconds),
            )
            return False

        return True
