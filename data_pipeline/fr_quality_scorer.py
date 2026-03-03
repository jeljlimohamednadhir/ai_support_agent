"""
FR Quality Scorer — Évaluation de la qualité des Fiches de Résolution
Usage : python data_pipeline/fr_quality_scorer.py
Input : data_pipeline/output/fr_parsed.json
Output : data_pipeline/output/fr_scored.json
"""
import json
import re
from pathlib import Path
from typing import Dict, List


INPUT_FILE  = Path(__file__).parent / "output" / "fr_parsed.json"
OUTPUT_FILE = Path(__file__).parent / "output" / "fr_scored.json"


# ─────────────────────────────────────────────
# Indicateurs de qualité médiocre
# ─────────────────────────────────────────────

VAGUE_PHRASES = [
    "ras", "ok", "corrigé", "résolu", "fait", "traité", "réglé",
    "n/a", "sans objet", "voir ci-dessus", "cf.", "idem",
    "à compléter", "en cours", "tbd",
]

ACTION_KEYWORDS = [
    "vérifier", "supprimer", "modifier", "relancer", "exécuter",
    "connecter", "chercher", "identifier", "corriger", "mettre à jour",
    "contrôler", "lancer", "copier", "coller", "saisir", "sélectionner",
    "cliquer", "ouvrir", "fermer", "redémarrer", "recharger",
    "select", "delete", "update", "insert", "where", "from",
]

TECHNICAL_KEYWORDS = [
    "erreur", "table", "base", "bdd", "sql", "vlan", "nd", "dslam",
    "carte", "port", "vc", "vp", "script", "requête", "commande",
    "procédure", "stockée", "trigger", "log", "trace", "exception",
]


# ─────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────

def score_fr(fr: dict) -> dict:
    """
    Calcule le score qualité d'une FR (0-100).
    
    Critères :
    ─────────────────────────────────────────────
    Longueur (mots)                          /20
    Présence de sections clés                /20
    Ratio d'actions concrètes                /20
    Présence de codes d'erreur               /10
    Mots-clés techniques                     /15
    Absence de phrases vagues                /15
    ─────────────────────────────────────────────
    """
    score = 0
    breakdown = {}
    full_text = fr.get("full_text", "").lower()
    word_count = fr.get("word_count", 0)
    sections = fr.get("sections", {})

    # 1. Longueur (max 20 pts)
    if word_count >= 300:
        pts = 20
    elif word_count >= 150:
        pts = 14
    elif word_count >= 80:
        pts = 8
    elif word_count >= 30:
        pts = 4
    else:
        pts = 0
    breakdown["length"] = pts
    score += pts

    # 2. Présence de sections clés (max 20 pts)
    sections_filled = sum(
        1 for k in ["procedure", "symptoms", "causes", "checks"]
        if sections.get(k)
    )
    pts = sections_filled * 5
    breakdown["sections"] = pts
    score += pts

    # 3. Actions concrètes (max 20 pts)
    action_count = sum(
        1 for kw in ACTION_KEYWORDS
        if kw in full_text
    )
    pts = min(action_count * 2, 20)
    breakdown["actions"] = pts
    score += pts

    # 4. Codes d'erreur mentionnés (max 10 pts)
    error_codes = fr.get("error_codes", [])
    pts = min(len(error_codes) * 5, 10)
    breakdown["error_codes"] = pts
    score += pts

    # 5. Mots-clés techniques (max 15 pts)
    tech_count = sum(
        1 for kw in TECHNICAL_KEYWORDS
        if kw in full_text
    )
    pts = min(tech_count * 2, 15)
    breakdown["technical_keywords"] = pts
    score += pts

    # 6. Pénalité phrases vagues (max -15 pts → on retire des pts de 15 disponibles)
    vague_count = sum(
        1 for phrase in VAGUE_PHRASES
        if re.search(r'\b' + phrase + r'\b', full_text)
    )
    vague_ratio = min(vague_count / max(word_count / 50, 1), 1.0)
    pts = max(0, 15 - int(vague_ratio * 15))
    breakdown["vague_penalty"] = pts
    score += pts

    # Classer selon le score
    if score >= 80:
        quality = "canonique"
        trust_level = "high"
    elif score >= 60:
        quality = "bonne"
        trust_level = "medium"
    elif score >= 30:
        quality = "partielle"
        trust_level = "low"
    else:
        quality = "inutilisable"
        trust_level = "none"

    return {
        **fr,
        "quality_score": score,
        "quality_label": quality,
        "trust_level": trust_level,
        "score_breakdown": breakdown,
        "vague_phrase_count": vague_count,
        "action_keyword_count": action_count,
        "technical_keyword_count": tech_count,
    }


def score_all(fr_list: List[dict]) -> List[dict]:
    """Score toutes les FR et retourne la liste enrichie triée par score"""
    scored = [score_fr(fr) for fr in fr_list]
    return sorted(scored, key=lambda x: x["quality_score"], reverse=True)


def print_report(scored: List[dict]):
    """Affiche un rapport lisible dans le terminal"""
    print("\n" + "=" * 70)
    print("📊 RAPPORT QUALITÉ DES FICHES DE RÉSOLUTION BRASIL")
    print("=" * 70)

    labels = ["canonique", "bonne", "partielle", "inutilisable"]
    counts = {l: sum(1 for fr in scored if fr["quality_label"] == l) for l in labels}
    total = len(scored)

    print(f"\n📈 Distribution ({total} FR):")
    for label, count in counts.items():
        bar = "█" * count + "░" * (total - count)
        pct = int(count / total * 100)
        print(f"  {label:>15} : {count:>3} ({pct:>3}%) {bar[:40]}")

    print(f"\n🏆 Top 10 meilleures FR:")
    print(f"  {'FR':>6} | {'Score':>5} | {'Qualité':>12} | Titre")
    print(f"  {'-'*6}-+-{'-'*5}-+-{'-'*12}-+-{'-'*40}")
    for fr in scored[:10]:
        print(f"  FR {fr['fr_number']:>4} | {fr['quality_score']:>5} | {fr['quality_label']:>12} | {fr['title'][:40]}")

    print(f"\n⚠️  Bottom 5 (à améliorer en priorité):")
    for fr in scored[-5:]:
        print(f"  FR {fr['fr_number']:>4} | score={fr['quality_score']:>3} | {fr['quality_label']:>12} | {fr['title'][:40]}")

    # Top erreurs couvertes
    all_codes = []
    for fr in scored:
        all_codes.extend(fr.get("error_codes", []))
    from collections import Counter
    top_codes = Counter(all_codes).most_common(10)
    if top_codes:
        print(f"\n🔢 Codes d'erreur les plus couverts:")
        for code, count in top_codes:
            print(f"  Code {code}: mentionné dans {count} FR")

    # Candidats pour canonisation
    candidates = [fr for fr in scored if fr["quality_label"] in ("canonique", "bonne")]
    print(f"\n🎯 Candidats pour CanonicalProcedure: {len(candidates)} FR")
    print(f"   ({counts['canonique']} directement canonisables + {counts['bonne']} à enrichir)")


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 FR Quality Scorer — BRASIL")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print(f"❌ Fichier introuvable: {INPUT_FILE}")
        print("   Lancer d'abord: python data_pipeline/fr_parser.py")
        exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        fr_list = json.load(f)

    print(f"📥 {len(fr_list)} FR chargées")
    scored = score_all(fr_list)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(scored, f, ensure_ascii=False, indent=2)

    print(f"💾 Résultats sauvegardés: {OUTPUT_FILE}")
    print_report(scored)
