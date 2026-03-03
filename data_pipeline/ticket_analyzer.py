"""
Ticket CSV Analyzer — Analyse des tickets BRASIL 2025
Usage : python data_pipeline/ticket_analyzer.py [--csv path/to/file.csv]
Input : CSV exporté depuis PARKA/JIRA (PARKA_OCEANE_D13_V07.csv ou similaire)
Output: data_pipeline/output/ticket_analysis.json
"""
import json
import re
import sys
import argparse
from pathlib import Path
from collections import Counter
from typing import List, Dict, Optional

try:
    import pandas as pd
except ImportError:
    print("❌ pandas non installé. Lancer: pip install pandas")
    sys.exit(1)


OUTPUT_FILE = Path(__file__).parent / "output" / "ticket_analysis.json"

# Codes d'erreur BRASIL connus
KNOWN_ERROR_CODES = [
    "1300", "9903", "1002", "42C", "B4002", "4002",
    "300", "327", "1583", "135", "136",
]

# Colonnes possibles dans le CSV (on détecte automatiquement)
POSSIBLE_SUMMARY_COLS    = ["summary", "résumé", "objet", "titre", "sujet", "libellé", "description courte"]
POSSIBLE_DESC_COLS       = ["description", "corps", "commentaire", "détail"]
POSSIBLE_STATUS_COLS     = ["status", "statut", "état", "etat"]
POSSIBLE_CREATED_COLS    = ["created", "créé le", "date création", "date de création", "ouverture"]
POSSIBLE_RESOLVED_COLS   = ["resolved", "résolu le", "date résolution", "fermeture"]
POSSIBLE_PRIORITY_COLS   = ["priority", "priorité", "urgence"]
POSSIBLE_COMPONENT_COLS  = ["component", "composant", "application", "système"]


def detect_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Détecte automatiquement une colonne parmi les candidats"""
    cols_lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    return None


def extract_error_codes(text: str) -> List[str]:
    """Extrait les codes d'erreur d'un texte"""
    if not isinstance(text, str):
        return []
    codes = []
    for code in KNOWN_ERROR_CODES:
        if code in text:
            codes.append(code)
    # Codes numériques génériques 4 chiffres
    found = re.findall(r'\b(\d{4})\b', text)
    codes.extend(found)
    return list(set(codes))


def categorize_ticket(text: str) -> str:
    """Catégorise un ticket selon son contenu"""
    text_lower = text.lower() if isinstance(text, str) else ""
    categories = {
        "Suppression_Impossible": ["suppression impossible", "impossible de supprimer", "ne peut pas supprimer"],
        "Erreur_1300": ["1300", "erreur 1300"],
        "VLAN_Blocked": ["vlan bloqué", "vlan occupé", "vlan impossible"],
        "Double_Access": ["double accès", "double access", "double déclaration"],
        "ND_Unknown": ["nd inconnu", "nd introuvable", "nd absent", "noeud inconnu"],
        "DSLAM_Error": ["dslam", "recherche de broche", "compteurs dslam"],
        "Card_Error": ["carte impossible", "suppression carte", "carte manquante"],
        "Counter_Error": ["compteur", "ressource logique", "vc vp", "vlan occupé à tort"],
        "IHM_Error": ["ihm bloquée", "script bloqué", "lancement de script"],
        "Internal_Error": ["internal error", "brasil internal", "b4002", "erreur interne"],
        "Data_Inconsistency": ["incohérence", "incoherence", "données incorrectes"],
        "Configuration_Error": ["configuration", "configurer", "erreur de format"],
    }
    for category, keywords in categories.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "Autre"


def analyze_csv(csv_path: Path) -> dict:
    """Analyse complète du CSV tickets"""
    print(f"📥 Chargement: {csv_path.name}...")

    # Essayer différents encodages et séparateurs
    df = None
    for encoding in ["utf-8", "latin-1", "cp1252", "utf-8-sig"]:
        for sep in [";", ",", "\t"]:
            try:
                df = pd.read_csv(csv_path, encoding=encoding, sep=sep, low_memory=False)
                if len(df.columns) > 3:
                    print(f"  ✅ Chargé avec encoding={encoding}, sep='{sep}'")
                    break
            except Exception:
                continue
        if df is not None and len(df.columns) > 3:
            break

    if df is None or len(df.columns) <= 1:
        raise ValueError(f"Impossible de lire le CSV: {csv_path}")

    print(f"  📊 {len(df)} tickets, {len(df.columns)} colonnes")
    print(f"  Colonnes: {list(df.columns)[:10]}...")

    # Détecter les colonnes importantes
    summary_col   = detect_column(df, POSSIBLE_SUMMARY_COLS)
    desc_col      = detect_column(df, POSSIBLE_DESC_COLS)
    status_col    = detect_column(df, POSSIBLE_STATUS_COLS)
    created_col   = detect_column(df, POSSIBLE_CREATED_COLS)
    priority_col  = detect_column(df, POSSIBLE_PRIORITY_COLS)

    print(f"  Colonnes détectées — summary: {summary_col}, status: {status_col}, created: {created_col}")

    # Combiner summary + description pour l'analyse
    df["_text"] = ""
    if summary_col:
        df["_text"] += df[summary_col].fillna("").astype(str)
    if desc_col:
        df["_text"] += " " + df[desc_col].fillna("").astype(str)

    # Extraire codes d'erreur
    df["_error_codes"] = df["_text"].apply(extract_error_codes)

    # Catégoriser
    df["_category"] = df["_text"].apply(categorize_ticket)

    # ── ANALYSES ────────────────────────────────────

    # 1. Top catégories
    category_counts = df["_category"].value_counts().to_dict()

    # 2. Top codes d'erreur
    all_codes = []
    for codes in df["_error_codes"]:
        all_codes.extend(codes)
    error_code_counts = Counter(all_codes).most_common(20)

    # 3. Statuts
    status_counts = {}
    if status_col:
        status_counts = df[status_col].value_counts().to_dict()

    # 4. Priorités
    priority_counts = {}
    if priority_col:
        priority_counts = df[priority_col].value_counts().to_dict()

    # 5. Top mots-clés (ngrammes simples)
    all_text = " ".join(df["_text"].fillna("").tolist()).lower()
    keywords = extract_top_keywords(all_text)

    # 6. Clusters candidats (catégorie + code erreur)
    cluster_candidates = []
    for category, count in category_counts.items():
        if category == "Autre" or count < 3:
            continue
        # Trouver les codes d'erreur dominants dans cette catégorie
        cat_df = df[df["_category"] == category]
        cat_codes = []
        for codes in cat_df["_error_codes"]:
            cat_codes.extend(codes)
        top_code = Counter(cat_codes).most_common(1)

        cluster_candidates.append({
            "category": category,
            "ticket_count": int(count),
            "dominant_error_code": top_code[0][0] if top_code else None,
            "percentage": round(count / len(df) * 100, 1),
            "sample_summaries": cat_df[summary_col].dropna().head(3).tolist() if summary_col else [],
            "canonical_candidate": count >= 10,
        })

    cluster_candidates.sort(key=lambda x: x["ticket_count"], reverse=True)

    # 7. Taux de résolution
    resolved_count = 0
    if status_col:
        resolved_statuses = ["résolu", "closed", "done", "fermé", "resolved"]
        resolved_count = sum(
            count for status, count in status_counts.items()
            if any(rs in str(status).lower() for rs in resolved_statuses)
        )

    return {
        "total_tickets": len(df),
        "source_file": csv_path.name,
        "columns_detected": {
            "summary": summary_col,
            "description": desc_col,
            "status": status_col,
            "created": created_col,
            "priority": priority_col,
        },
        "category_distribution": category_counts,
        "top_error_codes": [{"code": c, "count": n} for c, n in error_code_counts],
        "status_distribution": {str(k): int(v) for k, v in status_counts.items()},
        "priority_distribution": {str(k): int(v) for k, v in priority_counts.items()},
        "top_keywords": keywords[:30],
        "cluster_candidates": cluster_candidates,
        "resolution_rate": round(resolved_count / len(df) * 100, 1) if len(df) > 0 else 0,
        "canonical_candidates_count": sum(1 for c in cluster_candidates if c["canonical_candidate"]),
    }


def extract_top_keywords(text: str, top_n: int = 50) -> List[str]:
    """Extrait les mots techniques les plus fréquents"""
    stop_words = {
        "le", "la", "les", "de", "du", "un", "une", "des", "est", "sur",
        "dans", "par", "en", "pour", "avec", "que", "qui", "pas", "ne",
        "au", "aux", "ce", "se", "si", "il", "elle", "ils", "elles",
        "nous", "vous", "je", "tu", "son", "sa", "ses", "mon", "ma",
        "et", "ou", "mais", "donc", "or", "ni", "car",
        "nan", "none", "null", "true", "false",
    }
    words = re.findall(r'\b[a-záàâäéèêëîïôùûüç_]{3,}\b', text)
    counts = Counter(w for w in words if w not in stop_words)
    return [w for w, _ in counts.most_common(top_n)]


def print_analysis_report(analysis: dict):
    """Affiche le rapport d'analyse dans le terminal"""
    print("\n" + "=" * 70)
    print("📊 ANALYSE TICKETS BRASIL 2025")
    print("=" * 70)
    print(f"\n📌 Total tickets: {analysis['total_tickets']}")
    print(f"📌 Taux de résolution: {analysis['resolution_rate']}%")

    print(f"\n🏷️  Distribution par catégorie:")
    for cat, count in sorted(analysis["category_distribution"].items(), key=lambda x: -x[1]):
        bar = "█" * min(count // 5, 30)
        print(f"  {cat:<30}: {count:>4}  {bar}")

    print(f"\n🔢 Top codes d'erreur:")
    for item in analysis["top_error_codes"][:10]:
        print(f"  Code {item['code']:>6}: {item['count']:>4} occurrences")

    print(f"\n🎯 Clusters candidats pour CanonicalProcedures ({analysis['canonical_candidates_count']} identifiés):")
    for c in analysis["cluster_candidates"]:
        marker = "✅" if c["canonical_candidate"] else "⚠️ "
        print(f"  {marker} {c['category']:<35}: {c['ticket_count']:>4} tickets ({c['percentage']}%)")
        if c["sample_summaries"]:
            print(f"      Ex: {c['sample_summaries'][0][:70]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze BRASIL ticket CSV")
    parser.add_argument(
        "--csv",
        default=None,
        help="Chemin vers le fichier CSV (ex: PARKA_OCEANE_D13_V07.csv)"
    )
    args = parser.parse_args()

    # Chercher le CSV automatiquement si non fourni
    if args.csv:
        csv_path = Path(args.csv)
    else:
        # Chercher dans les emplacements courants
        search_paths = [
            Path(__file__).parent / "input",
            Path(__file__).parents[1] / "backend" / "data",
            Path(__file__).parents[1],
        ]
        csv_path = None
        for sp in search_paths:
            candidates = list(sp.glob("*.csv")) if sp.exists() else []
            if candidates:
                csv_path = candidates[0]
                print(f"📂 CSV trouvé automatiquement: {csv_path}")
                break

    if not csv_path or not csv_path.exists():
        print("⚠️  Aucun CSV trouvé.")
        print("   Placer le fichier dans: data_pipeline/input/")
        print("   Ou utiliser: python data_pipeline/ticket_analyzer.py --csv chemin/vers/fichier.csv")
        print("\n💡 Génération d'un rapport vide pour démonstration...")
        analysis = {
            "total_tickets": 0,
            "source_file": "AUCUN",
            "message": "Placer le CSV PARKA dans data_pipeline/input/ et relancer.",
            "cluster_candidates": [],
            "canonical_candidates_count": 0,
        }
    else:
        analysis = analyze_csv(csv_path)
        print_analysis_report(analysis)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Analyse sauvegardée: {OUTPUT_FILE}")
