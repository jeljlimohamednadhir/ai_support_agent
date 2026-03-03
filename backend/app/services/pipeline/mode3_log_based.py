"""
Pipeline Mode 3 — Log Based
Utilisé quand l'application n'a pas de FR.
Flux : Ticket + Logs + Stack Traces → Parsing → Signature → Cluster → Diagnostic probabiliste
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.app_context import ApplicationContext
from app.models.error_signature import ErrorSignature, SignatureStatus
from app.services.pipeline.log_parser import log_parser
from app.services.trust.trust_engine import trust_engine
from app.schemas.error_signature import ParsedErrorEvent, DiagnosticResult, ProbableCause
from app.core.logging import get_logger

logger = get_logger(__name__)


class LogBasedPipeline:
    """
    Pipeline Mode 3 : Code + Logs Analysis.
    Construit un diagnostic probabiliste depuis tickets + logs + stack traces.
    Pas de FR, pas de procédure canonique → analyse technique pure.
    """

    def __init__(self, app_context: ApplicationContext):
        self.ctx = app_context
        self.parser_strategy = (
            app_context.log_parser_strategy.value
            if app_context.log_parser_strategy
            else "custom"
        )

    async def analyze(
        self,
        query: str,
        db: Session,
        logs: Optional[str] = None,
        stack_trace: Optional[str] = None,
        ticket_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyse complète Mode 3.
        Retourne un diagnostic probabiliste structuré.
        """
        # 1. Agréger les inputs
        raw_input = self._aggregate_inputs(query, logs, stack_trace, ticket_description)

        # 2. Parser → ParsedErrorEvent
        parsed = log_parser.parse(
            raw_input=raw_input,
            app_id=self.ctx.id,
            strategy=self.parser_strategy,
        )

        # 3. Chercher les signatures similaires en DB
        matched_signatures = self._find_similar_signatures(parsed, db)

        # 4. Calculer le score de confiance
        trust = self._compute_trust(parsed, matched_signatures)

        # 5. Construire les causes probables
        probable_causes = self._build_probable_causes(parsed, matched_signatures)

        # 6. Construire les recommandations
        recommended_checks = self._build_recommendations(parsed, matched_signatures)

        # 7. Construire le résultat final
        diagnostic = DiagnosticResult(
            app_id=self.ctx.id,
            parsed_event=parsed,
            matched_signatures=[],  # On ne sérialise pas les ORM objects ici
            probable_causes=probable_causes,
            recommended_checks=recommended_checks,
            diagnostic_strength=trust.score,
            trust_label=trust.label.value,
            summary=self._build_summary(parsed, probable_causes, trust),
            sources=self._build_sources(matched_signatures),
        )

        # 8. Enregistrer / mettre à jour la signature si fréquente
        self._upsert_signature(parsed, matched_signatures, db)

        logger.info(
            f"[Mode3][{self.ctx.id}] Diagnostic: error_type={parsed.error_type}, "
            f"module={parsed.module}, trust={trust.score}/100"
        )

        return {
            "mode": "LOG_BASED",
            "app_id": self.ctx.id,
            "parsed_event": parsed.model_dump(),
            "diagnostic": diagnostic.model_dump(),
            "trust_score": trust,
            "context_blocks": self._build_context_blocks(parsed, matched_signatures, probable_causes, trust),
            "sources": self._build_sources(matched_signatures),
        }

    # ─────────────────────────────────────────────
    # Signature matching
    # ─────────────────────────────────────────────

    def _find_similar_signatures(
        self,
        parsed: ParsedErrorEvent,
        db: Session,
    ) -> List[ErrorSignature]:
        """Cherche les signatures similaires en base"""
        candidates = []

        # Match exact par hash
        exact = db.query(ErrorSignature).filter(
            ErrorSignature.app_id == self.ctx.id,
            ErrorSignature.signature_hash == parsed.signature_hash,
            ErrorSignature.is_active == True,
        ).first()
        if exact:
            candidates.append(exact)
            return candidates  # Match exact trouvé → stop

        # Match par error_type + module
        if parsed.error_type:
            by_type = db.query(ErrorSignature).filter(
                ErrorSignature.app_id == self.ctx.id,
                ErrorSignature.error_type == parsed.error_type,
                ErrorSignature.is_active == True,
            ).order_by(ErrorSignature.frequency.desc()).limit(5).all()
            candidates.extend(by_type)

        # Match par module seul (fallback)
        if not candidates and parsed.module:
            by_module = db.query(ErrorSignature).filter(
                ErrorSignature.app_id == self.ctx.id,
                ErrorSignature.module == parsed.module,
                ErrorSignature.is_active == True,
            ).order_by(ErrorSignature.frequency.desc()).limit(3).all()
            candidates.extend(by_module)

        return candidates

    def _compute_trust(
        self,
        parsed: ParsedErrorEvent,
        matched: List[ErrorSignature],
    ) -> Any:
        """Calcule le score de confiance basé sur les signatures trouvées"""
        if not matched:
            # Aucune signature connue → trust minimal
            return trust_engine.score_raw_ticket(0, False, len(parsed.log_keywords))

        best = matched[0]
        exact_match = (best.signature_hash == parsed.signature_hash)
        logs_coherent = len(parsed.log_keywords) >= 3

        return trust_engine.score_signature_match(
            exact_match=exact_match,
            frequency=best.frequency,
            logs_coherent=logs_coherent,
            stack_trace_stable=len(parsed.stack_trace_lines) > 0,
            cluster_confidence=best.cluster_confidence,
        )

    def _build_probable_causes(
        self,
        parsed: ParsedErrorEvent,
        matched: List[ErrorSignature],
    ) -> List[ProbableCause]:
        """Construit la liste des causes probables avec leur probabilité"""
        causes = []

        for sig in matched:
            if sig.probable_causes:
                for cause_data in sig.probable_causes:
                    if isinstance(cause_data, dict):
                        causes.append(ProbableCause(
                            cause=cause_data.get("cause", ""),
                            probability=cause_data.get("probability", 0.5),
                            evidence=[
                                f"Basé sur {sig.frequency} incidents similaires",
                            ],
                        ))
            elif sig.known_resolution:
                # Pas de causes structurées mais résolution connue
                causes.append(ProbableCause(
                    cause=f"Pattern connu: {sig.error_type or 'erreur'} dans {sig.module or 'module'}",
                    probability=sig.resolution_confidence or 0.5,
                    evidence=[
                        f"Fréquence: {sig.frequency} occurrences",
                        f"Résolution: {sig.known_resolution[:100]}",
                    ],
                ))

        # Si aucune cause depuis la DB → heuristiques depuis le parsing
        if not causes and parsed.error_type:
            causes.append(ProbableCause(
                cause=f"{parsed.error_type} dans {parsed.module or 'module inconnu'}",
                probability=0.4,
                evidence=parsed.log_keywords[:5],
            ))

        # Trier par probabilité décroissante
        return sorted(causes, key=lambda c: c.probability, reverse=True)[:5]

    def _build_recommendations(
        self,
        parsed: ParsedErrorEvent,
        matched: List[ErrorSignature],
    ) -> List[str]:
        """Recommandations de vérification basées sur l'analyse"""
        checks = []

        if parsed.module:
            checks.append(f"Vérifier les logs du module `{parsed.module}`")
        if parsed.error_type:
            checks.append(f"Rechercher les occurrences de `{parsed.error_type}` dans les logs récents")
        if parsed.affected_classes:
            checks.append(f"Analyser les classes impliquées: {', '.join(parsed.affected_classes[:3])}")
        if matched:
            best = matched[0]
            if best.known_resolution:
                checks.append(f"Procédure connue: {best.known_resolution[:150]}")
            checks.append(f"Consulter l'historique: {best.frequency} incidents similaires répertoriés")

        checks.append("Vérifier l'état des dépendances de l'application")
        checks.append("Contrôler les logs des dernières 2 heures")

        return checks[:7]

    def _build_summary(
        self,
        parsed: ParsedErrorEvent,
        causes: List[ProbableCause],
        trust: Any,
    ) -> str:
        parts = []

        if parsed.error_type:
            parts.append(f"Erreur détectée : **{parsed.error_type}**")
        if parsed.module:
            parts.append(f"Module : `{parsed.module}`")
            if parsed.method:
                parts.append(f"Méthode : `{parsed.method}`")

        if causes:
            top = causes[0]
            pct = int(top.probability * 100)
            parts.append(f"\nHypothèse principale ({pct}% de probabilité) : {top.cause}")

        parts.append(f"\nForce du diagnostic : **{trust.score}/100** ({trust.label.value.upper()})")
        parts.append(f"_{trust.explanation}_")

        return "\n".join(parts)

    def _build_context_blocks(
        self,
        parsed: ParsedErrorEvent,
        matched: List[ErrorSignature],
        causes: List[ProbableCause],
        trust: Any,
    ) -> List[Dict]:
        blocks = []

        # Bloc parsing
        blocks.append({
            "type": "parsed_error",
            "title": "🔍 Analyse technique",
            "trust_badge": f"⚙️ MODE 3 — LOG BASED ({trust.score}/100)",
            "trust_score": trust.score,
            "trust_label": trust.label.value,
            "content": self._format_parsed_event(parsed),
        })

        # Bloc historique
        if matched:
            freq_total = sum(s.frequency for s in matched)
            blocks.append({
                "type": "signature_history",
                "title": "📊 Historique interne",
                "trust_badge": "📈 DONNÉES HISTORIQUES",
                "trust_score": trust.score,
                "trust_label": trust.label.value,
                "content": self._format_history(matched, freq_total),
            })

        # Bloc causes probables
        if causes:
            blocks.append({
                "type": "probable_causes",
                "title": "🎯 Causes probables",
                "trust_badge": "",
                "trust_score": trust.score,
                "trust_label": trust.label.value,
                "content": self._format_causes(causes),
            })

        return blocks

    def _build_sources(self, matched: List[ErrorSignature]) -> List[Dict]:
        return [
            {
                "id": sig.id,
                "type": "error_signature",
                "error_type": sig.error_type,
                "module": sig.module,
                "frequency": sig.frequency,
                "trust_score": int((sig.confidence_score or 0) * 100),
                "status": sig.status.value,
            }
            for sig in matched
        ]

    def _upsert_signature(
        self,
        parsed: ParsedErrorEvent,
        matched: List[ErrorSignature],
        db: Session,
    ):
        """Met à jour la fréquence ou crée une nouvelle signature"""
        try:
            from datetime import datetime
            import uuid

            if matched and matched[0].signature_hash == parsed.signature_hash:
                # Incrémenter fréquence
                matched[0].frequency += 1
                matched[0].last_seen_at = datetime.utcnow()
                db.commit()
            elif not matched:
                # Créer nouvelle signature
                new_sig = ErrorSignature(
                    id=f"{self.ctx.id.lower()}_{parsed.signature_hash[:16]}",
                    app_id=self.ctx.id,
                    signature_hash=parsed.signature_hash,
                    error_type=parsed.error_type,
                    module=parsed.module,
                    method=parsed.method,
                    error_message_pattern=parsed.error_message,
                    log_keywords=parsed.log_keywords,
                    stack_trace_pattern="\n".join(parsed.stack_trace_lines),
                    affected_classes=parsed.affected_classes,
                    frequency=1,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow(),
                    status=SignatureStatus.RAW,
                    confidence_score=0.0,
                )
                db.add(new_sig)
                db.commit()
        except Exception as e:
            logger.warning(f"[Mode3] Erreur upsert signature: {e}")
            db.rollback()

    # ─────────────────────────────────────────────
    # Formatage
    # ─────────────────────────────────────────────

    def _aggregate_inputs(self, *parts) -> str:
        return "\n\n".join(p for p in parts if p)

    def _format_parsed_event(self, parsed: ParsedErrorEvent) -> str:
        lines = []
        if parsed.error_type:
            lines.append(f"**Type d'erreur:** `{parsed.error_type}`")
        if parsed.module:
            lines.append(f"**Module:** `{parsed.module}`")
            if parsed.method:
                lines.append(f"**Méthode:** `{parsed.method}`")
        if parsed.error_message:
            lines.append(f"**Message:** {parsed.error_message}")
        if parsed.log_keywords:
            lines.append(f"**Mots-clés détectés:** {', '.join(parsed.log_keywords[:8])}")
        if parsed.affected_classes:
            lines.append(f"**Classes impliquées:** {', '.join(parsed.affected_classes[:5])}")
        if parsed.stack_trace_lines:
            lines.append("\n**Stack trace (top):**")
            lines.extend(f"  `{l}`" for l in parsed.stack_trace_lines[:3])
        return "\n".join(lines)

    def _format_history(self, matched: List[ErrorSignature], total_freq: int) -> str:
        lines = [f"**{total_freq} incidents similaires répertoriés**\n"]
        for sig in matched[:3]:
            lines.append(f"- Signature `{sig.error_type or 'N/A'}` dans `{sig.module or 'N/A'}`")
            lines.append(f"  → {sig.frequency} occurrences")
            if sig.known_resolution:
                lines.append(f"  → Résolution connue: {sig.known_resolution[:100]}")
        return "\n".join(lines)

    def _format_causes(self, causes: List[ProbableCause]) -> str:
        lines = []
        for i, cause in enumerate(causes, 1):
            pct = int(cause.probability * 100)
            lines.append(f"**{i}. {cause.cause}** ({pct}%)")
            if cause.evidence:
                for ev in cause.evidence[:2]:
                    lines.append(f"   - {ev}")
        return "\n".join(lines)
