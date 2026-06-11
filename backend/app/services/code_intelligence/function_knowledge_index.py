"""
function_knowledge_index.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Keyword-based function knowledge index over the execution graph.

Complements brasil_extractor.py (exception-centric) with:
- Search by operation name, entity, log keyword, table name
- Forensic context blocks for chatbot/explainability injection
- No ML dependencies — pure in-memory keyword index

Usage:
    from app.services.code_intelligence.function_knowledge_index import function_knowledge_index
    results = function_knowledge_index.search("delete dslam constraint")
    context = function_knowledge_index.forensic_block("constraint bloquante", "Dslam", max_chars=800)
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from .extractors.execution_graph_extractor import ExecutionNode, get_execution_graph

logger = logging.getLogger(__name__)


# ── Token weights (for ranking) ──────────────────────────────────────────────

_LAYER_WEIGHT = {
    "validator": 4,
    "service":   3,
    "business":  2,
    "repository": 1,
    "controller": 1,
}

_OP_SYNONYMS = {
    "supprimer":  "delete",
    "suppression": "delete",
    "suppr":      "delete",
    "effacer":    "delete",
    "créer":      "create",
    "création":   "create",
    "creer":      "create",
    "modifier":   "modify",
    "modification": "modify",
    "bloquer":    "validate",
    "bloquant":   "validate",
    "bloqué":     "validate",
    "vérifier":   "validate",
    "contrôle":   "validate",
    "contraint":  "validate",
    "contrainte": "validate",
    "lien":       "check_mrt",
    "liens":      "check_mrt",
    "rollback":   "rollback",
    "annuler":    "rollback",
    "synchroniser": "sync",
    "sync":       "sync",
    "connecter":  "connect",
    "connexion":  "connect",
    "provisionner": "provision",
    "provisioning": "provision",
    "activer":    "activate",
    "activation": "activate",
    "désactiver": "deactivate",
    "migrer":     "migrate",
    "migration":  "migrate",
    "rejouer":    "replay",
    "relancer":   "replay",
    "compteur":   "counter",
    "toc":        "counter",
    "chercher":   "search",
    "recherche":  "search",
}

_ENTITY_SYNONYMS = {
    "équipement": "dslam",
    "equipement": "dslam",
    "noeud":      "dslam",
    "node":       "dslam",
    "carte":      "card",
    "vlan":       "vlan",
    "interface":  "vlaninterface",
    "lien":       "mrt",
    "port":       "port",
}


def _normalize_tokens(text: str) -> List[str]:
    """Lowercase, French synonym expansion, tokenize."""
    tokens = re.findall(r'[a-zéèàùâêîôûç]+', text.lower())
    normalized = []
    for t in tokens:
        normalized.append(_OP_SYNONYMS.get(t, t))
        normalized.append(_ENTITY_SYNONYMS.get(t, t))
    return list(set(normalized))


def _score_node(node: ExecutionNode, tokens: List[str]) -> int:
    """Score an execution node against query tokens."""
    score = 0
    node_text = (
        f"{node.class_name} {node.method_name} {node.entity} {node.operation} "
        f"{' '.join(node.exceptions_thrown)} {' '.join(node.sql_tables)} "
        f"{' '.join(node.blocking_conditions)} {' '.join(node.log_patterns)}"
    ).lower()

    for tok in tokens:
        if tok in node_text:
            # Higher score for more specific fields
            if tok in node.method_name.lower():
                score += 5
            elif tok in node.entity.lower():
                score += 4
            elif any(tok in e.lower() for e in node.exceptions_thrown):
                score += 3
            elif any(tok in b.lower() for b in node.blocking_conditions):
                score += 3
            elif tok in node.operation:
                score += 2
            else:
                score += 1

    # Bonus for service/validator layer (more relevant for forensics)
    score += _LAYER_WEIGHT.get(node.node_type, 0)

    return score


class FunctionKnowledgeIndex:
    """
    Keyword search index over the execution graph.
    Thread-safe (read-only after init).
    """

    def search(
        self,
        query: str,
        entity: Optional[str] = None,
        operation: Optional[str] = None,
        max_results: int = 6,
        min_score: int = 2,
    ) -> List[Tuple[ExecutionNode, int]]:
        """
        Search execution nodes by natural-language query.

        Args:
            query:       Free-text query (French or English)
            entity:      Optional entity filter (e.g. "Dslam")
            operation:   Optional operation filter (e.g. "delete")
            max_results: Max nodes to return
            min_score:   Minimum relevance score to include

        Returns:
            List of (ExecutionNode, score) sorted by score descending
        """
        graph = get_execution_graph()
        if not graph.nodes:
            return []

        tokens = _normalize_tokens(query)
        if entity:
            tokens.append(entity.lower())
        if operation:
            tokens.append(operation.lower())

        # Score all nodes
        scored: List[Tuple[ExecutionNode, int]] = []
        for node in graph.nodes.values():
            score = _score_node(node, tokens)
            if score >= min_score:
                scored.append((node, score))

        scored.sort(key=lambda x: -x[1])
        return scored[:max_results]

    def forensic_block(
        self,
        query: str,
        entity: Optional[str] = None,
        max_chars: int = 800,
    ) -> str:
        """
        Returns a bounded LLM-safe forensic context block.

        Example output:
            [SOURCE CODE]
            DslamDeletionValidator.validate | op=validate | throws=[DslamStillActivException] | [DslamDeletionValidator.java:45]
            DslamServiceImpl.deleteDslam | op=delete | throws=[TechnicalException] | tables=[t_dslam] | [DslamServiceImpl.java:120]
        """
        results = self.search(query, entity=entity, max_results=5)
        if not results:
            return ""

        lines = ["[SOURCE CODE]"]
        for node, score in results:
            lines.append(f"  {node.to_summary()}")
            if node.blocking_conditions:
                for cond in node.blocking_conditions[:2]:
                    lines.append(f"    ⚠ {cond[:90]}")

        text = "\n".join(lines)
        return text[:max_chars]

    def get_exception_source(self, exception_class: str) -> Optional[str]:
        """
        Find the primary source method that throws a given exception class.
        Returns a one-line summary for forensic context.
        """
        graph = get_execution_graph()
        nodes = graph.find_nodes_by_exception(exception_class)
        if not nodes:
            return None
        # Prefer validators/services
        nodes.sort(key=lambda n: _LAYER_WEIGHT.get(n.node_type, 0), reverse=True)
        node = nodes[0]
        loc = node.code_location
        file_short = loc.get("file", "?").split("\\")[-1].split("/")[-1] if loc else "?"
        return (
            f"`{node.node_id}` [{file_short}:{loc.get('line', '?')}] "
            f"→ throws `{exception_class}`"
            + (f" — condition: {node.blocking_conditions[0][:80]}" if node.blocking_conditions else "")
        )

    def get_table_access_chain(self, table: str) -> str:
        """
        Returns which service methods access a given SQL table.
        Useful for forensic DB state queries.
        """
        graph = get_execution_graph()
        nodes = graph.find_nodes_by_table(table)
        if not nodes:
            return ""
        lines = [f"[TABLE `{table}`]"]
        for node in nodes[:5]:
            lines.append(f"  {node.node_type.upper()}: `{node.node_id}` op={node.operation}")
        return "\n".join(lines)


# Singleton
function_knowledge_index = FunctionKnowledgeIndex()
