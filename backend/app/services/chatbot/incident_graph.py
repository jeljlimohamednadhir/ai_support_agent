"""
Incident Graph — Causal Reasoning Engine
==========================================
Replaces flat hypothesis scoring with a directed causal graph.

Graph structure:
  Nodes: symptom | entity | cause | action | constraint
  Edges: causes | blocks | requires | resolves | related_to
  Weights: confidence [0.0–1.0]

Capabilities:
  - Link incidents into causal chains
  - Detect recurring root causes across sessions
  - Traverse graph to explain reasoning step-by-step
  - Merge learned patterns into the graph

Example causal chain:
  [SYMPTOM] DSLAM deletion fails
    ─causes─► [CAUSE] Active cards still attached
      ─blocks─► [CAUSE] FK constraint violation on t_cards
        ─requires─► [ACTION] Detach all services
          ─resolves─► [SYMPTOM] DSLAM deletion fails

This module is STATELESS per-query but ACCUMULATES learned edges
across sessions via the learning loop.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple, Any

# ─────────────────────────────────────────────────────────────────────────────
# Node & Edge types
# ─────────────────────────────────────────────────────────────────────────────

NODE_SYMPTOM    = "symptom"
NODE_ENTITY     = "entity"
NODE_CAUSE      = "cause"
NODE_ACTION     = "action"
NODE_CONSTRAINT = "constraint"

EDGE_CAUSES     = "causes"
EDGE_BLOCKS     = "blocks"
EDGE_REQUIRES   = "requires"
EDGE_RESOLVES   = "resolves"
EDGE_RELATED    = "related_to"
EDGE_TRIGGERS   = "triggers"
EDGE_DEPENDS_ON = "depends_on"


@dataclass
class GraphNode:
    id: str
    node_type: str          # NODE_* constant
    label: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    visit_count: int = 0    # how many times this node appeared in incidents

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, GraphNode) and self.id == other.id


@dataclass
class GraphEdge:
    from_id: str
    to_id: str
    edge_type: str          # EDGE_* constant
    weight: float = 1.0     # confidence / strength
    fr_reference: str = ""  # FR number backing this edge
    evidence_count: int = 1 # how many incidents support this edge

    @property
    def id(self) -> str:
        return f"{self.from_id}--{self.edge_type}--{self.to_id}"


@dataclass
class CausalChainStep:
    node: GraphNode
    edge_from_parent: Optional[GraphEdge]
    depth: int

    def explain(self) -> str:
        if self.edge_from_parent is None:
            return f"[{self.node.node_type.upper()}] {self.node.label}"
        rel = self.edge_from_parent.edge_type.replace("_", " ")
        fr = f" (ref: {self.edge_from_parent.fr_reference})" if self.edge_from_parent.fr_reference else ""
        indent = "  " * self.depth
        return f"{indent}─{rel}─► [{self.node.node_type.upper()}] {self.node.label}{fr}"


@dataclass
class GraphReasoning:
    """Full reasoning output from a graph traversal."""
    root_symptom: GraphNode
    causal_chain: List[CausalChainStep]
    root_cause: Optional[GraphNode]
    blocking_constraints: List[GraphNode]
    recommended_actions: List[GraphNode]
    confidence: float
    explanation: str
    fr_references: List[str]

    def to_dict(self) -> dict:
        return {
            "root_symptom": self.root_symptom.label,
            "root_cause": self.root_cause.label if self.root_cause else None,
            "blocking_constraints": [n.label for n in self.blocking_constraints],
            "recommended_actions": [n.label for n in self.recommended_actions],
            "confidence": round(self.confidence, 3),
            "explanation": self.explanation,
            "fr_references": self.fr_references,
            "chain_length": len(self.causal_chain),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Built-in BRASIL causal knowledge graph
# ─────────────────────────────────────────────────────────────────────────────

# Node registry
_NODES: List[Dict] = [
    # ── Symptoms ──────────────────────────────────────────────────────────────
    {"id": "S-001", "type": NODE_SYMPTOM,    "label": "Suppression équipement échoue",
     "desc": "L'opération de suppression d'un DSLAM/MSAN est rejetée par BRASIL"},
    {"id": "S-002", "type": NODE_SYMPTOM,    "label": "Aucun port disponible",
     "desc": "La recherche de broche ne retourne aucun résultat disponible (TOC=100%)"},
    {"id": "S-003", "type": NODE_SYMPTOM,    "label": "Commande bloquée en attente",
     "desc": "Un dossier de réalisation reste en statut IN_PROGRESS indéfiniment"},
    {"id": "S-004", "type": NODE_SYMPTOM,    "label": "MRT introuvable",
     "desc": "L'identifiant MRT est absent de t_mrt_access_dslams"},
    {"id": "S-005", "type": NODE_SYMPTOM,    "label": "Dossier réalisation inconnu",
     "desc": "NIFolderID absent ou invalide dans message UMI-EPC"},
    {"id": "S-006", "type": NODE_SYMPTOM,    "label": "Erreur deadlock PostgreSQL",
     "desc": "Transactions concurrentes provoquent un verrou mort"},
    {"id": "S-007", "type": NODE_SYMPTOM,    "label": "Compteurs VP/VC/VLAN incorrects",
     "desc": "Compteurs divergent de l'état réel de la base"},
    {"id": "S-008", "type": NODE_SYMPTOM,    "label": "TSF resources not found",
     "desc": "Les fonctions de service technique ne sont pas provisionnées"},
    {"id": "S-009", "type": NODE_SYMPTOM,    "label": "DSLAM fermé à la production",
     "desc": "eqpt_prod_status='F', aucune opération possible"},
    {"id": "S-010", "type": NODE_SYMPTOM,    "label": "Nœud absent du référentiel",
     "desc": "Node présent dans Référentiel Sites mais absent BRASIL"},

    # ── Entities ──────────────────────────────────────────────────────────────
    {"id": "E-001", "type": NODE_ENTITY,     "label": "DSLAM",
     "desc": "Digital Subscriber Line Access Multiplexer — équipement cible"},
    {"id": "E-002", "type": NODE_ENTITY,     "label": "CARD (T-CARD)",
     "desc": "Carte réseau rattachée au DSLAM"},
    {"id": "E-003", "type": NODE_ENTITY,     "label": "PORT",
     "desc": "Port physique ou logique de la carte"},
    {"id": "E-004", "type": NODE_ENTITY,     "label": "MRT",
     "desc": "Macro Ressource Technique — identifiant d'accès"},
    {"id": "E-005", "type": NODE_ENTITY,     "label": "MAKING_FILE",
     "desc": "Dossier de réalisation — commande de provisionnement"},
    {"id": "E-006", "type": NODE_ENTITY,     "label": "CCL",
     "desc": "Circuit Client Logique — ressource d'offre"},
    {"id": "E-007", "type": NODE_ENTITY,     "label": "VLAN/VP/VC",
     "desc": "Ressources logiques réseau"},
    {"id": "E-008", "type": NODE_ENTITY,     "label": "EPC",
     "desc": "Entité de Provisionnement Centralisé"},

    # ── Causes ────────────────────────────────────────────────────────────────
    {"id": "C-001", "type": NODE_CAUSE,      "label": "Cartes actives encore rattachées au DSLAM",
     "desc": "Des T-CARDs sont encore présentes dans t_cards pour ce DSLAM"},
    {"id": "C-002", "type": NODE_CAUSE,      "label": "Services actifs sur les ports",
     "desc": "Des ports sont encore en statut actif, bloquant la suppression"},
    {"id": "C-003", "type": NODE_CAUSE,      "label": "DSLAM fermé à la production",
     "desc": "eqpt_prod_status='F' — aucune allocation possible"},
    {"id": "C-004", "type": NODE_CAUSE,      "label": "Compteur port_attribuable incorrect",
     "desc": "port_attribuable=0 mais des ports sont physiquement libres"},
    {"id": "C-005", "type": NODE_CAUSE,      "label": "MRT non synchronisé après migration",
     "desc": "Migration DSLAM n'a pas mis à jour t_mrt_access_dslams"},
    {"id": "C-006", "type": NODE_CAUSE,      "label": "NIFolderID absent du message UMI-EPC",
     "desc": "Le champ obligatoire NIFolderID est manquant dans la commande"},
    {"id": "C-007", "type": NODE_CAUSE,      "label": "Transactions concurrentes sur même DSLAM",
     "desc": "Plusieurs dossiers tentent de verrouiller les mêmes ressources"},
    {"id": "C-008", "type": NODE_CAUSE,      "label": "Rollback partiel laissant compteurs incohérents",
     "desc": "Une transaction interrompue n'a pas décrémenté les compteurs VP/VC"},
    {"id": "C-009", "type": NODE_CAUSE,      "label": "TSF non provisionnées à l'onboarding DSLAM",
     "desc": "L'étape de provisionnement TSF a été sautée lors de la mise en service"},
    {"id": "C-010", "type": NODE_CAUSE,      "label": "FK constraint violation sur t_cards",
     "desc": "Contrainte de clé étrangère empêche la suppression de l'équipement parent"},
    {"id": "C-011", "type": NODE_CAUSE,      "label": "Carte fermée à la production",
     "desc": "card_prod_status='F' sur la carte cible"},
    {"id": "C-012", "type": NODE_CAUSE,      "label": "CCL NumeroCCL absent pour offre CEV",
     "desc": "Le champ NumeroCCL est obligatoire pour les offres CEV"},

    # ── Constraints ───────────────────────────────────────────────────────────
    {"id": "K-001", "type": NODE_CONSTRAINT, "label": "SFD: Ne pas supprimer si cartes actives",
     "desc": "Un équipement DSLAM ne peut pas être supprimé si des cartes y sont rattachées",
     "meta": {"rule_id": "CSTR-SQL-001", "severity": "blocking"}},
    {"id": "K-002", "type": NODE_CONSTRAINT, "label": "SFD: Ne pas supprimer si ports actifs",
     "desc": "Des ports actifs bloquent la suppression de la carte parente",
     "meta": {"rule_id": "CSTR-SQL-002", "severity": "blocking"}},
    {"id": "K-003", "type": NODE_CONSTRAINT, "label": "SFD: DSLAM doit être ouvert à la production",
     "desc": "eqpt_prod_status doit être 'O' pour toute opération d'allocation",
     "meta": {"rule_id": "CSTR-FR-001", "severity": "blocking"}},
    {"id": "K-004", "type": NODE_CONSTRAINT, "label": "SFD: port_attribuable doit être > 0",
     "desc": "Le compteur port_attribuable doit être positif pour affecter une broche",
     "meta": {"rule_id": "CSTR-FR-007", "severity": "blocking"}},
    {"id": "K-005", "type": NODE_CONSTRAINT, "label": "SFD: Deadlock — 3 tentatives max",
     "desc": "En cas de deadlock, le système réessaie 3 fois avec 55s de délai",
     "meta": {"rule_id": "CSTR-FR-010", "severity": "warning"}},
    {"id": "K-006", "type": NODE_CONSTRAINT, "label": "SFD: NumeroCCL obligatoire pour CEV",
     "desc": "Le champ NumeroCCL est obligatoire pour les offres CEV",
     "meta": {"rule_id": "CSTR-FR-003", "severity": "blocking"}},

    # ── Actions ───────────────────────────────────────────────────────────────
    {"id": "A-001", "type": NODE_ACTION,     "label": "Vérifier cartes: SELECT FROM t_cards WHERE eqpt_id=<ID>",
     "desc": "Lister toutes les cartes rattachées à l'équipement", "meta": {"fr": ""}},
    {"id": "A-002", "type": NODE_ACTION,     "label": "Vérifier ports actifs: SELECT FROM t_ports WHERE card_id IN (...)",
     "desc": "Lister tous les ports encore actifs sur les cartes", "meta": {"fr": ""}},
    {"id": "A-003", "type": NODE_ACTION,     "label": "Désaffecter services actifs via IHM BRASIL",
     "desc": "Retirer tous les services avant suppression de l'équipement", "meta": {"fr": "FR-001"}},
    {"id": "A-004", "type": NODE_ACTION,     "label": "Ouvrir DSLAM à la production (eqpt_prod_status='O')",
     "desc": "Modifier le statut de production via IHM ou UPDATE direct", "meta": {"fr": "FR-001"}},
    {"id": "A-005", "type": NODE_ACTION,     "label": "Lancer CalculerToc.ksh pour recalculer les compteurs",
     "desc": "Script de recalcul du TOC et des compteurs port_attribuable", "meta": {"fr": "FR-001"}},
    {"id": "A-006", "type": NODE_ACTION,     "label": "Appliquer FR 136b: Libérer ports occupés à tort",
     "desc": "Procédure de libération des ports logiques incorrectement occupés", "meta": {"fr": "FR-136b"}},
    {"id": "A-007", "type": NODE_ACTION,     "label": "Appliquer FR 136c: Corriger compteurs VP/VLAN/VC",
     "desc": "Correction des compteurs de ressources logiques", "meta": {"fr": "FR-136c"}},
    {"id": "A-008", "type": NODE_ACTION,     "label": "Vérifier pg_locks et tuer sessions bloquantes",
     "desc": "Identifier et terminer les transactions PostgreSQL bloquantes", "meta": {"fr": ""}},
    {"id": "A-009", "type": NODE_ACTION,     "label": "Synchroniser MRT: vérifier t_mrt_access_dslams",
     "desc": "Recréer ou corriger l'entrée MRT après migration", "meta": {"fr": "FR-012"}},
    {"id": "A-010", "type": NODE_ACTION,     "label": "Appliquer FR 148/151: Contrôle nœud BRASIL vs Référentiel Sites",
     "desc": "Créer le nœud manquant dans BRASIL", "meta": {"fr": "FR-148"}},
    {"id": "A-011", "type": NODE_ACTION,     "label": "Provisionner TSF: vérifier t_d_rsc_dslam_tsfs",
     "desc": "Ajouter les fonctions de service technique manquantes", "meta": {"fr": "FR-137"}},
    {"id": "A-012", "type": NODE_ACTION,     "label": "Fermer DSLAM à la production avant suppression",
     "desc": "Mettre eqpt_prod_status='F' avant de lancer la suppression", "meta": {"fr": "FR-001"}},
]

# Edge definitions: (from_id, edge_type, to_id, weight, fr_ref)
_EDGES: List[Tuple] = [
    # S-001 (Suppression échoue) causal chain
    ("S-001", EDGE_CAUSES,     "C-001", 0.95, ""),
    ("C-001", EDGE_CAUSES,     "C-002", 0.90, ""),
    ("C-001", EDGE_TRIGGERS,   "K-001", 1.00, "CSTR-SQL-001"),
    ("C-002", EDGE_TRIGGERS,   "K-002", 1.00, "CSTR-SQL-002"),
    ("K-001", EDGE_REQUIRES,   "A-001", 1.00, ""),
    ("K-001", EDGE_REQUIRES,   "A-003", 0.95, "FR-001"),
    ("K-002", EDGE_REQUIRES,   "A-002", 1.00, ""),
    ("A-003", EDGE_RESOLVES,   "S-001", 0.85, "FR-001"),
    ("C-010", EDGE_CAUSES,     "S-001", 0.90, ""),
    ("C-010", EDGE_TRIGGERS,   "K-001", 0.95, "CSTR-SQL-001"),
    ("C-001", EDGE_DEPENDS_ON, "E-002", 1.00, ""),
    ("E-001", EDGE_RELATED,    "E-002", 1.00, ""),  # DSLAM contains CARD
    ("E-002", EDGE_RELATED,    "E-003", 1.00, ""),  # CARD contains PORT

    # S-002 (Aucun port disponible) causal chain
    ("S-002", EDGE_CAUSES,     "C-003", 0.70, ""),
    ("S-002", EDGE_CAUSES,     "C-004", 0.90, ""),
    ("C-003", EDGE_TRIGGERS,   "K-003", 1.00, "CSTR-FR-001"),
    ("C-004", EDGE_TRIGGERS,   "K-004", 1.00, "CSTR-FR-007"),
    ("K-003", EDGE_REQUIRES,   "A-004", 1.00, "FR-001"),
    ("K-004", EDGE_REQUIRES,   "A-005", 1.00, "FR-001"),
    ("A-005", EDGE_RESOLVES,   "S-002", 0.80, "FR-001"),
    ("A-004", EDGE_RESOLVES,   "S-009", 0.90, "FR-001"),

    # S-003 (Commande bloquée) causal chain
    ("S-003", EDGE_CAUSES,     "C-007", 0.85, ""),
    ("C-007", EDGE_TRIGGERS,   "K-005", 1.00, "CSTR-FR-010"),
    ("K-005", EDGE_REQUIRES,   "A-008", 0.90, ""),

    # S-007 (Compteurs incorrects) causal chain
    ("S-007", EDGE_CAUSES,     "C-008", 0.90, ""),
    ("C-008", EDGE_REQUIRES,   "A-006", 1.00, "FR-136b"),
    ("C-008", EDGE_REQUIRES,   "A-007", 1.00, "FR-136c"),
    ("A-006", EDGE_RESOLVES,   "S-007", 0.85, "FR-136b"),
    ("A-007", EDGE_RESOLVES,   "S-007", 0.85, "FR-136c"),

    # S-004 (MRT introuvable) causal chain
    ("S-004", EDGE_CAUSES,     "C-005", 0.90, ""),
    ("C-005", EDGE_REQUIRES,   "A-009", 1.00, "FR-012"),
    ("A-009", EDGE_RESOLVES,   "S-004", 0.80, "FR-012"),

    # S-008 (TSF not found) causal chain
    ("S-008", EDGE_CAUSES,     "C-009", 0.90, ""),
    ("C-009", EDGE_REQUIRES,   "A-011", 1.00, "FR-137"),
    ("A-011", EDGE_RESOLVES,   "S-008", 0.80, "FR-137"),

    # S-009 (DSLAM fermé) links
    ("S-009", EDGE_CAUSES,     "C-003", 0.95, ""),
    ("C-003", EDGE_TRIGGERS,   "K-003", 1.00, "CSTR-FR-001"),

    # S-010 (Nœud absent)
    ("S-010", EDGE_REQUIRES,   "A-010", 1.00, "FR-148"),
]

# Pre-process edges: symptom keyword → node ID mapping
_SYMPTOM_KEYWORDS: Dict[str, str] = {
    "supprimer":        "S-001",
    "suppression":      "S-001",
    "delete":           "S-001",
    "port":             "S-002",
    "broche":           "S-002",
    "toc":              "S-002",
    "bloqué":           "S-003",
    "deadlock":         "S-006",
    "verrou":           "S-006",
    "compteur":         "S-007",
    "vlan":             "S-007",
    "vc":               "S-007",
    "mrt":              "S-004",
    "dossier":          "S-005",
    "nifolderid":       "S-005",
    "tsf":              "S-008",
    "fermé":            "S-009",
    "ferm":             "S-009",
    "production":       "S-009",
    "nœud":             "S-010",
    "node":             "S-010",
    "carte":            "C-001",
    "card":             "C-001",
}

# Hypothesis ID → symptom node mapping (from correlation_engine catalog)
_HYP_TO_SYMPTOM: Dict[str, str] = {
    "HYP-001": "S-009",
    "HYP-002": "S-002",
    "HYP-003": "C-011",   # card closed
    "HYP-004": "S-004",
    "HYP-005": "S-005",
    "HYP-006": "C-012",
    "HYP-007": "S-006",
    "HYP-008": "S-007",
    "HYP-009": "S-003",
    "HYP-010": "S-001",
    "HYP-011": "S-010",
    "HYP-012": "S-008",
}


# ─────────────────────────────────────────────────────────────────────────────
# IncidentGraph
# ─────────────────────────────────────────────────────────────────────────────

class IncidentGraph:
    """
    Directed causal graph over BRASIL incident knowledge.

    Graph is built once from the static catalog above,
    then enriched with learned patterns from learning_loop outputs.
    """

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self._adj: Dict[str, List[str]] = {}   # node_id → [edge_ids]
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        # Build nodes
        for nd in _NODES:
            meta = nd.get("meta", {})
            node = GraphNode(
                id=nd["id"],
                node_type=nd["type"],
                label=nd["label"],
                description=nd.get("desc", ""),
                metadata=meta,
            )
            self.nodes[nd["id"]] = node
            self._adj[nd["id"]] = []

        # Build edges
        for (fid, etype, tid, weight, fr_ref) in _EDGES:
            if fid not in self.nodes or tid not in self.nodes:
                continue
            edge = GraphEdge(
                from_id=fid,
                to_id=tid,
                edge_type=etype,
                weight=weight,
                fr_reference=fr_ref,
            )
            self.edges[edge.id] = edge
            self._adj[fid].append(edge.id)

        # Try to load learned edges from learning loop output
        self._load_learned_edges()
        self._loaded = True

    # ── Query API ─────────────────────────────────────────────────────────────

    def reason(
        self,
        query: str,
        hypothesis_id: Optional[str] = None,
        entity_names: Optional[List[str]] = None,
        max_depth: int = 5,
    ) -> GraphReasoning:
        """
        Main reasoning entry point.
        Returns a full causal chain from symptom → cause → actions.
        """
        self.load()
        entity_names = entity_names or []

        # 1. Find entry node
        entry_node = self._find_entry_node(query, hypothesis_id)
        if entry_node is None:
            return self._empty_reasoning(query)

        entry_node.visit_count += 1

        # 2. Traverse causal chain (BFS)
        chain = self._traverse(entry_node, max_depth=max_depth)

        # 3. Extract root cause, constraints, actions
        root_cause = self._find_deepest_cause(chain)
        constraints = [s.node for s in chain if s.node.node_type == NODE_CONSTRAINT]
        actions = self._get_ordered_actions(chain, constraints)
        fr_refs = list({
            e.edge_from_parent.fr_reference
            for e in chain
            if e.edge_from_parent and e.edge_from_parent.fr_reference
        })

        # 4. Compute confidence
        confidence = self._chain_confidence(chain)

        # 5. Build explanation
        explanation = self._build_explanation(entry_node, chain, root_cause, constraints, actions)

        return GraphReasoning(
            root_symptom=entry_node,
            causal_chain=chain,
            root_cause=root_cause,
            blocking_constraints=constraints,
            recommended_actions=actions[:6],
            confidence=confidence,
            explanation=explanation,
            fr_references=fr_refs,
        )

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        self.load()
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[Tuple[GraphEdge, GraphNode]]:
        self.load()
        result = []
        for eid in self._adj.get(node_id, []):
            edge = self.edges[eid]
            if edge_type and edge.edge_type != edge_type:
                continue
            neighbor = self.nodes.get(edge.to_id)
            if neighbor:
                result.append((edge, neighbor))
        return sorted(result, key=lambda x: x[0].weight, reverse=True)

    def explain_node(self, node_id: str) -> str:
        """Return a human-readable explanation of a single node and its edges."""
        self.load()
        node = self.nodes.get(node_id)
        if not node:
            return f"Node {node_id} not found"
        lines = [f"[{node.node_type.upper()}] {node.label}"]
        if node.description:
            lines.append(f"  {node.description}")
        neighbors = self.get_neighbors(node_id)
        if neighbors:
            lines.append("  Edges:")
            for edge, neighbor in neighbors[:4]:
                fr = f" (ref: {edge.fr_reference})" if edge.fr_reference else ""
                lines.append(f"    ─{edge.edge_type}─► {neighbor.label}{fr}")
        return "\n".join(lines)

    def add_learned_edge(
        self,
        from_label: str,
        edge_type: str,
        to_label: str,
        weight: float = 0.7,
        fr_ref: str = "",
    ):
        """Dynamically add an edge learned from user confirmations."""
        self.load()
        # Find or create nodes
        from_node = self._find_node_by_label(from_label) or self._create_node(from_label, NODE_SYMPTOM)
        to_node   = self._find_node_by_label(to_label)   or self._create_node(to_label, NODE_CAUSE)

        edge = GraphEdge(
            from_id=from_node.id,
            to_id=to_node.id,
            edge_type=edge_type,
            weight=weight,
            fr_reference=fr_ref,
        )
        if edge.id not in self.edges:
            self.edges[edge.id] = edge
            if from_node.id not in self._adj:
                self._adj[from_node.id] = []
            self._adj[from_node.id].append(edge.id)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _find_entry_node(self, query: str, hypothesis_id: Optional[str]) -> Optional[GraphNode]:
        # From hypothesis ID mapping (most precise)
        if hypothesis_id and hypothesis_id in _HYP_TO_SYMPTOM:
            nid = _HYP_TO_SYMPTOM[hypothesis_id]
            return self.nodes.get(nid)

        # From keyword matching
        q_lower = query.lower()
        best_nid: Optional[str] = None
        best_score = 0
        for kw, nid in _SYMPTOM_KEYWORDS.items():
            if kw in q_lower:
                node = self.nodes.get(nid)
                if node:
                    score = node.visit_count + 1
                    if score > best_score:
                        best_score = score
                        best_nid = nid
        return self.nodes.get(best_nid) if best_nid else None

    def _traverse(self, start: GraphNode, max_depth: int) -> List[CausalChainStep]:
        """BFS traversal following causes, triggers, requires edges."""
        FOLLOW_TYPES = {EDGE_CAUSES, EDGE_TRIGGERS, EDGE_REQUIRES, EDGE_BLOCKS, EDGE_DEPENDS_ON}
        visited: Set[str] = set()
        queue: List[Tuple[GraphNode, Optional[GraphEdge], int]] = [(start, None, 0)]
        chain: List[CausalChainStep] = []

        while queue:
            node, parent_edge, depth = queue.pop(0)
            if node.id in visited or depth > max_depth:
                continue
            visited.add(node.id)
            chain.append(CausalChainStep(node=node, edge_from_parent=parent_edge, depth=depth))

            # Traverse neighbors
            for edge, neighbor in self.get_neighbors(node.id):
                if edge.edge_type in FOLLOW_TYPES and neighbor.id not in visited:
                    queue.append((neighbor, edge, depth + 1))

        return chain

    def _find_deepest_cause(self, chain: List[CausalChainStep]) -> Optional[GraphNode]:
        """Return the deepest CAUSE node in the chain."""
        causes = [s for s in chain if s.node.node_type == NODE_CAUSE]
        if not causes:
            return None
        deepest_step = max(causes, key=lambda s: s.depth)
        return deepest_step.node

    def _get_ordered_actions(
        self,
        chain: List[CausalChainStep],
        constraints: List[GraphNode],
    ) -> List[GraphNode]:
        """Collect ACTION nodes from chain, ordered by depth."""
        actions = [s.node for s in chain if s.node.node_type == NODE_ACTION]

        # Also get actions required by blocking constraints
        for constraint in constraints:
            for edge, neighbor in self.get_neighbors(constraint.id, edge_type=EDGE_REQUIRES):
                if neighbor.node_type == NODE_ACTION and neighbor not in actions:
                    actions.append(neighbor)

        # Deduplicate preserving order
        seen = set()
        deduped = []
        for a in actions:
            if a.id not in seen:
                seen.add(a.id)
                deduped.append(a)
        return deduped

    def _chain_confidence(self, chain: List[CausalChainStep]) -> float:
        if not chain:
            return 0.0
        weights = [
            s.edge_from_parent.weight
            for s in chain
            if s.edge_from_parent
        ]
        if not weights:
            base = 0.7
        else:
            # Geometric mean for multi-hop confidence
            log_sum = sum(math.log(max(w, 0.01)) for w in weights)
            base = min(1.0, math.exp(log_sum / len(weights)))

        # visit_count boost: log(1 + total_visits) * 0.15
        total_visits = sum(s.node.visit_count for s in chain)
        visit_boost = math.log(1 + total_visits) * 0.15
        return min(1.0, base + visit_boost)

    def _build_explanation(
        self,
        entry: GraphNode,
        chain: List[CausalChainStep],
        root_cause: Optional[GraphNode],
        constraints: List[GraphNode],
        actions: List[GraphNode],
    ) -> str:
        lines = []

        # Opening
        lines.append(f"Le problème détecté est : **{entry.label}**.")
        if entry.description:
            lines.append(f"_{entry.description}_")

        # Causal chain narrative
        causes = [s for s in chain if s.node.node_type == NODE_CAUSE]
        if causes:
            lines.append("\n**Chaîne causale identifiée :**")
            for step in causes[:4]:
                edge_label = step.edge_from_parent.edge_type.replace("_", " ") if step.edge_from_parent else "lié à"
                lines.append(f"  {step.explain()}")

        # Root cause
        if root_cause:
            lines.append(f"\n**Cause racine :** {root_cause.label}")
            if root_cause.description:
                lines.append(f"  → {root_cause.description}")

        # SFD constraints
        if constraints:
            lines.append("\n**Règles SFD applicables :**")
            for cstr in constraints[:3]:
                rule_id = cstr.metadata.get("rule_id", "")
                lines.append(f"  • [{rule_id}] {cstr.label}")
                lines.append(f"    {cstr.description}")

        # Actions
        if actions:
            lines.append("\n**Plan d'action recommandé :**")
            for i, action in enumerate(actions[:5], 1):
                fr = action.metadata.get("fr", "")
                ref = f" [{fr}]" if fr else ""
                lines.append(f"  {i}. {action.label}{ref}")

        return "\n".join(lines)

    def _find_node_by_label(self, label: str) -> Optional[GraphNode]:
        label_lower = label.lower()
        for node in self.nodes.values():
            if node.label.lower() == label_lower:
                return node
        return None

    def _create_node(self, label: str, node_type: str) -> GraphNode:
        new_id = f"DYN-{len(self.nodes):04d}"
        node = GraphNode(id=new_id, node_type=node_type, label=label)
        self.nodes[new_id] = node
        self._adj[new_id] = []
        return node

    # ── Reinforcement API ────────────────────────────────────────────────────────

    def reinforce(self, hypothesis_id: str, delta: float = 0.15) -> None:
        """
        Boost all nodes in the causal chain for hypothesis_id.
        Increments visit_count and raises edge weights.
        Called on confirmed resolutions or human corrections.
        """
        self.load()
        symptom_id = _HYP_TO_SYMPTOM.get(hypothesis_id)
        if not symptom_id:
            return
        entry = self.nodes.get(symptom_id)
        if not entry:
            return
        chain = self._traverse(entry, max_depth=6)
        for step in chain:
            step.node.visit_count += 1
            # Strengthen edges on this chain
            if step.edge_from_parent:
                edge = self.edges.get(step.edge_from_parent.id)
                if edge:
                    edge.weight = min(1.0, edge.weight + delta * 0.1)
        self._persist_weights()

    def suppress(self, hypothesis_id: str, delta: float = 0.15) -> None:
        """
        Weaken all nodes for hypothesis_id.
        Decrements edge weights and marks symptom node.
        Called on repeated failures or human correction of wrong hypothesis.
        """
        self.load()
        symptom_id = _HYP_TO_SYMPTOM.get(hypothesis_id)
        if not symptom_id:
            return
        entry = self.nodes.get(symptom_id)
        if not entry:
            return
        chain = self._traverse(entry, max_depth=6)
        for step in chain:
            if step.edge_from_parent:
                edge = self.edges.get(step.edge_from_parent.id)
                if edge:
                    edge.weight = max(0.05, edge.weight - delta * 0.1)
        # Mark the symptom node itself as suppressed via metadata
        entry.metadata["suppressed_score"] = entry.metadata.get("suppressed_score", 0.0) - delta
        self._persist_weights()

    def get_node_suppression(self, hypothesis_id: str) -> float:
        """Return accumulated suppression delta for a hypothesis (≤ 0)."""
        self.load()
        symptom_id = _HYP_TO_SYMPTOM.get(hypothesis_id)
        if not symptom_id:
            return 0.0
        node = self.nodes.get(symptom_id)
        if not node:
            return 0.0
        return node.metadata.get("suppressed_score", 0.0)

    def _persist_weights(self) -> None:
        """Persist node visit_counts and edge weights to data/learning/graph_weights.json."""
        weights_file = (
            Path(__file__).parents[3] / "data" / "learning" / "graph_weights.json"
        )
        weights_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": {
                nid: {
                    "visit_count": n.visit_count,
                    "suppressed_score": n.metadata.get("suppressed_score", 0.0),
                }
                for nid, n in self.nodes.items()
                if n.visit_count > 0 or "suppressed_score" in n.metadata
            },
            "edges": {
                eid: {"weight": e.weight, "evidence_count": e.evidence_count}
                for eid, e in self.edges.items()
                if e.weight != 1.0 or e.evidence_count != 1
            },
        }
        weights_file.write_text(
            __import__("json").dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_learned_edges(self):
        """Load dynamically learned edges from learning loop output."""
        patterns_file = (
            Path(__file__).parents[3] / "data" / "learning" / "learned_patterns.json"
        )
        if patterns_file.exists():
            try:
                data = json.loads(patterns_file.read_text(encoding="utf-8"))
                for pattern in data.get("patterns", []):
                    hyp_id = pattern.get("hypothesis_id", "")
                    if hyp_id in _HYP_TO_SYMPTOM:
                        symptom_id = _HYP_TO_SYMPTOM[hyp_id]
                        symptom_node = self.nodes.get(symptom_id)
                        if symptom_node:
                            symptom_node.visit_count += 1
            except Exception:
                pass

        # Load persisted weights (visit_count + edge weights from reinforce/suppress)
        weights_file = (
            Path(__file__).parents[3] / "data" / "learning" / "graph_weights.json"
        )
        if weights_file.exists():
            try:
                w = json.loads(weights_file.read_text(encoding="utf-8"))
                for nid, ndata in w.get("nodes", {}).items():
                    node = self.nodes.get(nid)
                    if node:
                        node.visit_count = max(node.visit_count, ndata.get("visit_count", 0))
                        if "suppressed_score" in ndata:
                            node.metadata["suppressed_score"] = ndata["suppressed_score"]
                for eid, edata in w.get("edges", {}).items():
                    edge = self.edges.get(eid)
                    if edge:
                        edge.weight = edata.get("weight", edge.weight)
                        edge.evidence_count = edata.get("evidence_count", edge.evidence_count)
            except Exception:
                pass

    def _empty_reasoning(self, query: str) -> "GraphReasoning":
        placeholder = GraphNode(
            id="UNKNOWN",
            node_type=NODE_SYMPTOM,
            label=f"Symptôme non cartographié: {query[:60]}",
        )
        return GraphReasoning(
            root_symptom=placeholder,
            causal_chain=[CausalChainStep(placeholder, None, 0)],
            root_cause=None,
            blocking_constraints=[],
            recommended_actions=[],
            confidence=0.0,
            explanation=(
                "Je n'ai pas pu cartographier ce symptôme dans le graphe d'incidents BRASIL.\n"
                "Veuillez préciser l'équipement concerné et le message d'erreur exact."
            ),
            fr_references=[],
        )


# Singleton
incident_graph = IncidentGraph()
