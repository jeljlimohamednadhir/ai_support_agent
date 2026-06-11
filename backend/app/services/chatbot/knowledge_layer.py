"""
Layer 2 — Knowledge Layer
===========================
Multi-source hybrid retrieval for N3 BRASIL diagnostics.

Sources (priority order):
  1. INCIDENTS (historical case-based evidence) — PRIMARY
  2. FR Documents (official procedures)
  3. Log patterns (regex-based error matching)
  4. SFD constraints (structural rules)
  5. Canonical KB (brasil_entities, brasil_workflows, etc.)

JIRA: NEVER indexed here. NEVER used for query/response.
JIRA feeds only the learning_loop.py (Layer 8).

Retrieval strategy:
  - TF-IDF BM25-style keyword scoring for incident + FR blocks
  - Regex matching for log patterns
  - Entity-based exact lookup for constraints and entities
  - Sliding window re-ranking by entity overlap
"""
from __future__ import annotations

import re
import json
import math
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

_BASE = Path(__file__).parents[3]   # backend/
_DATA = _BASE / "data"


# ─────────────────────────────────────────────────────────────────────────────
# In-memory indexes
# ─────────────────────────────────────────────────────────────────────────────

class _BM25Index:
    """
    Lightweight BM25 index for small corpora (< 50k docs).
    Uses simple term frequency with IDF weighting.
    """
    K1 = 1.5
    B = 0.75

    def __init__(self):
        self.docs: List[Dict] = []
        self._idf: Dict[str, float] = {}
        self._tf: List[Dict[str, int]] = []
        self._avg_dl: float = 0.0
        self._built = False

    def add_doc(self, doc: Dict, text_field: str = "text"):
        self.docs.append(doc)
        tokens = self._tokenize(doc.get(text_field, ""))
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        self._tf.append(tf)
        self._built = False

    def build(self):
        N = len(self.docs)
        if N == 0:
            return
        df: Dict[str, int] = {}
        total_len = 0
        for tf in self._tf:
            total_len += sum(tf.values())
            for term in tf:
                df[term] = df.get(term, 0) + 1
        self._avg_dl = total_len / N
        self._idf = {
            term: math.log((N - freq + 0.5) / (freq + 0.5) + 1.0)
            for term, freq in df.items()
        }
        self._built = True

    def search(self, query: str, top_k: int = 5) -> List[Tuple[float, Dict]]:
        if not self._built:
            self.build()
        if not self.docs:
            return []
        q_terms = self._tokenize(query)
        scores: List[float] = []
        for idx, tf in enumerate(self._tf):
            dl = sum(tf.values())
            score = 0.0
            for term in q_terms:
                if term not in self._idf:
                    continue
                f = tf.get(term, 0)
                idf = self._idf[term]
                numer = f * (self.K1 + 1)
                denom = f + self.K1 * (1 - self.B + self.B * dl / max(1, self._avg_dl))
                score += idf * numer / denom
            scores.append(score)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(s, self.docs[i]) for i, s in ranked[:top_k] if s > 0]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\b[a-z0-9_]{3,}\b", text.lower())


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Layer class
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeLayer:
    """
    Multi-source hybrid retrieval.
    Indexes are built lazily on first query.
    """

    def __init__(self):
        self._indexes: Dict[str, _BM25Index] = {
            "incidents": _BM25Index(),
            "fr":        _BM25Index(),
            "logs":      _BM25Index(),
            "canonical": _BM25Index(),
        }
        self._log_patterns: List[Dict] = []
        self._sfd_constraints: List[Dict] = []
        self._entities: Dict[str, Dict] = {}
        self._loaded = False

    # ── public API ────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        top_k: int = 5,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve knowledge blocks from all sources.
        Learned patterns are prepended as HIGH PRIORITY evidence.

        Returns:
            {
              "incidents": [...],
              "fr": [...],
              "logs": [...],
              "sfd_constraints": [...],
              "canonical": [...],
            }
        """
        self._ensure_loaded()
        entities = entities or []
        sources = sources or ["incidents", "fr", "logs", "sfd_constraints", "canonical"]

        result: Dict[str, List[Dict]] = {s: [] for s in sources}

        if "incidents" in sources:
            result["incidents"] = self._search_index("incidents", query, entities, top_k)
        if "fr" in sources:
            result["fr"] = self._search_index("fr", query, entities, top_k)
        if "logs" in sources:
            result["logs"] = self._match_log_patterns(query)
        if "sfd_constraints" in sources:
            result["sfd_constraints"] = self._match_sfd_constraints(query, entities)
        if "canonical" in sources:
            result["canonical"] = self._search_index("canonical", query, entities, top_k)

        # ── LEARNING INJECTION: prepend learned patterns as top evidence ──────
        if "incidents" in sources:
            learned_blocks = self._inject_learned_patterns(entities, query)
            if learned_blocks:
                result["incidents"] = learned_blocks + result["incidents"]
                result["incidents"] = result["incidents"][:top_k + len(learned_blocks)]

        return result

    def get_entity(self, name: str) -> Optional[Dict]:
        self._ensure_loaded()
        return self._entities.get(name.upper())

    def get_log_patterns(self) -> List[Dict]:
        self._ensure_loaded()
        return self._log_patterns

    def get_all_constraints(self) -> List[Dict]:
        self._ensure_loaded()
        return self._sfd_constraints

    def format_context_block(self, retrieved: Dict[str, List[Dict]], max_chars: int = 2000) -> str:
        """
        Format retrieved knowledge into a single LLM-injectable context block.
        Prioritizes incident evidence > FR > logs > SFD.
        """
        lines: List[str] = []
        budget = max_chars

        for source_key, label in [
            ("incidents", "INCIDENTS SIMILAIRES"),
            ("fr",        "DOCUMENTATION FR"),
            ("logs",      "PATTERNS ERREUR"),
            ("sfd_constraints", "CONTRAINTES SFD"),
            ("canonical", "ENTITÉS BRASIL"),
        ]:
            blocks = retrieved.get(source_key, [])
            if not blocks:
                continue
            header = f"\n### {label} ({len(blocks)} résultat(s)):\n"
            if len(header) > budget:
                break
            lines.append(header)
            budget -= len(header)
            for block in blocks[:3]:
                snippet = self._block_snippet(block, source_key)
                if len(snippet) + 2 > budget:
                    break
                lines.append(snippet)
                budget -= len(snippet) + 2

        return "\n".join(lines)

    # ── internal ──────────────────────────────────────────────────────────────

    def _ensure_loaded(self):
        if not self._loaded:
            self._load_all()
            self._loaded = True

    def _load_all(self):
        """Load all data sources into indexes."""
        self._load_incidents()
        self._load_fr_docs()
        self._load_log_patterns()
        self._load_sfd_constraints()
        self._load_canonical()
        self._load_schema_knowledge()   # ← schéma extrait de brasil_prod

    def _load_incidents(self):
        """
        Load incidents from data/incidents/ directory.
        Each file is expected to be a JSON with a list of incident dicts.
        Also checks data_pipeline/output/ for legacy data.
        """
        search_paths = [
            _DATA / "incidents",
            _BASE.parent / "data" / "incidents",
        ]
        count = 0
        for search_path in search_paths:
            if not search_path.exists():
                continue
            for f in search_path.glob("*.json"):
                try:
                    raw = json.loads(f.read_text(encoding="utf-8"))
                    items = raw if isinstance(raw, list) else raw.get("incidents", [raw])
                    for item in items:
                        text = _incident_to_text(item)
                        doc = {**item, "_text": text, "_source": "incident", "_file": f.name}
                        self._indexes["incidents"].add_doc(doc, "_text")
                        count += 1
                except Exception as e:
                    logger.warning(f"Failed to load incident file {f}: {e}")
        self._indexes["incidents"].build()
        logger.info(f"Knowledge Layer: loaded {count} incidents")

    def _load_fr_docs(self):
        """
        Load FR documentation from data/fr/ or directly from pipeline JSON.
        """
        fr_paths = [
            _DATA / "fr",
            _DATA,
        ]
        count = 0
        for fr_path in fr_paths:
            if not fr_path.exists():
                continue
            for f in fr_path.glob("*.json"):
                if "fr" not in f.name.lower() and f.name not in ("brasil_entities.json",):
                    continue
                try:
                    raw = json.loads(f.read_text(encoding="utf-8"))
                    items = raw if isinstance(raw, list) else raw.get("entities", raw.get("fr_docs", []))
                    if not isinstance(items, list):
                        continue
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        text = _dict_to_text(item)
                        doc = {**item, "_text": text, "_source": "fr", "_file": f.name}
                        self._indexes["fr"].add_doc(doc, "_text")
                        count += 1
                except Exception as e:
                    logger.warning(f"Failed to load FR file {f}: {e}")
        self._indexes["fr"].build()
        logger.info(f"Knowledge Layer: loaded {count} FR documents")

    def _load_log_patterns(self):
        """Load log patterns from brasil_logs_patterns.json."""
        patterns_file = _DATA / "brasil_logs_patterns.json"
        if not patterns_file.exists():
            logger.warning("brasil_logs_patterns.json not found")
            return
        try:
            raw = json.loads(patterns_file.read_text(encoding="utf-8"))
            patterns = raw if isinstance(raw, list) else raw.get("patterns", [])
            for p in patterns:
                text = _dict_to_text(p)
                doc = {**p, "_text": text, "_source": "log"}
                self._log_patterns.append(p)
                self._indexes["logs"].add_doc(doc, "_text")
            self._indexes["logs"].build()
            logger.info(f"Knowledge Layer: loaded {len(self._log_patterns)} log patterns")
        except Exception as e:
            logger.warning(f"Failed to load log patterns: {e}")

    def _load_sfd_constraints(self):
        """Load constraints from brasil_constraints.json."""
        constraints_file = _DATA / "brasil_constraints.json"
        if not constraints_file.exists():
            logger.warning("brasil_constraints.json not found")
            return
        try:
            raw = json.loads(constraints_file.read_text(encoding="utf-8"))
            constraints = raw if isinstance(raw, list) else raw.get("constraints", [])
            self._sfd_constraints = constraints
            logger.info(f"Knowledge Layer: loaded {len(self._sfd_constraints)} constraints")
        except Exception as e:
            logger.warning(f"Failed to load constraints: {e}")

    def _load_canonical(self):
        """Load entities and workflows into canonical index."""
        canonical_files = [
            _DATA / "brasil_entities.json",
            _DATA / "brasil_workflows.json",
            _DATA / "brasil_diagnostic_rules.json",
        ]
        count = 0

        # ── Présentation Brasil (source prioritaire) ──────────────────────────
        presentation_file = _DATA / "brasil_presentation.json"
        if presentation_file.exists():
            try:
                raw = json.loads(presentation_file.read_text(encoding="utf-8"))
                # Aplatir les sections en documents indexables
                pres = raw.get("presentation", {})
                archi = raw.get("architecture", {})
                meta = raw.get("meta", {})

                # Document 1 : présentation générale
                doc_pres = {
                    "name": "BRASIL_PRESENTATION",
                    "type": "presentation",
                    "title": meta.get("title", "Présentation BRASIL"),
                    "description": pres.get("description_courte", ""),
                    "content": pres.get("description_longue", ""),
                    "contexte": pres.get("contexte_operationnel", ""),
                    "nom_complet": pres.get("nom_complet", ""),
                    "nature": pres.get("nature", ""),
                    "domaine": pres.get("domaine", ""),
                    "_source": "presentation",
                    "_file": "brasil_presentation.json",
                }
                doc_pres["_text"] = " ".join(str(v) for v in doc_pres.values() if isinstance(v, str))
                self._indexes["canonical"].add_doc(doc_pres, "_text")
                self._entities["BRASIL"] = doc_pres
                self._entities["BRASIL_PRESENTATION"] = doc_pres
                count += 1

                # Document 2 : architecture + composants
                composants_text = " ".join(
                    f"{c.get('nom','')} {c.get('role','')}" for c in archi.get("composants_principaux", [])
                )
                doc_archi = {
                    "name": "BRASIL_ARCHITECTURE",
                    "type": "architecture",
                    "content": f"Architecture {archi.get('type_systeme','')}. Composants : {composants_text}",
                    "base_de_donnees": str(archi.get("base_de_donnees", {})),
                    "messagerie": str(archi.get("messagerie", {})),
                    "_source": "presentation",
                    "_file": "brasil_presentation.json",
                }
                doc_archi["_text"] = doc_archi["content"] + " " + doc_archi["base_de_donnees"] + " " + doc_archi["messagerie"]
                self._indexes["canonical"].add_doc(doc_archi, "_text")
                count += 1

                # Document 3 : entités principales
                for ent_name, ent_data in raw.get("entites_principales", {}).items():
                    doc_ent = {
                        "name": f"ENTITE_{ent_name}",
                        "type": "entity_definition",
                        "entity": ent_name,
                        "description": ent_data.get("description", ""),
                        "etats": str(ent_data.get("etats", "")),
                        "attribut_cle": ent_data.get("attribut_cle", ""),
                        "_source": "presentation",
                        "_file": "brasil_presentation.json",
                    }
                    doc_ent["_text"] = f"{ent_name} {doc_ent['description']} {doc_ent['etats']} {doc_ent['attribut_cle']}"
                    self._indexes["canonical"].add_doc(doc_ent, "_text")
                    self._entities[ent_name.upper()] = doc_ent
                    count += 1

                # Document 4 : processus métier
                for proc in raw.get("processus_metier", []):
                    doc_proc = {
                        "name": f"PROCESS_{proc.get('code','')}",
                        "type": "business_process",
                        "code": proc.get("code", ""),
                        "description": proc.get("description", ""),
                        "nom": proc.get("nom", ""),
                        "declencheur": proc.get("declencheur", ""),
                        "_source": "presentation",
                        "_file": "brasil_presentation.json",
                    }
                    doc_proc["_text"] = f"{proc.get('code','')} {proc.get('nom','')} {proc.get('description','')} {proc.get('declencheur','')}"
                    self._indexes["canonical"].add_doc(doc_proc, "_text")
                    count += 1

                # Document 5 : incidents fréquents
                for inc in raw.get("incidents_frequents", []):
                    doc_inc = {
                        "name": f"INCIDENT_{inc.get('type','')}",
                        "type": "known_incident",
                        "incident_type": inc.get("type", ""),
                        "description": inc.get("description", ""),
                        "action_n3": inc.get("action_n3", ""),
                        "_source": "presentation",
                        "_file": "brasil_presentation.json",
                    }
                    doc_inc["_text"] = f"{inc.get('type','')} {inc.get('description','')} {inc.get('action_n3','')}"
                    self._indexes["canonical"].add_doc(doc_inc, "_text")
                    count += 1

                # Document 6 : procédures clés
                for proc in raw.get("procedures_cles", []):
                    doc_p = {
                        "name": f"PROC_{proc.get('ref','').replace(' ','_')}",
                        "type": "procedure",
                        "ref": proc.get("ref", ""),
                        "nom": proc.get("nom", ""),
                        "description": proc.get("description", ""),
                        "_source": "presentation",
                        "_file": "brasil_presentation.json",
                    }
                    doc_p["_text"] = f"{proc.get('ref','')} {proc.get('nom','')} {proc.get('description','')}"
                    self._indexes["canonical"].add_doc(doc_p, "_text")
                    count += 1

                # Document 7 : systèmes connectés
                for sys_name, sys_data in raw.get("systemes_connectes", {}).items():
                    doc_sys = {
                        "name": f"SYSTEM_{sys_name.replace(' ','_').upper()}",
                        "type": "connected_system",
                        "system": sys_name,
                        "role": sys_data.get("role", ""),
                        "protocole": sys_data.get("protocole", ""),
                        "direction": sys_data.get("direction", ""),
                        "_source": "presentation",
                        "_file": "brasil_presentation.json",
                    }
                    doc_sys["_text"] = f"{sys_name} {sys_data.get('role','')} {sys_data.get('protocole','')} {sys_data.get('direction','')}"
                    self._indexes["canonical"].add_doc(doc_sys, "_text")
                    self._entities[sys_name.upper()] = doc_sys
                    count += 1

                # Document 8 : contraintes techniques
                for cstr in raw.get("contraintes_techniques", []):
                    doc_c = {
                        "name": cstr.get("ref", ""),
                        "type": "constraint",
                        "ref": cstr.get("ref", ""),
                        "description": cstr.get("description", ""),
                        "_source": "presentation",
                        "_file": "brasil_presentation.json",
                    }
                    doc_c["_text"] = f"{cstr.get('ref','')} {cstr.get('description','')}"
                    self._indexes["canonical"].add_doc(doc_c, "_text")
                    self._entities[cstr.get("ref","").upper()] = doc_c
                    count += 1

                # Résumé chatbot global
                summary_text = raw.get("chatbot_knowledge_summary", "")
                if summary_text:
                    doc_summary = {
                        "name": "BRASIL_CHATBOT_SUMMARY",
                        "type": "chatbot_summary",
                        "content": summary_text,
                        "_source": "presentation",
                        "_file": "brasil_presentation.json",
                    }
                    doc_summary["_text"] = summary_text
                    self._indexes["canonical"].add_doc(doc_summary, "_text")
                    self._entities["CHATBOT_SUMMARY"] = doc_summary
                    count += 1

                logger.info(f"Knowledge Layer: Brasil presentation loaded ({count} items)")
            except Exception as e:
                logger.warning(f"Failed to load brasil_presentation.json: {e}")
        for f in canonical_files:
            if not f.exists():
                continue
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                # Flatten to list
                for key in ("entities", "workflows", "rules"):
                    items = raw.get(key, [])
                    if isinstance(items, list):
                        for item in items:
                            text = _dict_to_text(item)
                            doc = {**item, "_text": text, "_source": "canonical", "_file": f.name}
                            self._indexes["canonical"].add_doc(doc, "_text")
                            # Also build entity lookup
                            name = item.get("name", item.get("id", ""))
                            if name:
                                self._entities[name.upper()] = item
                            count += 1
                # Handle top-level list
                if isinstance(raw, list):
                    for item in raw:
                        text = _dict_to_text(item)
                        doc = {**item, "_text": text, "_source": "canonical", "_file": f.name}
                        self._indexes["canonical"].add_doc(doc, "_text")
                        count += 1
            except Exception as e:
                logger.warning(f"Failed to load {f}: {e}")
        self._indexes["canonical"].build()
        logger.info(f"Knowledge Layer: loaded {count} canonical items")

        # ── Inject BRASIL ontology & knowledge base ───────────────────────
        self._inject_brasil_knowledge_base()

    def _inject_brasil_knowledge_base(self):
        """Inject real BRASIL workflows, exceptions, entities from ontology."""
        try:
            from app.services.chatbot.ontology import (
                CANONICAL_ENTITIES, WORKFLOW_CATALOG, EXCEPTION_CATALOG,
            )
            from app.services.chatbot.brasil_knowledge_base import (
                INTENT_TO_RESOURCES, TABLE_TO_JAVA_CLASSES, FR_CATALOG,
            )
            injected = 0

            # Inject workflows
            for wf_id, wf in WORKFLOW_CATALOG.items():
                doc = {
                    "name": wf_id,
                    "type": "workflow",
                    "label": wf.get("label", wf_id),
                    "tables": " ".join(wf.get("tables", [])),
                    "exceptions": " ".join(wf.get("exceptions", [])),
                    "steps": " ".join(wf.get("steps", [])),
                    "states": str(wf.get("states", {})),
                    "_source": "brasil_ontology",
                    "_text": f"workflow {wf.get('label',wf_id)} tables: {' '.join(wf.get('tables',[]))} "
                             f"exceptions: {' '.join(wf.get('exceptions',[]))} "
                             f"steps: {' '.join(wf.get('steps',[]))}",
                }
                self._indexes["canonical"].add_doc(doc, "_text")
                self._entities[wf_id] = doc
                injected += 1

            # Inject exceptions
            for exc_name, exc_info in EXCEPTION_CATALOG.items():
                doc = {
                    "name": exc_name,
                    "type": "exception",
                    "context": exc_info.get("context", ""),
                    "tables": " ".join(exc_info.get("related_tables", [])),
                    "workflow": exc_info.get("workflow", ""),
                    "_source": "brasil_ontology",
                    "_text": f"exception {exc_name} {exc_info.get('context','')} "
                             f"tables: {' '.join(exc_info.get('related_tables',[]))}",
                }
                self._indexes["canonical"].add_doc(doc, "_text")
                self._entities[exc_name.upper()] = doc
                injected += 1

            # Inject canonical entities
            for ent_id, ent in CANONICAL_ENTITIES.items():
                doc = {
                    "name": ent_id,
                    "type": "canonical_entity",
                    "label": ent.label,
                    "description": ent.description,
                    "aliases": " ".join(ent.aliases),
                    "tables": " ".join(ent.related_tables),
                    "_source": "brasil_ontology",
                    "_text": f"{ent.label} {ent.description} {' '.join(ent.aliases)} "
                             f"tables: {' '.join(ent.related_tables)}",
                }
                self._indexes["canonical"].add_doc(doc, "_text")
                self._entities[ent_id] = doc
                injected += 1

            # Inject FR catalog
            for fr_id, fr_info in FR_CATALOG.items():
                doc = {
                    "name": fr_id,
                    "type": "functional_requirement",
                    "label": fr_info.get("label", ""),
                    "workflow": fr_info.get("workflow", ""),
                    "description": str(fr_info.get("states", fr_info.get("description", ""))),
                    "_source": "brasil_ontology",
                    "_text": f"FR {fr_id} {fr_info.get('label','')} {fr_info.get('workflow','')}",
                }
                self._indexes["canonical"].add_doc(doc, "_text")
                self._entities[fr_id] = doc
                injected += 1

            self._indexes["canonical"].build()
            logger.info(f"Knowledge Layer: injected {injected} BRASIL ontology items")
        except Exception as e:
            logger.warning(f"[KnowledgeLayer] Failed to inject BRASIL knowledge base: {e}")

    def _load_schema_knowledge(self):
        """
        Charge le schéma extrait de brasil_prod (brasil_schema_knowledge.py).
        Injecte: tables+colonnes, FK, triggers, états métier, row counts,
        indexes, séquences, vues et fonctions.
        """
        try:
            from app.services.chatbot import brasil_schema_knowledge as sk
        except ImportError:
            logger.info("[KnowledgeLayer] brasil_schema_knowledge.py non disponible — lancer extract_schema_knowledge.py")
            return

        injected = 0

        # 1. Injecter chaque table avec ses colonnes + FK + états + index + triggers
        table_cols   = getattr(sk, "TABLE_COLUMNS",   {})
        fk_graph     = getattr(sk, "FK_GRAPH",        {})
        reverse_fk   = getattr(sk, "REVERSE_FK",      {})
        state_cols   = getattr(sk, "STATE_COLUMNS",   {})
        table_stats  = getattr(sk, "TABLE_STATS",     {})
        trigger_map  = getattr(sk, "TRIGGERS",        {})
        pk_map       = getattr(sk, "PRIMARY_KEYS",    {})
        index_map    = getattr(sk, "INDEXES",         {})
        sequence_map = getattr(sk, "SEQUENCES",       {})
        view_map     = getattr(sk, "VIEWS",           {})
        alias_map    = getattr(sk, "TABLE_ALIAS_TO_CANONICAL", {})

        table_to_document = getattr(sk, "table_to_document", None)

        for table_name in getattr(sk, "REAL_SQL_TABLES", table_cols.keys()):
            if table_to_document:
                doc = table_to_document(table_name)
            else:
                cols = table_cols.get(table_name, [])
                col_desc = ", ".join(
                    f"{c['col']} {c['type']}" + (f"({c['max_len']})" if c.get("max_len") else "")
                    for c in cols[:30]
                )
                fk_desc = "; ".join(
                    f"{f['col']}→{f['parent']}.{f['parent_col']}"
                    for f in fk_graph.get(table_name, [])
                )
                children = ", ".join(reverse_fk.get(table_name, [])[:8])
                states_txt = ""
                for col, info in state_cols.get(table_name, {}).items():
                    vals = info.get("values", [])
                    if vals:
                        states_txt += f"{col} ∈ {{{','.join(vals)}}} "
                pk = ", ".join(pk_map.get(table_name, []))
                stats = table_stats.get(table_name, {})
                triggers = "; ".join(t["name"] for t in trigger_map.get(table_name, []))
                doc = {
                    "name":        table_name,
                    "type":        "schema_table",
                    "table":       table_name,
                    "columns":     col_desc,
                    "pk":          pk,
                    "fk":          fk_desc,
                    "children":    children,
                    "state_cols":  states_txt,
                    "triggers":    triggers,
                    "live_rows":   stats.get("live_rows"),
                    "size":        stats.get("size"),
                    "_source":     "brasil_prod_schema",
                    "_text":       (
                        f"table {table_name} colonnes: {col_desc} PK: {pk} FK: {fk_desc} "
                        f"referenced_by: {children} etats: {states_txt} triggers: {triggers}"
                    ),
                }

            # enrichissement d'index avec les métadonnées brutes
            doc["indexes"] = index_map.get(table_name, [])
            doc["triggers"] = trigger_map.get(table_name, [])
            doc["sequence_refs"] = [
                {"name": seq_name, **seq_info}
                for seq_name, seq_info in sequence_map.items()
                if seq_info.get("owned_table") == table_name
            ]
            doc["views"] = [
                view_name for view_name, defn in view_map.items()
                if table_name in (defn or "")
            ]
            doc["relations"] = fk_graph.get(table_name, [])
            doc["incoming_relations"] = reverse_fk.get(table_name, [])
            doc["row_count"] = table_stats.get(table_name)

            self._indexes["canonical"].add_doc(doc, "_text")
            self._entities[table_name.upper()] = doc
            injected += 1

        # 1.b Injecter les alias legacy → tables canoniques pour absorber les anciens noms
        for alias_name, canonical_name in alias_map.items():
            canonical_doc = self._entities.get(canonical_name.upper())
            if not canonical_doc:
                continue
            alias_doc = {
                "name": alias_name,
                "type": "schema_table_alias",
                "canonical_table": canonical_name,
                "_source": "brasil_prod_schema_alias",
                "_text": (
                    f"alias legacy {alias_name} correspond à la table canonique {canonical_name}. "
                    f"{canonical_doc.get('_text', '')}"
                ),
            }
            self._indexes["canonical"].add_doc(alias_doc, "_text")
            self._entities[alias_name.upper()] = alias_doc
            injected += 1

        # 2. Injecter les fonctions PostgreSQL
        functions = getattr(sk, "FUNCTIONS", {})
        for fn_name, fn_info in functions.items():
            doc = {
                "name":    fn_name,
                "type":    "pg_function",
                "kind":    fn_info.get("kind", "FUNCTION"),
                "args":    fn_info.get("args", ""),
                "returns": fn_info.get("returns", ""),
                "language":fn_info.get("language", ""),
                "_source": "brasil_prod_schema",
                "_text":   f"fonction {fn_name} {fn_info.get('kind','')} {fn_info.get('args','')} {fn_info.get('returns','')}",
            }
            self._indexes["canonical"].add_doc(doc, "_text")
            injected += 1

        # 3. Injecter les index comme artefacts de recherche
        for table_name, items in index_map.items():
            for idx in items:
                doc = {
                    "name": idx.get("name"),
                    "type": "schema_index",
                    "table": table_name,
                    "unique": idx.get("unique"),
                    "primary": idx.get("primary"),
                    "columns": idx.get("columns"),
                    "index_type": idx.get("type"),
                    "definition": idx.get("definition"),
                    "_source": "brasil_prod_schema",
                    "_text": f"index {idx.get('name')} table {table_name} columns {idx.get('columns')} unique {idx.get('unique')}",
                }
                self._indexes["canonical"].add_doc(doc, "_text")
                injected += 1

        # 4. Injecter les triggers
        for table_name, items in trigger_map.items():
            for trg in items:
                doc = {
                    "name": trg.get("name"),
                    "type": "schema_trigger",
                    "table": table_name,
                    "event": trg.get("event"),
                    "timing": trg.get("timing"),
                    "orientation": trg.get("orientation"),
                    "condition": trg.get("condition"),
                    "body": trg.get("body"),
                    "_source": "brasil_prod_schema",
                    "_text": f"trigger {trg.get('name')} table {table_name} event {trg.get('event')} timing {trg.get('timing')} body {trg.get('body')}",
                }
                self._indexes["canonical"].add_doc(doc, "_text")
                injected += 1

        # 5. Injecter les séquences
        for seq_name, seq in sequence_map.items():
            doc = {
                "name": seq_name,
                "type": "schema_sequence",
                "owned_table": seq.get("owned_table"),
                "owned_column": seq.get("owned_column"),
                "data_type": seq.get("data_type"),
                "start_value": seq.get("start_value"),
                "increment": seq.get("increment"),
                "_source": "brasil_prod_schema",
                "_text": f"sequence {seq_name} owns {seq.get('owned_table')}.{seq.get('owned_column')} type {seq.get('data_type')}",
            }
            self._indexes["canonical"].add_doc(doc, "_text")
            injected += 1

        # 6. Injecter les vues
        for view_name, defn in view_map.items():
            doc = {
                "name": view_name,
                "type": "schema_view",
                "definition": defn,
                "_source": "brasil_prod_schema",
                "_text": f"view {view_name} {defn}",
            }
            self._indexes["canonical"].add_doc(doc, "_text")
            injected += 1

        self._indexes["canonical"].build()
        logger.info(f"[KnowledgeLayer] Schéma brasil_prod injecté: {injected} objets (tables+FK+indexes+triggers+sequences+views+functions)")

    def _search_index(
        self,
        source: str,
        query: str,
        entities: List[str],
        top_k: int,
    ) -> List[Dict]:
        index = self._indexes.get(source)
        if not index:
            return []
        # Augment query with entity names
        aug_query = query + " " + " ".join(entities)
        results = index.search(aug_query, top_k=top_k * 2)

        # Re-rank: boost blocks that mention known entities
        scored: List[Tuple[float, Dict]] = []
        for score, doc in results:
            bonus = sum(
                1 for e in entities
                if e.lower() in doc.get("_text", "").lower()
            ) * 0.2
            scored.append((score + bonus, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def _match_log_patterns(self, text: str) -> List[Dict]:
        """Match text against log pattern regex."""
        matches = []
        for pattern in self._log_patterns:
            regex = pattern.get("pattern_regex", "")
            if not regex:
                continue
            try:
                if re.search(regex, text, re.I):
                    matches.append(pattern)
            except re.error:
                pass
        return matches[:5]

    def _match_sfd_constraints(self, query: str, entities: List[str]) -> List[Dict]:
        """Return constraints relevant to the query or named entities."""
        q_lower = query.lower()
        result = []
        for c in self._sfd_constraints:
            desc = (c.get("description", "") + " " + c.get("rule_id", "")).lower()
            entity_match = any(e.lower() in desc for e in entities)
            text_match = any(kw in q_lower for kw in desc.split()[:6] if len(kw) > 3)
            if entity_match or text_match:
                result.append(c)
        return result[:5]

    def _inject_learned_patterns(self, entities: List[str], query: str) -> List[Dict]:
        """
        Pull scored learned patterns from learning_loop for entities in context.
        Uses anti-bias formula: score = min(0.85 + 0.02*visit_count, 0.95) * age_factor * success_factor.
        Import is deferred to avoid circular dependency.
        """
        try:
            from app.services.chatbot.learning_loop import learning_loop  # deferred
        except ImportError:
            return []

        injected: List[Dict] = []
        names_to_check: set = set()
        for e in entities:
            parts = e.split(":")
            names_to_check.add(parts[-1])
            names_to_check.add(e)

        seen_ids: set = set()
        for name in names_to_check:
            patterns = learning_loop.get_patterns_for_entity(name, limit=3)
            for pattern in patterns:
                pid = pattern.get("id", "")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                computed_score = pattern.get("_computed_score", 0.85)
                actions_text = "; ".join(pattern.get("actions_taken", [])[:4])
                content = (
                    f"[LEARNED RESOLUTION — {pattern.get('entity_name', name)}] "
                    f"Problème: {pattern.get('problem_summary', '')} | "
                    f"Cause: {pattern.get('root_cause', '')} | "
                    f"Actions: {actions_text}"
                )
                injected.append({
                    "title": f"Résolution apprise: {pattern.get('root_cause', '')[:60]}",
                    "content": content,
                    "_text": content,
                    "_source": "learned",
                    "_score": computed_score,
                    "hypothesis_id": pattern.get("hypothesis_id", ""),
                    "entity_name": pattern.get("entity_name", name),
                    "confidence": computed_score,
                })

        # Sort by computed score descending
        injected.sort(key=lambda x: x["_score"], reverse=True)
        return injected[:5]

    @staticmethod
    def _block_snippet(block: Dict, source: str) -> str:
        if source == "incidents":
            title = block.get("title", block.get("summary", "Incident"))
            desc = block.get("description", block.get("content", ""))[:200]
            return f"- [{title}]: {desc}"
        elif source == "fr":
            name = block.get("name", block.get("fr_id", "FR"))
            desc = block.get("description", block.get("content", ""))[:200]
            return f"- [{name}]: {desc}"
        elif source in ("logs", "log_patterns"):
            etype = block.get("error_type", block.get("type", "LOG"))
            desc = block.get("pattern_regex", block.get("description", ""))[:150]
            return f"- [{etype}]: {desc}"
        elif source == "sfd_constraints":
            rule_id = block.get("rule_id", "SFD")
            desc = block.get("description", "")[:200]
            return f"- [{rule_id}]: {desc}"
        else:
            name = block.get("name", block.get("id", ""))
            desc = block.get("description", block.get("content", ""))[:150]
            return f"- [{name}]: {desc}"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _incident_to_text(incident: Dict) -> str:
    parts = []
    for field in ("title", "summary", "description", "content", "error_code", "error_message",
                  "resolution", "cause", "equipment_type", "symptoms"):
        v = incident.get(field, "")
        if v:
            parts.append(str(v))
    return " ".join(parts)


def _dict_to_text(d: Dict) -> str:
    parts = []
    for v in d.values():
        if isinstance(v, str) and len(v) > 2:
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(i) for i in v if isinstance(i, str))
    return " ".join(parts)


# Singleton
knowledge_layer = KnowledgeLayer()
