"""
Log Parser — Extraction de signatures d'erreur depuis logs/stack traces
Modulaire : chaque stratégie correspond à un type d'application
"""
import re
import hashlib
from typing import List, Optional

from app.schemas.error_signature import ParsedErrorEvent


class LogParser:
    """
    Parser de logs/stack traces modulaire.
    Supporte : java_spring, oracle, network, python, custom
    """

    def parse(
        self,
        raw_input: str,
        app_id: str,
        strategy: str = "custom",
    ) -> ParsedErrorEvent:
        """
        Entrée  : texte brut (log, stack trace, description ticket)
        Sortie  : ParsedErrorEvent structuré
        """
        strategy = strategy.lower()

        event = ParsedErrorEvent(
            app_id=app_id,
            raw_input=raw_input,
            parser_strategy=strategy,
        )

        if strategy == "java_spring":
            self._parse_java_spring(raw_input, event)
        elif strategy == "oracle":
            self._parse_oracle(raw_input, event)
        elif strategy == "python":
            self._parse_python(raw_input, event)
        elif strategy == "network":
            self._parse_network(raw_input, event)
        else:
            self._parse_custom(raw_input, event)

        # Générer le hash de signature pour déduplication
        event.signature_hash = self._compute_hash(event)
        return event

    # ─────────────────────────────────────────────
    # Stratégies de parsing
    # ─────────────────────────────────────────────

    def _parse_java_spring(self, text: str, event: ParsedErrorEvent):
        """Parsing logs Java Spring Boot"""
        # Type d'exception
        exc_match = re.search(
            r'(java\.\w+\.\w+Exception|org\.\w+\.\w+Exception|[A-Z]\w*Exception)',
            text
        )
        if exc_match:
            full = exc_match.group(1)
            event.error_type = full.split(".")[-1]

        # Message d'erreur
        msg_match = re.search(r'Exception[:\s]+(.+?)(?:\n|$)', text)
        if msg_match:
            event.error_message = msg_match.group(1).strip()[:200]

        # Module (classe principale)
        at_match = re.search(r'at\s+([\w.]+)\.([\w$]+)\(', text)
        if at_match:
            class_parts = at_match.group(1).split(".")
            event.module = class_parts[-1] if class_parts else None
            event.method = at_match.group(2)

        # Classes dans la stack trace
        classes = re.findall(r'at\s+([\w.]+)\.\w+\(', text)
        event.affected_classes = list(set(
            c.split(".")[-1] for c in classes
        ))[:10]

        # Stack trace lines (top 5)
        stack_lines = [l.strip() for l in text.split("\n") if l.strip().startswith("at ")]
        event.stack_trace_lines = stack_lines[:5]

        # Keywords de log
        event.log_keywords = self._extract_log_keywords(text)

    def _parse_oracle(self, text: str, event: ParsedErrorEvent):
        """Parsing erreurs Oracle SQL"""
        # Code ORA-XXXXX
        ora_match = re.search(r'ORA-(\d+)', text, re.IGNORECASE)
        if ora_match:
            event.error_type = f"ORA-{ora_match.group(1)}"

        # Message Oracle
        msg_match = re.search(r'ORA-\d+:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if msg_match:
            event.error_message = msg_match.group(1).strip()[:200]

        # Table / procédure impliquée
        table_match = re.search(r'\b(from|into|update|table)\s+(\w+)', text, re.IGNORECASE)
        if table_match:
            event.module = table_match.group(2).upper()

        event.log_keywords = self._extract_log_keywords(text)

    def _parse_python(self, text: str, event: ParsedErrorEvent):
        """Parsing stack traces Python"""
        # Type d'erreur Python
        err_match = re.search(r'(\w+Error|\w+Exception|Traceback).*?:\s*(.+?)(?:\n|$)', text)
        if err_match:
            event.error_type = err_match.group(1)
            event.error_message = err_match.group(2).strip()[:200]

        # Fichier et fonction
        file_match = re.search(r'File "([^"]+)", line \d+, in (\w+)', text)
        if file_match:
            event.module = file_match.group(1).split("/")[-1].replace(".py", "")
            event.method = file_match.group(2)

        # Toutes les frames
        frames = re.findall(r'File "([^"]+)", line \d+, in (\w+)', text)
        event.affected_classes = list(set(
            f[0].split("/")[-1].replace(".py", "") for f in frames
        ))[:10]
        event.stack_trace_lines = [
            f'File "{f[0]}", in {f[1]}' for f in frames[:5]
        ]
        event.log_keywords = self._extract_log_keywords(text)

    def _parse_network(self, text: str, event: ParsedErrorEvent):
        """Parsing erreurs réseau (VLAN, port, équipement)"""
        # Codes d'erreur réseau
        code_match = re.search(r'\b(\d{4})\b', text)
        if code_match:
            event.error_type = f"ERR_{code_match.group(1)}"

        # Équipement (DSLAM, NE, etc.)
        equip_match = re.search(
            r'\b(DSLAM|NE|BAS|ROUTEUR|VLAN|ND|NRO|CARTE|PORT)\b',
            text, re.IGNORECASE
        )
        if equip_match:
            event.module = equip_match.group(1).upper()

        event.log_keywords = self._extract_log_keywords(text)

    def _parse_custom(self, text: str, event: ParsedErrorEvent):
        """Parser générique — tente de détecter les patterns courants"""
        # Essayer chaque stratégie et garder la plus riche
        candidates = []
        for strategy in ["java_spring", "python", "oracle", "network"]:
            candidate = ParsedErrorEvent(
                app_id=event.app_id,
                raw_input=text,
                parser_strategy=strategy,
            )
            getattr(self, f"_parse_{strategy}")(text, candidate)
            richness = len(candidate.affected_classes) + len(candidate.log_keywords)
            if candidate.error_type:
                richness += 5
            candidates.append((richness, candidate))

        if candidates:
            _, best = max(candidates, key=lambda x: x[0])
            event.error_type = best.error_type
            event.error_message = best.error_message
            event.module = best.module
            event.method = best.method
            event.affected_classes = best.affected_classes
            event.stack_trace_lines = best.stack_trace_lines

        event.log_keywords = self._extract_log_keywords(text)

    # ─────────────────────────────────────────────
    # Utilitaires
    # ─────────────────────────────────────────────

    def _extract_log_keywords(self, text: str) -> List[str]:
        """Extrait les mots-clés techniques significatifs"""
        stop_words = {
            "le", "la", "les", "de", "du", "un", "une", "des", "est",
            "sur", "dans", "par", "en", "pour", "avec", "que", "qui",
            "at", "in", "the", "an", "to", "of", "is", "for", "on",
            "com", "org", "java", "net",
        }
        # Extraire mots alphanumériques de longueur 3+
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', text)
        keywords = []
        seen = set()
        for w in words:
            w_lower = w.lower()
            if w_lower not in stop_words and w_lower not in seen:
                seen.add(w_lower)
                keywords.append(w)
            if len(keywords) >= 20:
                break
        return keywords

    def _compute_hash(self, event: ParsedErrorEvent) -> str:
        """Génère un hash stable de la signature pour déduplication"""
        parts = [
            event.app_id or "",
            event.error_type or "",
            event.module or "",
            event.method or "",
        ]
        raw = "|".join(parts).lower()
        return hashlib.md5(raw.encode()).hexdigest()


# Instance globale
log_parser = LogParser()
