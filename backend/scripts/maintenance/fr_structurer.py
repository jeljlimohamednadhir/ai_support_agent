#!/usr/bin/env python3
"""
FR Structurer — BRASIL Knowledge Pipeline
==========================================
Converts every FR .docx file into structured reasoning JSON using the LLM.

Pipeline:
  1. Read each FR .docx  →  extract raw text
  2. Send to LLM with the structuration prompt  →  get JSON
  3. Validate + store to  data/brasil_fr_structured.json
  4. (Optional) inject into Qdrant collection  brasil_frs

Usage:
    python fr_structurer.py                       # process all FRs
    python fr_structurer.py --fr "FR 189"         # process one FR by name
    python fr_structurer.py --skip-qdrant         # skip Qdrant injection
    python fr_structurer.py --reprocess           # overwrite already-processed FRs

Output:
    backend/data/brasil_fr_structured.json        # master JSON array
    backend/data/fr_structured/FR_XXX.json        # one file per FR
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Optional

# ── ensure backend/ is on the path ──────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from docx import Document                           # python-docx
from app.core.llm_client import llm_client
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
FR_FOLDER          = BACKEND_DIR / "FR"
OUT_DIR            = BACKEND_DIR / "data" / "fr_structured"
MASTER_JSON        = BACKEND_DIR / "data" / "brasil_fr_structured.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── LLM Structuration Prompt ─────────────────────────────────────────────────
_STRUCTURATION_PROMPT = """\
You are a senior N3 telecom expert specialized in BRASIL Network Management system.

Your task is to transform a Functional Requirement (FR) into structured reasoning knowledge
used by an advanced troubleshooting engine.

━━━━━━━━━━━━━━━━━━━━━━━
🎯 OBJECTIVE
━━━━━━━━━━━━━━━━━━━━━━━

Convert the FR into a structured JSON object that enables:
- root cause analysis
- incident correlation (FR + incidents + logs)
- constraint validation (SFD rules)
- expert-level troubleshooting

━━━━━━━━━━━━━━━━━━━━━━━
📥 FR CONTENT
━━━━━━━━━━━━━━━━━━━━━━━

{fr_text}

━━━━━━━━━━━━━━━━━━━━━━━
📦 OUTPUT FORMAT (STRICT JSON ONLY)
━━━━━━━━━━━━━━━━━━━━━━━

{{
  "id": "FR-<short-title>-<index>",
  "application": "BRASIL",
  "title": "...",

  "intents": [],

  "entities": [
    {{
            "type": "EQUIPMENT | RESOURCE | SERVICE | ORDER | SYSTEM | DATABASE_TABLE",
      "examples": []
    }}
  ],

  "symptoms": [
    {{
      "text": "...",
      "type": "constraint_violation | system_error | data_inconsistency | state_lock"
    }}
  ],

  "causal_graph": [
    {{
      "from": "symptom:...",
      "to": "cause:...",
      "confidence": 0.0
    }},
    {{
      "from": "cause:...",
      "to": "root:...",
      "confidence": 0.0
        }},
        {{
            "from": "cause:...",
            "to": "root:...",
            "confidence": 0.0
    }}
  ],

  "root_cause": {{
    "class": "A|B|C|D",
    "label": "...",
    "confidence": 0.0
  }},

  "blocking_conditions": [],

  "diagnostic": [
    {{
      "step": "...",
      "type": "query | check | analysis"
    }}
  ],

  "resolution": [
    {{
      "action": "...",
            "type": "data_fix | config_fix | retry | cleanup | check"
    }}
  ],

  "sfd_rules": [
    {{
      "rule": "...",
      "type": "hard_constraint | soft_constraint"
    }}
  ],

  "evidence_tags": [],

  "confidence_score": 0.0,

  "pattern_signature": "<primary_intent>|<main_entity>|<key_technical_marker>|<root_cause_type>",

  "trigger_signals": [
    "...",
    "..."
  ],

  "non_blocking_conditions": [
    "...",
    "..."
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━
🧠 DOMAIN RULES (BRASIL)
━━━━━━━━━━━━━━━━━━━━━━━

ROOT CAUSE CLASSES:
A = configuration issue
B = system bug
C = data inconsistency (ghost/orphan data)
D = external dependency (Artemis, API, MQ)

SYMPTOM TYPES:
- constraint_violation  → suppression impossible, bloqué
- system_error          → erreur 1300, exception, crash
- data_inconsistency    → fantôme, orphelin, désynchronisé
- state_lock            → IN_PROGRESS, verrouillé, commande bloquée

━━━━━━━━━━━━━━━━━━━━━━━
⚠️ STRICT RULES
━━━━━━━━━━━━━━━━━━━━━━━

- Output MUST be valid JSON only (no text before or after)
- NO generic explanations
- NO hallucinated rules
- MUST reflect BRASIL technical logic
- MUST build a causal chain (symptom → cause → root cause)
- MUST include actionable diagnostic steps
- MUST include real resolution actions (not vague advice)

━━━━━━━━━━━━━━━━━━━━━━━
🧩 ENHANCED REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━

- intents MUST be normalized system intents (e.g. delete_equipment, update_service, diagnose_incident)
- causal_graph MUST include at least 3 steps: symptom → intermediate cause → root cause
- entities MUST separate business entities from technical objects (EQUIPMENT + DATABASE_TABLE)
- resolution MUST include precise technical actions (table names, SQL fragments, verification step)
- Avoid generic wording like "clean data": specify WHERE and HOW

━━━━━━━━━━━━━━━━━━━━━━━
🔒 STRICT NORMALIZATION RULES
━━━━━━━━━━━━━━━━━━━━━━━

- Only ONE root cause class allowed (no “or”, no combination, no class B if class C applies)
- causal_graph nodes MUST use concrete references (table names, field names, not abstractions)
- causal_graph format: "from": "symptom:<text>", "to": "cause:<concrete>", or "to": "root:<label>"
- resolution actions MUST be ordered: data_fix first, then check, then retry
- resolution MUST NOT contain policy steps (e.g. “Conserver historique pendant 30 jours” is FORBIDDEN)
- entities examples MUST NOT mix business names and table names in the same entry
- One entry type EQUIPMENT → examples = ["DSLAM"], one entry type DATABASE_TABLE → examples = ["t_res_prod_controlers", ...]

━━━━━━━━━━━━━━━━━━━━━━━
🧠 ENRICHMENT FIELDS
━━━━━━━━━━━━━━━━━━━━━━━

pattern_signature: "<intent>|<entity>|<key_table>|<rc_type>"  (rc_type: data_orphan|config_error|system_bug|external_dependency|state_lock)
trigger_signals: 3-6 lowercase phrases from symptoms/title matching real user wording
non_blocking_conditions: logical inverse of blocking_conditions, referencing concrete tables/fields

━━━━━━━━━━━━━━━━━━━━━━━
📚 CANONICAL EXAMPLE
━━━━━━━━━━━━━━━━━━━━━━━

{{"id":"FR-DSLAM-DELETION-189","application":"BRASIL","title":"Suppression DSLAM bloquée","intents":["delete_equipment"],"entities":[{{"type":"EQUIPMENT","examples":["DSLAM"]}},{{"type":"DATABASE_TABLE","examples":["t_res_prod_controlers","t_cards","t_shelfs"]}}],"symptoms":[{{"text":"Suppression DSLAM impossible via IHM","type":"constraint_violation"}}],"causal_graph":[{{"from":"symptom:Suppression DSLAM impossible via IHM","to":"cause:Présence eqpt_id dans t_res_prod_controlers","confidence":0.95}},{{"from":"cause:Présence eqpt_id dans t_res_prod_controlers","to":"cause:Données orphelines non nettoyées","confidence":0.97}},{{"from":"cause:Données orphelines non nettoyées","to":"root:Données orphelines persistantes en base","confidence":0.99}}],"root_cause":{{"class":"C","label":"Données orphelines persistantes en base","confidence":0.96}},"blocking_conditions":["Présence eqpt_id dans t_res_prod_controlers"],"diagnostic":[{{"step":"SELECT eqpt_id FROM t_equipments WHERE eqpt_name='DSLAM'","type":"query"}},{{"step":"SELECT * FROM t_res_prod_controlers WHERE eqpt_id=<ID>","type":"query"}},{{"step":"Vérifier t_cards, t_shelfs","type":"analysis"}}],"resolution":[{{"action":"DELETE FROM t_res_prod_controlers WHERE eqpt_id=<ID>","type":"data_fix"}},{{"action":"DELETE FROM t_cards WHERE eqpt_id=<ID>","type":"data_fix"}},{{"action":"Vérifier absence de références","type":"check"}},{{"action":"Relancer suppression via IHM","type":"retry"}}],"sfd_rules":[{{"rule":"Équipement non supprimable si références en base","type":"hard_constraint"}}],"evidence_tags":["eqpt_id","t_res_prod_controlers","t_cards","t_shelfs"],"confidence_score":0.95,"pattern_signature":"delete_equipment|DSLAM|t_res_prod_controlers|data_orphan","trigger_signals":["suppression impossible","dslam non supprimé","erreur suppression dslam","équipement bloqué suppression"],"non_blocking_conditions":["aucune référence eqpt_id dans t_res_prod_controlers","aucune entrée dans t_cards liée à eqpt_id"]}}
"""

_SYSTEM_PROMPT = (
    "You are a BRASIL N3 expert knowledge engineer. "
    "You ONLY output valid JSON. No prose, no markdown fences, no explanation. "
    "Start your response with { and end with }."
)


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_docx_text(path: Path) -> str:
    """Extract all text from a .docx file, preserving paragraph structure."""
    try:
        doc = Document(str(path))
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        # Also extract tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
        return "\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Failed to read {path.name}: {e}")
        return ""


def truncate_fr_text(text: str, max_chars: int = 3500) -> str:
    """Truncate FR text to avoid exceeding LLM context window."""
    if len(text) <= max_chars:
        return text
    logger.warning(f"FR text truncated from {len(text)} to {max_chars} chars")
    return text[:max_chars] + "\n[... truncated ...]"


# ── JSON extraction ───────────────────────────────────────────────────────────

def extract_json(raw: str) -> Optional[dict]:
    """
    Extract and parse a JSON object from an LLM response.
    Handles cases where the model adds prose/CoT reasoning before the JSON block.
    """
    # Strip markdown fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip()

    # Strip CoT reasoning if model outputs thinking before JSON
    # Look for first { that begins a top-level JSON object
    # (model thinking often appears as prose paragraphs before the JSON)
    # Strategy: find all { positions and try each as a start
    brace_positions = [i for i, c in enumerate(raw) if c == "{"]
    for start in brace_positions:
        end = raw.rfind("}")
        if end <= start:
            continue
        candidate = raw[start : end + 1]
        # Quick sanity: must contain "application" key
        if '"application"' not in candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Try to fix common LLM JSON issues: trailing commas
            fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                continue
    return None


def _is_normalized_intent(intent: str) -> bool:
    """Normalized system intent format: snake_case with at least one underscore."""
    return bool(re.fullmatch(r"[a-z]+(?:_[a-z0-9]+)+", intent or ""))


def _auto_fix(data: dict, fr_name: str) -> dict:
    """Auto-correct common LLM output issues before strict validation."""
    _TABLE_RE = re.compile(r"^t_[a-z_]+$", re.IGNORECASE)

    # Auto-fix: map 'data_inconsistency' → 'data_orphan' in pattern_signature
    pattern_sig = data.get("pattern_signature", "")
    if isinstance(pattern_sig, str) and "data_inconsistency" in pattern_sig:
        data["pattern_signature"] = pattern_sig.replace("data_inconsistency", "data_orphan")
        logger.info(f"[{fr_name}] Auto-fix: mapped pattern_signature data_inconsistency → data_orphan")

    # Auto-fix: collapse excess root nodes in causal_graph (keep only first root)
    causal_graph = data.get("causal_graph", [])
    if isinstance(causal_graph, list):
        root_links = [lnk for lnk in causal_graph if str(lnk.get("to", "")).startswith("root:")]
        if len(root_links) > 1:
            # Keep only the highest-confidence root link
            root_links_sorted = sorted(root_links, key=lambda x: x.get("confidence", 0), reverse=True)
            kept_root = root_links_sorted[0]
            removed_roots = root_links_sorted[1:]
            # Convert removed roots to cause nodes
            for lnk in removed_roots:
                lnk["to"] = lnk["to"].replace("root:", "cause:", 1)
            data["causal_graph"] = causal_graph
            logger.info(f"[{fr_name}] Auto-fix: collapsed {len(removed_roots)} excess root node(s) to cause nodes")

    # 1. Lowercase trigger_signals
    if isinstance(data.get("trigger_signals"), list):
        fixed = [s.lower() if isinstance(s, str) else s for s in data["trigger_signals"]]
        if fixed != data["trigger_signals"]:
            logger.info(f"[{fr_name}] Auto-fix: lowercased trigger_signals")
        data["trigger_signals"] = fixed[:6]  # cap at 6

    # 2. Strip non-t_* entries from DATABASE_TABLE examples
    entities = data.get("entities", [])
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        if str(ent.get("type", "")).upper() == "DATABASE_TABLE":
            orig = ent.get("examples", [])
            filtered = [ex for ex in orig if isinstance(ex, str) and _TABLE_RE.match(ex)]
            if filtered != orig:
                logger.info(f"[{fr_name}] Auto-fix: filtered DATABASE_TABLE examples from {orig} → {filtered}")
            ent["examples"] = filtered

    # 3. Add dummy EQUIPMENT if missing but DATABASE_TABLE is present
    entity_types = {str(e.get("type", "")).upper() for e in entities if isinstance(e, dict)}
    if "DATABASE_TABLE" in entity_types and "EQUIPMENT" not in entity_types:
        # Infer equipment name from title
        title_words = (data.get("title") or fr_name).split()
        equipment_name = next(
            (w for w in title_words if w.upper() in {"DSLAM", "CARD", "PORT", "VLAN", "BAS", "ROUTEUR",
                                                      "CARTE", "SLOT", "REGLETTE", "VC", "VP", "OLT"}),
            "EQUIPMENT_UNKNOWN"
        )
        entities.append({"type": "EQUIPMENT", "examples": [equipment_name]})
        logger.info(f"[{fr_name}] Auto-fix: added EQUIPMENT entity '{equipment_name}'")
        data["entities"] = entities

    # 4. Auto-sort resolution: data_fix before check/retry
    resolution = data.get("resolution", [])
    if isinstance(resolution, list):
        fixes = [a for a in resolution if a.get("type") == "data_fix"]
        others = [a for a in resolution if a.get("type") != "data_fix"]
        reordered = fixes + others
        if reordered != resolution:
            logger.info(f"[{fr_name}] Auto-fix: reordered resolution (data_fix first)")
        data["resolution"] = reordered

    # 5. Normalize resolution type 'analysis' → 'check'
    for action in data.get("resolution", []):
        if isinstance(action, dict) and action.get("type") == "analysis":
            action["type"] = "check"
            logger.info(f"[{fr_name}] Auto-fix: resolution type 'analysis' → 'check'")

    # 6. Remove policy steps from resolution
    _POLICY_PATTERNS = [
        "conserver historique", "keep history", "clean data",
        "nettoyer les données", "corriger les données",
        "30 jours", "pendant x jours",
    ]
    data["resolution"] = [
        a for a in data.get("resolution", [])
        if not any(p in str(a.get("action", "")).lower() for p in _POLICY_PATTERNS)
    ]

    return data


def validate_structured_fr(data: dict, fr_name: str) -> bool:
    """Validate with auto-correction for common LLM deviations."""
    # Auto-fix first
    data = _auto_fix(data, fr_name)

    required = {
        "id", "title", "application", "intents", "entities", "symptoms",
        "causal_graph", "root_cause", "diagnostic", "resolution",
        "sfd_rules", "evidence_tags", "confidence_score",
    }
    missing = required - set(data.keys())
    if missing:
        logger.warning(f"[{fr_name}] Missing keys: {missing}")
        return False

    if data.get("application") != "BRASIL":
        logger.warning(f"[{fr_name}] Invalid application: {data.get('application')}")
        return False

    intents = data.get("intents", [])
    if not isinstance(intents, list) or not intents:
        logger.warning(f"[{fr_name}] intents must be a non-empty list")
        return False
    if not all(isinstance(i, str) and _is_normalized_intent(i) for i in intents):
        logger.warning(f"[{fr_name}] intents must use normalized system format (snake_case)")
        return False

    causal_graph = data.get("causal_graph", [])
    if not isinstance(causal_graph, list) or len(causal_graph) < 3:
        logger.warning(f"[{fr_name}] causal_graph must contain at least 3 links")
        return False
    for link in causal_graph:
        to_val = str(link.get("to", ""))
        if re.fullmatch(r"root:[A-D]", to_val):
            logger.warning(f"[{fr_name}] causal_graph 'to' must be concrete, not '{to_val}'")
            return False

    entities = data.get("entities", [])
    if not isinstance(entities, list) or len(entities) < 1:
        logger.warning(f"[{fr_name}] entities must be non-empty")
        return False
    entity_types = {str(e.get("type", "")).upper() for e in entities if isinstance(e, dict)}
    if "DATABASE_TABLE" not in entity_types:
        logger.warning(f"[{fr_name}] entities must include at least DATABASE_TABLE")
        return False
    _TABLE_RE = re.compile(r"^t_[a-z_]+$", re.IGNORECASE)
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        etype = str(ent.get("type", "")).upper()
        examples = ent.get("examples", [])
        if etype == "EQUIPMENT":
            if any(_TABLE_RE.match(str(ex)) for ex in examples):
                logger.warning(f"[{fr_name}] EQUIPMENT entity must not contain table names: {examples}")
                return False
        elif etype == "DATABASE_TABLE":
            bad = [ex for ex in examples if not _TABLE_RE.match(str(ex))]
            if bad:
                logger.warning(f"[{fr_name}] DATABASE_TABLE still has non-table entries after auto-fix: {bad}")
                return False

    root_cause = data.get("root_cause", {})
    if root_cause.get("class") not in {"A", "B", "C", "D"}:
        logger.warning(f"[{fr_name}] root_cause.class must be one of A/B/C/D")
        return False
    roots_in_graph = [
        link.get("to", "") for link in causal_graph
        if str(link.get("to", "")).startswith("root:")
    ]
    for r in roots_in_graph:
        tail = r[len("root:"):].strip()
        if len(tail) == 1 and tail.upper() in "ABCD":
            logger.warning(f"[{fr_name}] causal_graph uses bare class '{tail}'")
            return False
    if len(roots_in_graph) > 2:
        logger.warning(f"[{fr_name}] causal_graph has {len(roots_in_graph)} root nodes — max 2 allowed")
        return False

    diag_types_allowed = {"query", "check", "analysis"}
    diag = data.get("diagnostic", [])
    if not isinstance(diag, list) or not diag:
        logger.warning(f"[{fr_name}] diagnostic must be a non-empty list")
        return False
    for step in diag:
        if step.get("type") not in diag_types_allowed:
            logger.warning(f"[{fr_name}] invalid diagnostic type: {step.get('type')}")
            return False

    res_types_allowed = {"data_fix", "config_fix", "retry", "cleanup", "check"}
    resolution = data.get("resolution", [])
    if not isinstance(resolution, list) or len(resolution) < 2:
        logger.warning(f"[{fr_name}] resolution must contain at least 2 actions")
        return False
    seen_check_or_retry = False
    for action in resolution:
        if action.get("type") not in res_types_allowed:
            logger.warning(f"[{fr_name}] invalid resolution type: {action.get('type')}")
            return False
        if action.get("type") in {"check", "retry"}:
            seen_check_or_retry = True
        if action.get("type") == "data_fix" and seen_check_or_retry:
            logger.warning(f"[{fr_name}] resolution ordering still wrong after auto-fix")
            return False

    confidence_score = data.get("confidence_score", 0.0)
    if not isinstance(confidence_score, (int, float)) or not (0.0 <= float(confidence_score) <= 1.0):
        logger.warning(f"[{fr_name}] confidence_score must be in [0,1]")
        return False

    # ── Intelligence enrichment fields ──────────────────────────────────
    _VALID_RC_TYPES = {"data_orphan", "config_error", "system_bug", "external_dependency", "state_lock"}
    pattern_sig = data.get("pattern_signature", "")
    if not isinstance(pattern_sig, str) or not pattern_sig:
        logger.warning(f"[{fr_name}] pattern_signature is missing or empty")
        return False
    parts = pattern_sig.split("|")
    if len(parts) != 4:
        logger.warning(f"[{fr_name}] pattern_signature must have exactly 4 pipe-separated parts: {pattern_sig}")
        return False
    if parts[3] not in _VALID_RC_TYPES:
        logger.warning(f"[{fr_name}] pattern_signature root_cause_type '{parts[3]}' not in {_VALID_RC_TYPES}")
        return False
    if not _is_normalized_intent(parts[0]):
        logger.warning(f"[{fr_name}] pattern_signature primary_intent '{parts[0]}' must be snake_case")
        return False

    trigger_signals = data.get("trigger_signals", [])
    if not isinstance(trigger_signals, list) or len(trigger_signals) < 3:
        logger.warning(f"[{fr_name}] trigger_signals must contain at least 3 entries")
        return False
    if not all(isinstance(s, str) and s == s.lower() for s in trigger_signals):
        logger.warning(f"[{fr_name}] trigger_signals still has non-lowercase after auto-fix")
        return False

    non_blocking = data.get("non_blocking_conditions", [])
    if not isinstance(non_blocking, list) or not non_blocking:
        logger.warning(f"[{fr_name}] non_blocking_conditions must be a non-empty list")
        return False
    _vague = ["ok", "correct", "normal", "good"]
    for cond in non_blocking:
        if not isinstance(cond, str) or str(cond).lower().strip() in _vague:
            logger.warning(f"[{fr_name}] non_blocking_conditions contains vague entry: {cond}")
            return False

    return True


# ── LLM call ─────────────────────────────────────────────────────────────────

async def structure_fr(fr_name: str, fr_text: str) -> Optional[dict]:
    """Send FR text to LLM and return parsed structured dict."""
    prompt = _STRUCTURATION_PROMPT.format(fr_text=truncate_fr_text(fr_text))
    try:
        raw = await llm_client.generate(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=0.1,       # low temperature → deterministic JSON
            max_tokens=2048,
        )
        data = extract_json(raw)
        if data is None:
            logger.error(f"[{fr_name}] LLM returned non-parseable JSON:\n{raw[:400]}")
            return None
        # Inject source metadata
        data["_source_file"] = fr_name
        data["_qdrant_id"]   = str(uuid.uuid4())
        if validate_structured_fr(data, fr_name):
            return data
        return None
    except Exception as e:
        logger.error(f"[{fr_name}] LLM call failed: {e}")
        return None


# ── Qdrant injection ──────────────────────────────────────────────────────────

async def inject_into_qdrant(records: list[dict]) -> None:
    """Embed and inject structured FRs into the brasil_frs Qdrant collection."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        from sentence_transformers import SentenceTransformer
        from app.core.config import settings

        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        COLLECTION = "brasil_frs"

        # Create collection if needed
        existing = [c.name for c in client.get_collections().collections]
        if COLLECTION not in existing:
            client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            logger.info(f"[Qdrant] Collection '{COLLECTION}' created")

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L12-v2")
        points = []
        for rec in records:
            # Build a rich text representation for embedding
            symptom_texts  = " ".join(s.get("text", "") for s in rec.get("symptoms", []))
            diag_texts     = " ".join(s.get("step", "") for s in rec.get("diagnostic", []))
            trigger_texts  = " ".join(rec.get("trigger_signals", []))
            embed_text     = f"{rec.get('title', '')} {symptom_texts} {trigger_texts} {diag_texts}"
            vector        = model.encode(embed_text).tolist()

            payload = {
                "id":          rec.get("id", ""),
                "title":       rec.get("title", ""),
                "application": rec.get("application", "BRASIL"),
                "intents":     rec.get("intents", []),
                "root_cause":  rec.get("root_cause", {}),
                "symptoms":    rec.get("symptoms", []),
                "diagnostic":  rec.get("diagnostic", []),
                "resolution":  rec.get("resolution", []),
                "sfd_rules":   rec.get("sfd_rules", []),
                "evidence_tags": rec.get("evidence_tags", []),
                "confidence_score": rec.get("confidence_score", 0.0),
                "pattern_signature":    rec.get("pattern_signature", ""),
                "trigger_signals":      rec.get("trigger_signals", []),
                "non_blocking_conditions": rec.get("non_blocking_conditions", []),
                "source_file": rec.get("_source_file", ""),
            }
            points.append(PointStruct(
                id=rec["_qdrant_id"],
                vector=vector,
                payload=payload,
            ))

        if points:
            client.upsert(collection_name=COLLECTION, points=points)
            logger.info(f"[Qdrant] Injected {len(points)} structured FRs into '{COLLECTION}'")

    except Exception as e:
        logger.error(f"[Qdrant] Injection failed: {e}")


# ── Master JSON helpers ───────────────────────────────────────────────────────

def load_master() -> dict[str, dict]:
    """Load existing master JSON as {source_file: record}."""
    if MASTER_JSON.exists():
        try:
            with open(MASTER_JSON, encoding="utf-8") as f:
                records = json.load(f)
            return {r["_source_file"]: r for r in records if "_source_file" in r}
        except Exception:
            return {}
    return {}


def save_master(records_map: dict[str, dict]) -> None:
    """Save master JSON (sorted by source_file)."""
    records = sorted(records_map.values(), key=lambda r: r.get("_source_file", ""))
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logger.info(f"[Master] Saved {len(records)} records → {MASTER_JSON}")


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run(
    fr_filter: Optional[str] = None,
    skip_qdrant: bool = False,
    reprocess: bool = False,
) -> None:
    docx_files = sorted(FR_FOLDER.glob("*.docx"))
    if not docx_files:
        logger.error(f"No .docx files found in {FR_FOLDER}")
        return

    if fr_filter:
        docx_files = [f for f in docx_files if fr_filter.lower() in f.stem.lower()]
        if not docx_files:
            logger.error(f"No FR matched filter: '{fr_filter}'")
            return

    existing = load_master()
    new_records: list[dict] = []
    skipped = 0

    for docx_path in docx_files:
        fr_name = docx_path.stem

        if not reprocess and fr_name in existing:
            logger.info(f"[SKIP] {fr_name} (already processed)")
            skipped += 1
            continue

        print(f"\n⚙️  Processing: {fr_name}")
        fr_text = extract_docx_text(docx_path)

        if len(fr_text) < 50:
            logger.warning(f"[{fr_name}] Text too short ({len(fr_text)} chars) — skipping")
            continue

        structured = await structure_fr(fr_name, fr_text)
        if structured is None:
            print(f"  ❌ Failed")
            continue

        # Save individual file
        out_file = OUT_DIR / f"{fr_name}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(structured, f, ensure_ascii=False, indent=2)

        existing[fr_name] = structured
        new_records.append(structured)
        print(f"  ✅ {structured.get('title', fr_name)} "
              f"[class={structured.get('root_cause', {}).get('class', '?')}] "
              f"conf={structured.get('confidence_score', 0):.2f}")

    # Update master JSON
    if new_records:
        save_master(existing)

    # Inject new records into Qdrant
    if new_records and not skip_qdrant:
        print(f"\n🔄 Injecting {len(new_records)} records into Qdrant brasil_frs...")
        await inject_into_qdrant(new_records)

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Done — {len(new_records)} processed, {skipped} skipped")
    print(f"   Master: {MASTER_JSON}")
    print(f"   Per-FR: {OUT_DIR}/")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert BRASIL FR .docx → structured JSON")
    parser.add_argument("--fr",          type=str,  default=None,  help="Filter by FR name (partial match)")
    parser.add_argument("--skip-qdrant", action="store_true",       help="Skip Qdrant injection")
    parser.add_argument("--reprocess",   action="store_true",       help="Reprocess already-done FRs")
    args = parser.parse_args()

    asyncio.run(run(
        fr_filter=args.fr,
        skip_qdrant=args.skip_qdrant,
        reprocess=args.reprocess,
    ))


if __name__ == "__main__":
    main()
