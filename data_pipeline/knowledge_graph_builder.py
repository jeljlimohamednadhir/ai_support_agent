"""
Knowledge Graph Builder — Builds an incident knowledge graph using NetworkX.
Connects: Tickets ↔ IncidentTypes ↔ Procedures ↔ Applications ↔ ErrorCodes ↔ Clusters

Input:
  - data_pipeline/output/ticket_structured.json
  - data_pipeline/output/fr_normalized.json
  - data_pipeline/output/cluster_results.json

Output:
  - data_pipeline/output/knowledge_graph.json  (serialized)
  - data_pipeline/output/knowledge_graph.gexf  (Gephi-compatible, if networkx available)
"""
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

BACKEND_DIR = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

TICKET_FILE    = Path(__file__).parent / "output" / "ticket_structured.json"
FR_FILE        = Path(__file__).parent / "output" / "fr_normalized.json"
CLUSTER_FILE   = Path(__file__).parent / "output" / "cluster_results.json"
OUTPUT_JSON    = Path(__file__).parent / "output" / "knowledge_graph.json"
OUTPUT_GEXF    = Path(__file__).parent / "output" / "knowledge_graph.gexf"


# ─────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────

class KnowledgeGraphBuilder:
    """
    Builds a directed knowledge graph from all pipeline outputs.

    Node types:
      - Application       (BRASIL, SEBA, ...)
      - Ticket            (individual tickets)
      - IncidentType      (from taxonomy)
      - Cluster           (from clustering engine)
      - Procedure         (from fr_normalized)
      - ErrorCode         (from all sources)
      - RootCause         (extracted from procedures)

    Edge types:
      - Ticket       → [IS_TYPE]     → IncidentType
      - Ticket       → [BELONGS_TO]  → Cluster
      - Ticket       → [INVOLVES]    → Application
      - Ticket       → [HAS_ERROR]   → ErrorCode
      - Cluster      → [RESOLVED_BY] → Procedure
      - Procedure    → [APPLIES_TO]  → Application
      - Procedure    → [ADDRESSES]   → IncidentType
      - Procedure    → [HAS_ERROR]   → ErrorCode
      - ErrorCode    → [OCCURS_IN]   → Application
      - Application  → [INTERFACES_WITH] → Application
    """

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}         # id → {type, ...attrs}
        self.edges: List[Dict] = []              # [{from, to, rel_type, ...attrs}]
        self._edge_set = set()                   # Deduplication

    # ─────────────────────────────────────────────
    # Node management
    # ─────────────────────────────────────────────

    def add_node(self, node_id: str, node_type: str, **attrs):
        if node_id not in self.nodes:
            self.nodes[node_id] = {"id": node_id, "type": node_type, **attrs}

    def update_node(self, node_id: str, **attrs):
        if node_id in self.nodes:
            self.nodes[node_id].update(attrs)

    def add_edge(self, from_id: str, to_id: str, rel_type: str, **attrs):
        key = (from_id, to_id, rel_type)
        if key not in self._edge_set:
            self._edge_set.add(key)
            self.edges.append({
                "from": from_id,
                "to": to_id,
                "rel_type": rel_type,
                **attrs
            })

    # ─────────────────────────────────────────────
    # Ingestion methods
    # ─────────────────────────────────────────────

    def ingest_applications(self):
        """Add all known applications as nodes and their interface edges."""
        applications = ["BRASIL", "SEBA", "ARTEMIS", "IPON", "ADELIA", "SCA", "ORCHESTRA"]
        for app in applications:
            self.add_node(f"APP:{app}", "Application", name=app, display_name=app)

        # Known interface relationships
        interfaces = [
            ("BRASIL", "SEBA"),
            ("BRASIL", "ARTEMIS"),
            ("BRASIL", "IPON"),
            ("BRASIL", "ADELIA"),
            ("BRASIL", "SCA"),
            ("BRASIL", "ORCHESTRA"),
            ("SEBA", "IPON"),
        ]
        for a, b in interfaces:
            self.add_edge(f"APP:{a}", f"APP:{b}", "INTERFACES_WITH")
            self.add_edge(f"APP:{b}", f"APP:{a}", "INTERFACES_WITH")

    def ingest_taxonomy(self):
        """Add all incident types from the taxonomy as nodes."""
        try:
            from app.services.nlp.taxonomy import INCIDENT_TAXONOMY
            for type_id, defn in INCIDENT_TAXONOMY.items():
                self.add_node(
                    f"INC:{type_id}",
                    "IncidentType",
                    name=type_id,
                    category=defn.category,
                    display_name=defn.name,
                    description=defn.description,
                    severity=defn.severity,
                )
                for sys_name in defn.related_systems:
                    self.add_edge(f"INC:{type_id}", f"APP:{sys_name}", "INVOLVES")
        except Exception as e:
            print(f"  ⚠️  Taxonomie non chargée: {e}")

    def ingest_tickets(self, tickets: List[Dict]):
        """Ingest structured tickets as graph nodes with all their edges."""
        for t in tickets:
            tid = t["ticket_id"]
            node_id = f"TKT:{tid}"
            self.add_node(
                node_id, "Ticket",
                ticket_id=tid,
                intent=t.get("intent", ""),
                confidence=t.get("confidence", 0),
                trust_score=t.get("trust_score", 0),
                preprocessed_text=t.get("preprocessed_text", "")[:200],
            )
            # → Application
            app = t.get("application", "BRASIL")
            self.add_edge(node_id, f"APP:{app}", "INVOLVES")

            # → IncidentType
            inc_type = t.get("incident_type", "")
            if inc_type:
                self.add_node(f"INC:{inc_type}", "IncidentType", name=inc_type)
                self.add_edge(node_id, f"INC:{inc_type}", "IS_TYPE")

            # → ErrorCodes
            for code in t.get("error_codes", []):
                ec_id = f"ERR:{code.upper()}"
                self.add_node(ec_id, "ErrorCode", code=code.upper())
                self.add_edge(node_id, ec_id, "HAS_ERROR")
                self.add_edge(ec_id, f"APP:{app}", "OCCURS_IN")

            # → Cluster (if assigned)
            if t.get("cluster_id"):
                clu_id = f"CLU:{t['cluster_id']}"
                self.add_node(clu_id, "Cluster", cluster_id=t["cluster_id"])
                self.add_edge(node_id, clu_id, "BELONGS_TO")

    def ingest_clusters(self, clusters: List[Dict], ticket_cluster_map: Dict):
        """Ingest cluster nodes and enrich ticket→cluster edges."""
        for c in clusters:
            clu_id = f"CLU:{c['cluster_id']}"
            self.add_node(
                clu_id, "Cluster",
                cluster_id=c["cluster_id"],
                cluster_name=c["cluster_name"],
                size=c["size"],
                trust_score=c["trust_score"],
                incident_type=c.get("incident_type", ""),
                top_error_codes=c.get("top_error_codes", []),
            )
            # → Application
            app = c.get("application", "BRASIL")
            self.add_edge(clu_id, f"APP:{app}", "INVOLVES")

            # → IncidentType
            inc_type = c.get("incident_type", "")
            if inc_type:
                self.add_node(f"INC:{inc_type}", "IncidentType", name=inc_type)
                self.add_edge(clu_id, f"INC:{inc_type}", "IS_TYPE")

        # Update ticket nodes with cluster assignments
        for ticket_id, cluster_id in ticket_cluster_map.items():
            if cluster_id != "CLU-NOISE":
                node_id = f"TKT:{ticket_id}"
                clu_id = f"CLU:{cluster_id}"
                self.add_node(clu_id, "Cluster", cluster_id=cluster_id)
                self.add_edge(node_id, clu_id, "BELONGS_TO")

    def ingest_procedures(self, procedures: List[Dict]):
        """Ingest FR procedures as nodes with all their edges."""
        for p in procedures:
            proc_id = p["procedure_id"]
            node_id = f"PROC:{proc_id}"
            self.add_node(
                node_id, "Procedure",
                procedure_id=proc_id,
                title=p.get("title", ""),
                application=p.get("application", "BRASIL"),
                confidence_level=p.get("confidence_level", "low"),
                trust_score=p.get("trust_score", 0),
                incident_type=p.get("incident_type", ""),
            )
            # → Application
            app = p.get("application", "BRASIL")
            self.add_edge(node_id, f"APP:{app}", "APPLIES_TO")

            # Related systems
            for sys_name in p.get("related_systems", []):
                if sys_name != app:
                    self.add_edge(node_id, f"APP:{sys_name}", "APPLIES_TO")

            # → IncidentType
            inc_type = p.get("incident_type", "")
            if inc_type:
                self.add_node(f"INC:{inc_type}", "IncidentType", name=inc_type)
                self.add_edge(node_id, f"INC:{inc_type}", "ADDRESSES")

            # → ErrorCodes
            for code in p.get("error_codes", []):
                ec_id = f"ERR:{code.upper()}"
                self.add_node(ec_id, "ErrorCode", code=code.upper())
                self.add_edge(node_id, ec_id, "HAS_ERROR")

            # Root cause node
            rc = p.get("root_cause", "")
            if rc:
                import hashlib
                rc_id = f"RC:{hashlib.md5(rc.encode()).hexdigest()[:10]}"
                self.add_node(rc_id, "RootCause", description=rc[:300])
                self.add_edge(node_id, rc_id, "HAS_ROOT_CAUSE")

    def link_clusters_to_procedures(self, clusters: List[Dict], procedures: List[Dict]):
        """
        Link clusters to procedures by matching incident_type and error_codes.
        Creates: Cluster → [RESOLVED_BY] → Procedure
        """
        # Build index: (incident_type, error_code) → procedure
        proc_index: Dict[str, List[str]] = {}
        for p in procedures:
            inc_type = p.get("incident_type", "")
            proc_node = f"PROC:{p['procedure_id']}"
            if inc_type:
                proc_index.setdefault(inc_type, []).append(proc_node)
            for code in p.get("error_codes", []):
                proc_index.setdefault(f"ERR:{code.upper()}", []).append(proc_node)

        for c in clusters:
            clu_node = f"CLU:{c['cluster_id']}"
            inc_type = c.get("incident_type", "")
            matched = set()

            if inc_type and inc_type in proc_index:
                matched.update(proc_index[inc_type])
            for code in c.get("top_error_codes", []):
                key = f"ERR:{code.upper()}"
                if key in proc_index:
                    matched.update(proc_index[key])

            for proc_node in matched:
                self.add_edge(clu_node, proc_node, "RESOLVED_BY")
                # Also update linked_procedures list on cluster node
                if clu_node in self.nodes:
                    procs = self.nodes[clu_node].get("linked_procedures", [])
                    if proc_node not in procs:
                        procs.append(proc_node)
                    self.nodes[clu_node]["linked_procedures"] = procs

    # ─────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "nodes_by_type": _count_by_type(self.nodes),
                "edges_by_type": _count_by_rel(self.edges),
            },
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }

    def export_networkx(self):
        """Export as NetworkX DiGraph if available."""
        try:
            import networkx as nx
            G = nx.DiGraph()
            for node_id, attrs in self.nodes.items():
                # GEXF requires a 'label' string attribute
                safe_attrs = {k: v for k, v in attrs.items() if isinstance(v, (str, int, float, bool))}
                safe_attrs.setdefault("label", str(node_id))
                G.add_node(str(node_id), **safe_attrs)
            for i, edge in enumerate(self.edges):
                G.add_edge(
                    str(edge["from"]),
                    str(edge["to"]),
                    key=f"e{i}",
                    label=edge["rel_type"],
                    weight=1.0,
                )
            return G
        except ImportError:
            return None


def _count_by_type(nodes: Dict) -> Dict[str, int]:
    from collections import Counter
    return dict(Counter(n["type"] for n in nodes.values()))


def _count_by_rel(edges: List) -> Dict[str, int]:
    from collections import Counter
    return dict(Counter(e["rel_type"] for e in edges))


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def run(dry_run: bool = False) -> bool:
    builder = KnowledgeGraphBuilder()

    # 1. Applications
    print("  🏗️  Construction du graphe de connaissances...")
    builder.ingest_applications()
    builder.ingest_taxonomy()
    print(f"     Applications + Taxonomie: {len(builder.nodes)} nœuds")

    # 2. Tickets
    tickets = []
    if TICKET_FILE.exists():
        with open(TICKET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        tickets = data.get("tickets", [])
        builder.ingest_tickets(tickets)
        print(f"     Après tickets ({len(tickets)}): {len(builder.nodes)} nœuds, {len(builder.edges)} arêtes")
    else:
        print(f"  ⚠️  ticket_structured.json absent")

    # 3. Clusters
    clusters = []
    ticket_cluster_map = {}
    if CLUSTER_FILE.exists():
        with open(CLUSTER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        clusters = data.get("clusters", [])
        ticket_cluster_map = data.get("ticket_cluster_map", {})
        builder.ingest_clusters(clusters, ticket_cluster_map)
        print(f"     Après clusters ({len(clusters)}): {len(builder.nodes)} nœuds")
    else:
        print(f"  ⚠️  cluster_results.json absent")

    # 4. Procedures (FR normalized)
    procedures = []
    if FR_FILE.exists():
        with open(FR_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        procedures = data.get("procedures", [])
        builder.ingest_procedures(procedures)
        print(f"     Après procédures ({len(procedures)}): {len(builder.nodes)} nœuds")
    else:
        print(f"  ⚠️  fr_normalized.json absent")

    # 5. Link clusters → procedures
    if clusters and procedures:
        builder.link_clusters_to_procedures(clusters, procedures)

    graph_data = builder.to_dict()
    stats = graph_data["stats"]
    print(f"\n  📊 Graphe final:")
    print(f"     Nœuds: {stats['total_nodes']}")
    print(f"     Arêtes: {stats['total_edges']}")
    for node_type, count in sorted(stats['nodes_by_type'].items()):
        print(f"       {node_type}: {count}")
    for edge_type, count in sorted(stats['edges_by_type'].items()):
        print(f"       [{edge_type}]: {count}")

    if dry_run:
        print("  🔍 Mode DRY-RUN — pas d'écriture")
        return True

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 Graphe JSON: {OUTPUT_JSON}")

    # Export GEXF if NetworkX available
    G = builder.export_networkx()
    if G is not None:
        try:
            import networkx as nx
            nx.write_gexf(G, str(OUTPUT_GEXF))
            print(f"  💾 Graphe GEXF: {OUTPUT_GEXF}")
        except Exception as e:
            print(f"  ⚠️  Export GEXF échoué: {e}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Knowledge Graph Builder")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    success = run(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
