"""
FR Normalizer — Converts parsed FR documents into StructuredProcedure objects.
Extends the existing fr_parser.py + fr_quality_scorer.py output.

Input : data_pipeline/output/fr_scored.json (from existing pipeline)
Output: data_pipeline/output/fr_normalized.json

Produces structured procedures with:
  - symptoms, root_cause, diagnostic_steps, resolution_steps
  - application, related_systems
  - trust_score, confidence_level
  - metadata for RAG indexing
"""
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add backend to path
BACKEND_DIR = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.nlp.preprocessor import preprocessor
try:
    from app.services.nlp.enricher import KNOWN_SYSTEMS
except ImportError:
    KNOWN_SYSTEMS: dict = {
        "BRASIL": ["brasil", "b4002", "badb", "bsf"],
        "SEBA": ["seba"],
        "ARTEMIS": ["artemis"],
        "IPON": ["ipon"],
        "ADELIA": ["adelia"],
        "SCA": ["sca"],
        "ORCHESTRA": ["orchestra", "orch"],
    }
from app.services.nlp.taxonomy import find_incident_type

FR_SCORED_FILE = Path(__file__).parent / "output" / "fr_scored.json"
OUTPUT_FILE    = Path(__file__).parent / "output" / "fr_normalized.json"

# Trust level thresholds (same as canonical_builder.py)
TRUST_HIGH   = 80
TRUST_MEDIUM = 60
TRUST_LOW    = 30


# ─────────────────────────────────────────────
# Structured Procedure Schema
# ─────────────────────────────────────────────

def build_structured_procedure(fr: Dict) -> Optional[Dict[str, Any]]:
    """
    Convert a scored FR dict into a StructuredProcedure dict.
    Returns None if quality is too low (inutilisable).
    """
    quality_label = fr.get("quality_label", "inutilisable")
    if quality_label == "inutilisable":
        return None

    quality_score = fr.get("quality_score", 0)
    title = fr.get("title", "").strip()
    fr_number = str(fr.get("number", "???"))
    sections = fr.get("sections", {})
    full_text = fr.get("full_text", "")

    # ── Detect application & related systems ─────────────────────────
    application, related_systems = _detect_systems_in_fr(title + " " + full_text)

    # ── Extract symptoms ──────────────────────────────────────────────
    symptoms = _extract_list_from_section(
        sections,
        ["symptoms", "problème", "erreur", "context"],
        full_text,
    )

    # ── Extract root cause ────────────────────────────────────────────
    root_cause = _extract_root_cause(sections, full_text)

    # ── Extract diagnostic steps ──────────────────────────────────────
    diagnostic_steps = _extract_steps_from_section(
        sections,
        ["causes", "diagnostic"],
        full_text,
        is_diagnostic=True,
    )

    # ── Extract resolution steps ──────────────────────────────────────
    resolution_steps = _extract_steps_from_section(
        sections,
        ["procedure", "résolution", "solution"],
        full_text,
        is_diagnostic=False,
    )

    # ── Extract error codes ───────────────────────────────────────────
    error_codes = preprocessor.extract_error_codes(title + " " + full_text)

    # ── Detect incident type ──────────────────────────────────────────
    incident_type = find_incident_type(title + " " + full_text)

    # ── Compute trust score ───────────────────────────────────────────
    trust_score, confidence_level = _compute_trust(
        quality_score=quality_score,
        quality_label=quality_label,
        has_symptoms=len(symptoms) > 0,
        has_root_cause=bool(root_cause),
        has_steps=len(resolution_steps) > 0,
    )

    # ── Source quality metadata ───────────────────────────────────────
    source_quality = {
        "quality_score": quality_score,
        "quality_label": quality_label,
        "has_symptoms": len(symptoms) > 0,
        "has_root_cause": bool(root_cause),
        "has_diagnostic_steps": len(diagnostic_steps) > 0,
        "has_resolution_steps": len(resolution_steps) > 0,
        "word_count": fr.get("word_count", 0),
        "completeness_score": round(
            sum([
                1 if symptoms else 0,
                1 if root_cause else 0,
                1 if diagnostic_steps else 0,
                1 if resolution_steps else 0,
            ]) / 4.0, 2
        ),
    }

    return {
        "procedure_id": f"FR-{fr_number}",
        "title": title,
        "application": application,
        "related_systems": related_systems,
        "symptoms": symptoms,
        "root_cause": root_cause,
        "diagnostic_steps": diagnostic_steps,
        "resolution_steps": resolution_steps,
        "error_codes": error_codes,
        "incident_type": incident_type,
        "related_incidents": [],              # Filled by clustering step
        "confidence_level": confidence_level,
        "trust_score": round(trust_score, 3),
        "validated_by": "human",             # FR = human-written, inherently reviewed
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
        "source_fr_number": fr_number,
        "source_quality": source_quality,
        # For RAG chunking
        "_chunks": _prepare_rag_chunks(
            procedure_id=f"FR-{fr_number}",
            application=application,
            related_systems=related_systems,
            incident_type=incident_type,
            error_codes=error_codes,
            trust_score=trust_score,
            confidence_level=confidence_level,
            symptoms=symptoms,
            root_cause=root_cause,
            diagnostic_steps=diagnostic_steps,
            resolution_steps=resolution_steps,
        ),
    }


# ─────────────────────────────────────────────
# Extraction helpers
# ─────────────────────────────────────────────

def _detect_systems_in_fr(text: str):
    """Detect application and related systems from FR text."""
    text_lower = text.lower()
    found = []
    for system, aliases in KNOWN_SYSTEMS.items():
        if any(alias in text_lower for alias in aliases):
            found.append(system)
    application = found[0] if found else "BRASIL"
    if "BRASIL" not in found:
        found.insert(0, "BRASIL")
    return application, found


def _extract_list_from_section(
    sections: Dict,
    section_keys: List[str],
    full_text: str,
) -> List[str]:
    """Extract bullet/sentence list from named sections."""
    text = ""
    for key in section_keys:
        val = sections.get(key, "")
        if isinstance(val, list):
            text = " ".join(val)
        elif isinstance(val, str):
            text = val
        if text.strip():
            break

    if not text.strip():
        return []

    # Split into sentences/items
    items = []
    for line in re.split(r"[•\-\n;]", text):
        line = line.strip()
        if len(line) > 15:
            items.append(line[:300])  # Cap length
    return items[:8]


def _extract_root_cause(sections: Dict, full_text: str) -> str:
    """Extract root cause from causes/diagnostic section."""
    for key in ["causes", "diagnostic", "origine", "raison"]:
        val = sections.get(key, "")
        if isinstance(val, list):
            val = " ".join(val)
        if val and len(val.strip()) > 10:
            # Return first meaningful sentence
            sentences = re.split(r"[.\n]", val)
            for s in sentences:
                if len(s.strip()) > 15:
                    return s.strip()[:400]

    # Fallback: look for "cause" keyword in full text
    matches = re.findall(r"(?:cause|origine|raison)[:\s]+([^\n.]{20,200})", full_text, re.IGNORECASE)
    if matches:
        return matches[0].strip()
    return ""


def _extract_steps_from_section(
    sections: Dict,
    section_keys: List[str],
    full_text: str,
    is_diagnostic: bool = False,
) -> List[str]:
    """Extract numbered/bulleted steps from a section."""
    text = ""
    for key in section_keys:
        val = sections.get(key, "")
        if isinstance(val, list):
            text = " ".join(val)
        elif isinstance(val, str):
            text = val
        if text.strip():
            break

    if not text.strip():
        return []

    steps = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for i, line in enumerate(lines, 1):
        if len(line) > 10:
            # Normalize numbering
            clean = re.sub(r"^\d+[\.\)]\s*", "", line)
            if clean:
                steps.append(f"{i}. {clean[:300]}")
    return steps[:12]


def _compute_trust(
    quality_score: int,
    quality_label: str,
    has_symptoms: bool,
    has_root_cause: bool,
    has_steps: bool,
) -> tuple:
    """
    Compute trust score for a structured procedure.

    Formula:
      T = w1*S_source + w2*S_completeness + w3*S_validation
      w1=0.50, w2=0.30, w3=0.20

    S_source: based on quality_score from FR quality scorer
    S_completeness: presence of key sections
    S_validation: human-written FR = 1.0
    """
    # S_source: map quality_score 0-100 → 0.0-1.0
    s_source = min(quality_score / 100.0, 1.0)

    # S_completeness
    completeness_count = sum([has_symptoms, has_root_cause, has_steps])
    s_completeness = completeness_count / 3.0

    # S_validation: FR = human written
    s_validation = 1.0

    trust = 0.50 * s_source + 0.30 * s_completeness + 0.20 * s_validation

    if trust >= 0.80:
        confidence_level = "high"
    elif trust >= 0.60:
        confidence_level = "medium"
    elif trust >= 0.40:
        confidence_level = "low"
    else:
        confidence_level = "very_low"

    return trust, confidence_level


def _prepare_rag_chunks(
    procedure_id: str,
    application: str,
    related_systems: List[str],
    incident_type: str,
    error_codes: List[str],
    trust_score: float,
    confidence_level: str,
    symptoms: List[str],
    root_cause: str,
    diagnostic_steps: List[str],
    resolution_steps: List[str],
) -> List[Dict]:
    """
    Prepare section-based RAG chunks for Qdrant indexing.
    One chunk per section (symptoms / root_cause / diagnostic / resolution).
    """
    base_metadata = {
        "source_type": "procedure",
        "procedure_id": procedure_id,
        "application": application,
        "related_systems": related_systems,
        "incident_type": incident_type,
        "error_codes": error_codes,
        "trust_score": round(trust_score, 3),
        "confidence_level": confidence_level,
        "validated_by": "human",
        "language": "fr",
    }
    chunks = []

    if symptoms:
        chunks.append({
            "chunk_id": f"{procedure_id}_symptoms",
            "section": "symptoms",
            "content": "Symptômes:\n" + "\n".join(f"• {s}" for s in symptoms),
            "metadata": {**base_metadata, "section": "symptoms"},
        })

    if root_cause:
        chunks.append({
            "chunk_id": f"{procedure_id}_root_cause",
            "section": "root_cause",
            "content": f"Cause racine:\n{root_cause}",
            "metadata": {**base_metadata, "section": "root_cause"},
        })

    if diagnostic_steps:
        chunks.append({
            "chunk_id": f"{procedure_id}_diagnostic",
            "section": "diagnostic_steps",
            "content": "Étapes de diagnostic:\n" + "\n".join(diagnostic_steps),
            "metadata": {**base_metadata, "section": "diagnostic_steps"},
        })

    if resolution_steps:
        chunks.append({
            "chunk_id": f"{procedure_id}_resolution",
            "section": "resolution_steps",
            "content": "Étapes de résolution:\n" + "\n".join(resolution_steps),
            "metadata": {**base_metadata, "section": "resolution_steps"},
        })

    return chunks


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def run(dry_run: bool = False) -> bool:
    if not FR_SCORED_FILE.exists():
        print(f"  ❌ fr_scored.json introuvable ({FR_SCORED_FILE})")
        print("     Lancer d'abord: python data_pipeline/fr_quality_scorer.py")
        return False

    with open(FR_SCORED_FILE, "r", encoding="utf-8") as f:
        fr_list = json.load(f)

    print(f"  📂 {len(fr_list)} FRs chargées depuis fr_scored.json")

    procedures = []
    skipped = 0
    for fr in fr_list:
        proc = build_structured_procedure(fr)
        if proc:
            procedures.append(proc)
        else:
            skipped += 1

    # Compute chunk count
    total_chunks = sum(len(p.get("_chunks", [])) for p in procedures)

    print(f"  ✅ {len(procedures)} procédures structurées")
    print(f"  ⏭️  {skipped} FRs ignorées (qualité trop faible)")
    print(f"  🗂️  {total_chunks} chunks RAG préparés")

    # Trust distribution
    trust_levels = {"high": 0, "medium": 0, "low": 0, "very_low": 0}
    for p in procedures:
        trust_levels[p["confidence_level"]] = trust_levels.get(p["confidence_level"], 0) + 1
    print(f"  📊 Confiance: high={trust_levels['high']} medium={trust_levels['medium']} "
          f"low={trust_levels['low']} very_low={trust_levels['very_low']}")

    if dry_run:
        print("  🔍 Mode DRY-RUN — pas d'écriture")
        return True

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_procedures": len(procedures),
        "total_chunks": total_chunks,
        "skipped": skipped,
        "trust_distribution": trust_levels,
        "procedures": procedures,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  💾 Sauvegardé: {OUTPUT_FILE}")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FR Normalizer — structured procedure extraction")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    success = run(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
