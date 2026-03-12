"""
Build Labeled Dataset — Maps raw BRASIL tickets.csv to new L1/L2 taxonomy.

Reads : data_pipeline/input/tickets.csv  (222 tickets, semicolon-delimited)
Writes: data_pipeline/output/tickets_labeled.csv

The output CSV contains all original columns plus:
  - text_ml          : prepared text (user_sig + [SEP] + inc_solution × 2)
  - level_1          : mapped L1 category
  - level_2          : mapped L2 category
  - mapping_source   : "direct" | "fuzzy" | "default"

Usage:
    python data_pipeline/build_labeled_dataset.py
    python data_pipeline/build_labeled_dataset.py --csv path/to/other.csv
    python data_pipeline/build_labeled_dataset.py --review   # also print ambiguous rows
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("❌ pandas not installed. Run: pip install pandas")
    sys.exit(1)

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parents[1]
INPUT_CSV  = Path(__file__).parent / "input" / "tickets.csv"
OUTPUT_CSV = Path(__file__).parent / "output" / "tickets_labeled.csv"

# ── Import taxonomy & helpers from the backend ───────────────────────────────
sys.path.insert(0, str(ROOT / "backend"))
try:
    from app.services.hierarchical_classifier import (
        DEFAULT_TAXONOMY,
        prepare_text,
    )
    TAXONOMY      = DEFAULT_TAXONOMY
    LABEL_MAPPING = TAXONOMY["label_mapping"]
except ImportError as e:
    print(f"⚠  Could not import backend classifier ({e}). Using inline fallback taxonomy.")
    # Inline minimal mapping — mirrors DEFAULT_TAXONOMY label_mapping
    LABEL_MAPPING = {
        "INCOHERENCE DE DONNEES":                         {"level_1": "DATA",         "level_2": "DATA_INCONSISTENCY"},
        "INCOHERENCE DONNEES":                            {"level_1": "DATA",         "level_2": "DATA_INCONSISTENCY"},
        "DONNEES":                                        {"level_1": "DATA",         "level_2": "DATA_INCONSISTENCY"},
        "CORRECTION DE DONNEES":                          {"level_1": "DATA",         "level_2": "DATA_UPDATE_OR_DELETE"},
        "FONCTIONNALITE - DONNEE CORROMPUE":              {"level_1": "DATA",         "level_2": "DATA_CORRUPTION"},
        "INCOHERENCE CORRIGEE PAR OUTIL OU SCRIPT":       {"level_1": "DATA",         "level_2": "DATA_CORRECTION_SCRIPT"},
        "ADMINISTRATION DONNEES - QUALITE DONNEES":       {"level_1": "DATA",         "level_2": "DATA_UPDATE_OR_DELETE"},
        "QUALITE DONNEES":                                {"level_1": "DATA",         "level_2": "DATA_UPDATE_OR_DELETE"},
        "CONFIGURATION RESEAU":                           {"level_1": "DATA",         "level_2": "NETWORK_CONFIGURATION"},
        "BUG APPLICATIF":                                 {"level_1": "APPLICATION",  "level_2": "APPLICATION_BUG"},
        "APPLICATIF":                                     {"level_1": "APPLICATION",  "level_2": "APPLICATION_BUG"},
        "APPLICATION COMPOSANT - FONCTIONNALITE":         {"level_1": "APPLICATION",  "level_2": "APPLICATION_FUNCTIONALITY"},
        "NON CONFORMITE":                                 {"level_1": "APPLICATION",  "level_2": "APPLICATION_CONFIGURATION"},
        "INTERFACE AUTRE":                                {"level_1": "APPLICATION",  "level_2": "APPLICATION_BUG"},
        "TRAITEMENT IMPOSSIBLE - DESCRIPTION INCOMPLETE": {"level_1": "APPLICATION",  "level_2": "APPLICATION_BUG"},
        "NON CONFORMITE PROFIL OU DROITS":                {"level_1": "ACCESS",       "level_2": "ACCESS_RIGHTS"},
        "ACCES":                                          {"level_1": "ACCESS",       "level_2": "ACCESS_RIGHTS"},
        "DROITS":                                         {"level_1": "ACCESS",       "level_2": "ACCESS_RIGHTS"},
        "CONNEXION":                                      {"level_1": "ACCESS",       "level_2": "LOGIN_ISSUE"},
        "DEMANDE DE TRAVAUX":                             {"level_1": "OPERATIONS",   "level_2": "SERVICE_REQUEST"},
        "ASSISTANCE":                                     {"level_1": "OPERATIONS",   "level_2": "SERVICE_REQUEST"},
        "ANNULATION PROCESS":                             {"level_1": "OPERATIONS",   "level_2": "ANNULATION"},
        "ANNULATION UTILISATEUR":                         {"level_1": "OPERATIONS",   "level_2": "ANNULATION"},
        "ORDONNANCEMENT":                                 {"level_1": "OPERATIONS",   "level_2": "SCHEDULING"},
        "BON USAGE":                                      {"level_1": "OPERATIONS",   "level_2": "PROCESS_OPERATION"},
        "UTILISATEUR":                                    {"level_1": "OPERATIONS",   "level_2": "PROCESS_OPERATION"},
        "INFRASTRUCTURE TECHNIQUE - SERVEUR ET RESEAU":   {"level_1": "PROCESS_ERROR","level_2": "SYSTEM_PROCESS_ERROR"},
        "SERVEUR":                                        {"level_1": "PROCESS_ERROR","level_2": "SYSTEM_PROCESS_ERROR"},
        "INTERFACE ORACLE":                               {"level_1": "PROCESS_ERROR","level_2": "SYSTEM_PROCESS_ERROR"},
        "MECONNAISSANCE USAGE":                           {"level_1": "UNKNOWN",      "level_2": "UNDETERMINED"},
        "CAUSE INDETERMINEE":                             {"level_1": "UNKNOWN",      "level_2": "UNDETERMINED"},
        "DESCRIPTION INCOMPLETE":                         {"level_1": "UNKNOWN",      "level_2": "INCOMPLETE_DESCRIPTION"},
    }

    def prepare_text(user_sig: str, inc_solution: str) -> str:
        sig = re.sub(r'\s+', ' ', str(user_sig or "").lower()).strip()
        sol = re.sub(r'\s+', ' ', str(inc_solution or "").lower()).strip()
        parts = [p for p in [sig, sol, sol] if p]
        return " [SEP] ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Core mapping logic
# ─────────────────────────────────────────────────────────────────────────────

def map_label(raw_label: str) -> tuple[dict, str]:
    """
    Map an inc_cause string to (L1, L2) using the taxonomy label_mapping.

    Returns:
        (mapped_dict, source)  where source ∈ {"direct", "fuzzy", "default"}
    """
    key = str(raw_label or "").upper().strip()

    # 1. Direct match
    if key in LABEL_MAPPING:
        return LABEL_MAPPING[key], "direct"

    # 2. Fuzzy: check if key contains any mapping key as substring (or vice-versa)
    for k, v in LABEL_MAPPING.items():
        if key in k or k in key:
            return v, "fuzzy"

    # 3. Default → UNKNOWN
    return {"level_1": "UNKNOWN", "level_2": "UNDETERMINED"}, "default"


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def build(csv_path: Path, review: bool = False) -> pd.DataFrame:
    print(f"📂 Reading: {csv_path}")

    # Auto-detect delimiter
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        sample = f.read(2048)
    sep = ";" if sample.count(";") > sample.count(",") else ","
    print(f"   Delimiter detected: '{sep}'")

    df = pd.read_csv(csv_path, sep=sep, low_memory=False, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    print(f"   {len(df)} rows × {len(df.columns)} columns loaded")

    # ── Identify key columns ─────────────────────────────────────────────────
    def _find_col(candidates: list[str]) -> str | None:
        for c in candidates:
            if c in df.columns:
                return c
        return None

    col_cause    = _find_col(["inc_cause", "cause", "categorie", "category"])
    col_user_sig = _find_col(["user_sig", "description", "inc_commentaire"])
    col_solution = _find_col(["inc_solution", "solution", "resolution"])
    col_resume   = _find_col(["inc_resume", "resume", "summary", "titre"])

    print(f"   inc_cause  → '{col_cause}'")
    print(f"   user_sig   → '{col_user_sig}'")
    print(f"   inc_solution → '{col_solution}'")

    # ── Map labels ────────────────────────────────────────────────────────────
    level_1_list     = []
    level_2_list     = []
    source_list      = []
    text_ml_list     = []
    ambiguous_rows   = []

    for idx, row in df.iterrows():
        raw = row.get(col_cause, "") if col_cause else ""
        mapped, source = map_label(raw)

        level_1_list.append(mapped["level_1"])
        level_2_list.append(mapped["level_2"])
        source_list.append(source)

        # Build prepared text
        user_sig  = row.get(col_user_sig, "")  if col_user_sig  else ""
        solution  = row.get(col_solution, "")  if col_solution  else ""
        resume    = row.get(col_resume,   "")  if col_resume    else ""
        # If inc_solution is empty, fall back to inc_resume
        if not str(solution).strip() and str(resume).strip():
            solution = resume
        text_ml_list.append(prepare_text(user_sig, solution))

        if source in ("fuzzy", "default"):
            ambiguous_rows.append({
                "row": idx,
                "inc_cause": raw,
                "level_1":   mapped["level_1"],
                "level_2":   mapped["level_2"],
                "source":    source,
            })

    df["level_1"]       = level_1_list
    df["level_2"]       = level_2_list
    df["mapping_source"]= source_list
    df["text_ml"]       = text_ml_list

    # ── Stats ─────────────────────────────────────────────────────────────────
    l1_dist  = Counter(level_1_list)
    src_dist = Counter(source_list)

    print(f"\n✅ Label mapping done:")
    for l1, n in sorted(l1_dist.items(), key=lambda x: -x[1]):
        print(f"   {l1:<20} {n:>4} tickets")

    print(f"\n   Mapping sources:")
    for src, n in src_dist.items():
        print(f"   {src:<10} {n:>4}")

    if review and ambiguous_rows:
        print(f"\n⚠  Ambiguous / default-mapped rows ({len(ambiguous_rows)}):")
        for r in ambiguous_rows[:20]:
            print(f"   [{r['row']:>3}] '{r['inc_cause']}' → {r['level_1']} / {r['level_2']}  ({r['source']})")
        if len(ambiguous_rows) > 20:
            print(f"   … and {len(ambiguous_rows) - 20} more")

    return df


def main():
    parser = argparse.ArgumentParser(description="Build labeled training dataset from BRASIL tickets CSV")
    parser.add_argument("--csv",    type=Path, default=INPUT_CSV,  help="Input CSV path")
    parser.add_argument("--out",    type=Path, default=OUTPUT_CSV, help="Output labeled CSV path")
    parser.add_argument("--review", action="store_true",           help="Print ambiguous rows for manual review")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"❌ Input CSV not found: {args.csv}")
        sys.exit(1)

    df = build(args.csv, review=args.review)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"\n💾 Saved: {args.out}  ({len(df)} rows)")

    # Minimal quality check
    empty_text = (df["text_ml"].str.strip() == "").sum()
    if empty_text > 0:
        print(f"⚠  {empty_text} rows have empty text_ml — check user_sig/inc_solution columns")


if __name__ == "__main__":
    main()
