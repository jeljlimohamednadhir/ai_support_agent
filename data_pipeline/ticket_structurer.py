"""
Ticket Structuring Layer — data_pipeline step
Loads tickets from CSV, enriches each ticket via the NLP pipeline,
and produces a structured ticket_structured.json output.

Input : CSV with columns: ticket_id, user_sig / inc_resume / resume, inc_solution, application, ...
Output: data_pipeline/output/ticket_structured.json

Integrates with existing ticket_analyzer.py output.
"""
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    import pandas as pd
except ImportError:
    print("❌ pandas non installé. Lancer: pip install pandas")
    sys.exit(1)

# Add backend to path so we can import app services
BACKEND_DIR = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.nlp.enricher import ticket_enricher, StructuredTicket
from app.services.nlp.preprocessor import preprocessor

OUTPUT_FILE = Path(__file__).parent / "output" / "ticket_structured.json"

# Auto-detect column names (same convention as ticket_analyzer.py)
POSSIBLE_SUMMARY_COLS = [
    "user_sig", "inc_resume", "resume", "summary", "résumé",
    "objet", "titre", "sujet", "libellé", "description courte",
    "description",
]
POSSIBLE_ID_COLS = [
    "ticket_id", "inc_id", "id", "numero", "numéro", "ref",
]
POSSIBLE_SOLUTION_COLS = [
    "inc_solution", "solution", "resolution", "résolution",
    "réponse", "action_prise",
]
POSSIBLE_APP_COLS = [
    "application", "application_module", "inc_element", "composant",
    "component", "système",
]


def detect_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Case-insensitive column detection."""
    cols_lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    return None


def load_csv(csv_path: Path) -> pd.DataFrame:
    """Load and validate the CSV file. Auto-detects separator (comma or semicolon)."""
    if not csv_path.exists():
        print(f"❌ CSV introuvable: {csv_path}")
        sys.exit(1)

    # Detect separator from first line
    for encoding in ("utf-8", "latin-1", "utf-8-sig"):
        try:
            with open(csv_path, encoding=encoding, errors="replace") as f:
                first_line = f.readline()
            sep = ";" if first_line.count(";") > first_line.count(",") else ","
            df = pd.read_csv(
                str(csv_path),
                encoding=encoding,
                sep=sep,
                on_bad_lines="skip",
                low_memory=False,
            )
            # Strip BOM and whitespace from column names
            df.columns = [c.strip().strip('"').strip() for c in df.columns]
            print(f"  📂 Fichier chargé: {len(df)} lignes, séparateur='{sep}', colonnes: {list(df.columns[:8])}...")
            return df
        except Exception:
            continue

    print(f"❌ Impossible de lire le CSV: {csv_path}")
    sys.exit(1)


def process_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Enrich each row of the dataframe with the NLP pipeline.
    Returns list of structured ticket dicts.
    """
    # Detect columns
    id_col      = detect_column(df, POSSIBLE_ID_COLS)
    summary_col = detect_column(df, POSSIBLE_SUMMARY_COLS)
    solution_col = detect_column(df, POSSIBLE_SOLUTION_COLS)
    app_col     = detect_column(df, POSSIBLE_APP_COLS)

    if not summary_col:
        # Try to use any text column
        text_cols = [c for c in df.columns if df[c].dtype == "object"]
        if text_cols:
            summary_col = text_cols[0]
        else:
            print("❌ Impossible de détecter la colonne de texte principal")
            sys.exit(1)

    print(f"  🔎 Colonnes détectées:")
    print(f"     ID      : {id_col or 'Auto-généré'}")
    print(f"     Texte   : {summary_col}")
    print(f"     Solution: {solution_col or 'N/A'}")
    print(f"     App     : {app_col or 'BRASIL (défaut)'}")

    structured_tickets = []
    errors = 0

    for idx, row in df.iterrows():
        try:
            # Extract raw text
            raw_text = str(row.get(summary_col, "")) if summary_col else ""
            if not raw_text or raw_text in ("nan", "NaN", ""):
                continue

            # Ticket ID
            ticket_id = str(row.get(id_col, f"TKT-{idx:04d}")) if id_col else f"TKT-{idx:04d}"

            # Application (from CSV or auto-detected)
            app_from_csv = str(row.get(app_col, "BRASIL")).upper() if app_col else "BRASIL"
            # Normalize app names: BRASIL_CORE → BRASIL, BRASIL_CMD → BRASIL
            for base_app in ["BRASIL", "SEBA", "ARTEMIS", "IPON", "ADELIA", "SCA", "ORCHESTRA"]:
                if base_app in app_from_csv:
                    app_from_csv = base_app
                    break

            # Solution text (added to entity for knowledge enrichment)
            solution_text = ""
            if solution_col:
                solution_text = str(row.get(solution_col, ""))
                if solution_text in ("nan", "NaN"):
                    solution_text = ""

            # Combine for richer NLP input
            full_text = raw_text
            if solution_text:
                full_text = f"{raw_text} | Solution: {solution_text}"

            # Enrich via NLP pipeline
            structured: StructuredTicket = ticket_enricher.enrich(
                raw_text=raw_text,
                ticket_id=ticket_id,
                fallback_application=app_from_csv,
            )

            # Post-process: merge solution signals
            if solution_text:
                sol_codes = preprocessor.extract_error_codes(solution_text)
                for code in sol_codes:
                    if code not in structured.error_codes:
                        structured.error_codes.append(code)
                structured.requires_human_review = False  # Has solution = reviewed

            result = structured.to_dict()
            # Preserve original CSV fields for traceability
            result["_source"] = {
                "csv_row_index": int(idx),
                "original_text": raw_text,
                "solution_text": solution_text,
                "app_from_csv": app_from_csv,
            }
            # Add extra CSV metadata if present
            for extra_col in ["date_debut", "groupe", "statut", "datetime_debut",
                              "datetime_resolution", "inc_priorite", "inc_impact"]:
                if extra_col in df.columns:
                    val = row.get(extra_col, None)
                    if val is not None and str(val) not in ("nan", "NaN", ""):
                        result["_source"][extra_col] = str(val)

            structured_tickets.append(result)

        except Exception as e:
            errors += 1
            logger_print(f"  ⚠️  Erreur ligne {idx}: {e}")
            continue

    print(f"  ✅ {len(structured_tickets)} tickets enrichis ({errors} erreurs)")
    return structured_tickets


def compute_summary_stats(tickets: List[Dict]) -> Dict[str, Any]:
    """Compute summary statistics for the structured ticket set."""
    from collections import Counter

    intents = Counter(t["intent"] for t in tickets)
    incident_types = Counter(t["incident_type"] for t in tickets)
    applications = Counter(t["application"] for t in tickets)
    languages = Counter(t["language"] for t in tickets)
    needs_review = sum(1 for t in tickets if t.get("requires_human_review"))

    return {
        "total_tickets": len(tickets),
        "needs_human_review": needs_review,
        "intents": dict(intents.most_common(15)),
        "incident_types": dict(incident_types.most_common(15)),
        "applications": dict(applications.most_common()),
        "languages": dict(languages),
        "avg_confidence": round(
            sum(t["confidence"] for t in tickets) / max(len(tickets), 1), 3
        ),
        "tickets_with_error_codes": sum(1 for t in tickets if t["error_codes"]),
    }


def logger_print(msg: str):
    """Simple print wrapper for pipeline logging."""
    print(msg)


def run(csv_path: Path, dry_run: bool = False) -> bool:
    """
    Main entry point for ticket structuring step.
    Returns True on success.
    """
    print(f"\n  📋 Structuration tickets depuis: {csv_path}")

    # Load
    df = load_csv(csv_path)

    # Process
    structured_tickets = process_dataframe(df)

    if not structured_tickets:
        print("  ❌ Aucun ticket structuré produit")
        return False

    # Summary stats
    stats = compute_summary_stats(structured_tickets)
    print(f"\n  📊 Statistiques:")
    print(f"     Total           : {stats['total_tickets']}")
    print(f"     Confiance moy.  : {stats['avg_confidence']:.1%}")
    print(f"     Avec codes err. : {stats['tickets_with_error_codes']}")
    print(f"     Revue humaine   : {stats['needs_human_review']}")
    print(f"     Intents top3    : {list(stats['intents'].keys())[:3]}")
    print(f"     Types top3      : {list(stats['incident_types'].keys())[:3]}")

    if dry_run:
        print("  🔍 Mode DRY-RUN — pas d'écriture")
        return True

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        "source_csv": str(csv_path),
        "stats": stats,
        "tickets": structured_tickets,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  💾 Sauvegardé: {OUTPUT_FILE}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ticket Structuring — NLP enrichment pipeline"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).parent / "input" / "tickets.csv",
        help="Path to the input CSV file",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    success = run(args.csv, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
