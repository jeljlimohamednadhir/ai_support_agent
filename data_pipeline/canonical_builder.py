"""
Canonical Builder — Génère les CanonicalProcedures à partir des FRs scorées + analyse tickets
Usage : python data_pipeline/canonical_builder.py
Input :
  - data_pipeline/output/fr_scored.json
  - data_pipeline/output/ticket_analysis.json (optionnel)
Output: data_pipeline/output/canonical_candidates.json
"""
import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any

FR_SCORED_FILE       = Path(__file__).parent / "output" / "fr_scored.json"
TICKET_ANALYSIS_FILE = Path(__file__).parent / "output" / "ticket_analysis.json"
OUTPUT_FILE          = Path(__file__).parent / "output" / "canonical_candidates.json"

# Seuils de confiance pour promotion en CanonicalProcedure
TRUST_THRESHOLD_HIGH    = 80  # → trust_level = "HIGH"
TRUST_THRESHOLD_MEDIUM  = 60  # → trust_level = "MEDIUM"
TRUST_THRESHOLD_LOW     = 30  # → trust_level = "LOW"

# Minimum de tickets pour enrichir une procédure
MIN_TICKET_COUNT_ENRICH = 5


def load_fr_scored() -> List[Dict]:
    """Charge les FRs scorées"""
    if not FR_SCORED_FILE.exists():
        print(f"⚠️  fr_scored.json introuvable ({FR_SCORED_FILE})")
        print("   Lancer d'abord: python data_pipeline/fr_quality_scorer.py")
        return []
    with open(FR_SCORED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_ticket_analysis() -> Optional[Dict]:
    """Charge l'analyse tickets si disponible"""
    if not TICKET_ANALYSIS_FILE.exists():
        print("ℹ️  ticket_analysis.json absent → procédures sans enrichissement tickets")
        return None
    with open(TICKET_ANALYSIS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def map_quality_label_to_trust(quality_label: str) -> str:
    """Mappe un label qualité FR vers un niveau de confiance"""
    mapping = {
        "canonique": "HIGH",
        "bonne":     "MEDIUM",
        "partielle": "LOW",
        "inutilisable": None,  # Pas de procédure générée
    }
    return mapping.get(quality_label, "LOW")


def infer_category(fr: Dict) -> str:
    """Infère la catégorie métier depuis le titre et les sections"""
    title = (fr.get("title") or "").lower()
    text = title + " " + " ".join(
        " ".join(v) if isinstance(v, list) else str(v)
        for v in (fr.get("sections") or {}).values()
    ).lower()

    categories = {
        "Suppression":    ["suppression", "supprimer", "impossible de supprimer"],
        "VLAN":           ["vlan", "vlan bloqué", "vlan occupé"],
        "DSLAM":          ["dslam", "compteurs dslam", "broche"],
        "Acces":          ["accès", "access", "double accès"],
        "ND":             ["nd inconnu", "nd introuvable", "noeud de distribution"],
        "Carte":          ["carte", "card", "suppression carte"],
        "Erreur_Interne": ["erreur interne", "internal error", "b4002"],
        "Configuration":  ["configuration", "format", "paramètre"],
        "Cohérence_Data": ["incohérence", "données incorrectes", "incoherence"],
        "IHM":            ["ihm", "interface", "script"],
    }
    for category, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return category
    return "Général"


def build_resolution_steps(fr: Dict) -> List[str]:
    """Construit les étapes de résolution depuis les sections FR"""
    sections = fr.get("sections", {})
    steps = []

    # Extraire depuis la section procédure
    procedure_text = sections.get("procedure", [])
    if isinstance(procedure_text, list):
        procedure_text = " ".join(procedure_text)

    if procedure_text:
        # Découper en lignes/étapes
        lines = [l.strip() for l in procedure_text.split("\n") if l.strip()]
        for i, line in enumerate(lines[:15], 1):
            if len(line) > 10:
                # Numéroter si pas déjà numéroté
                if not line[0].isdigit():
                    steps.append(f"{i}. {line}")
                else:
                    steps.append(line)

    # Compléter avec les actions si peu d'étapes
    if len(steps) < 3:
        checks = sections.get("checks", [])
        if isinstance(checks, list):
            for check in checks[:5]:
                if isinstance(check, str) and len(check) > 10:
                    steps.append(f"✅ Vérifier: {check}")

    return steps if steps else ["Consulter la documentation FR associée."]


def build_diagnostic_checks(fr: Dict) -> List[str]:
    """Construit les vérifications de diagnostic depuis les sections FR"""
    sections = fr.get("sections", {})
    checks = []

    for section_key in ["checks", "symptoms", "causes"]:
        section_data = sections.get(section_key, [])
        if isinstance(section_data, list):
            for item in section_data[:5]:
                if isinstance(item, str) and len(item) > 10:
                    checks.append(item)

    return checks[:10] if checks else ["Analyser les logs Brasil.", "Vérifier les codes retour."]


def enrich_with_tickets(canonical: Dict, ticket_analysis: Dict) -> Dict:
    """Enrichit une procédure canonique avec les données tickets"""
    if not ticket_analysis or ticket_analysis.get("total_tickets", 0) == 0:
        return canonical

    error_codes = canonical.get("error_codes", [])
    category = canonical.get("category", "")

    # Rechercher les clusters tickets correspondants
    matching_clusters = []
    for cluster in ticket_analysis.get("cluster_candidates", []):
        cluster_cat = cluster.get("category", "")
        cluster_code = cluster.get("dominant_error_code", "")
        ticket_count = cluster.get("ticket_count", 0)

        # Match par code d'erreur
        if cluster_code and cluster_code in error_codes:
            matching_clusters.append(cluster)
        # Match par catégorie similaire
        elif any(
            part.lower() in cluster_cat.lower() or cluster_cat.lower() in part.lower()
            for part in category.split("_")
        ):
            matching_clusters.append(cluster)

    if matching_clusters:
        best_cluster = max(matching_clusters, key=lambda c: c["ticket_count"])
        canonical["ticket_count"] = best_cluster["ticket_count"]
        canonical["ticket_percentage"] = best_cluster.get("percentage", 0)
        # Ajouter les exemples de titres tickets
        if best_cluster.get("sample_summaries"):
            canonical["sample_ticket_titles"] = best_cluster["sample_summaries"][:3]
        # Ajuster le trust_level si beaucoup de tickets
        if best_cluster["ticket_count"] >= 20 and canonical["trust_level"] == "LOW":
            canonical["trust_level"] = "MEDIUM"
            canonical["trust_upgrade_reason"] = f"Promu MEDIUM: {best_cluster['ticket_count']} tickets confirmant le pattern"

    return canonical


def fr_to_canonical(fr: Dict, ticket_analysis: Optional[Dict] = None) -> Optional[Dict]:
    """Convertit un FR scoré en CanonicalProcedure candidate"""
    trust_level = map_quality_label_to_trust(fr.get("quality_label", "inutilisable"))
    if trust_level is None:
        return None  # FR inutilisable → on skip

    score = fr.get("score", 0)
    sections = fr.get("sections", {})

    # Extraire les symptômes
    symptoms_raw = sections.get("symptoms", [])
    if isinstance(symptoms_raw, list):
        symptoms = [s for s in symptoms_raw if isinstance(s, str) and len(s) > 5]
    else:
        symptoms = [str(symptoms_raw)] if symptoms_raw else []

    # Extraire les causes
    causes_raw = sections.get("causes", [])
    if isinstance(causes_raw, list):
        root_causes = [c for c in causes_raw if isinstance(c, str) and len(c) > 5]
    else:
        root_causes = [str(causes_raw)] if causes_raw else []

    canonical = {
        "id": str(uuid.uuid4()),
        "app_id": "BRASIL",
        "title": fr.get("title") or f"Procédure FR {fr.get('fr_number', '???')}",
        "category": infer_category(fr),
        "error_codes": fr.get("error_codes", []),
        "symptoms": symptoms[:10],
        "root_causes": root_causes[:5] if root_causes else ["Cause à déterminer selon contexte"],
        "diagnostic_checks": build_diagnostic_checks(fr),
        "resolution_steps": build_resolution_steps(fr),
        "risk_level": "MEDIUM",  # par défaut
        "impact_scope": "Équipement réseau BRASIL",
        "trust_level": trust_level,
        "validated_by": "fr_quality_scorer",
        "source_fr_numbers": [fr.get("fr_number")] if fr.get("fr_number") else [],
        "usage_count": 0,
        "success_count": 0,
        # Métadonnées de scoring
        "_meta": {
            "fr_score": score,
            "quality_label": fr.get("quality_label"),
            "score_breakdown": fr.get("score_breakdown", {}),
            "source_file": fr.get("filename", ""),
            "word_count": fr.get("word_count", 0),
        }
    }

    # Enrichissement avec tickets
    if ticket_analysis:
        canonical = enrich_with_tickets(canonical, ticket_analysis)

    return canonical


def build_from_ticket_clusters(ticket_analysis: Dict) -> List[Dict]:
    """
    Génère des CanonicalProcedure candidates depuis les clusters tickets
    pour les patterns sans FR correspondant
    """
    candidates = []
    if not ticket_analysis or ticket_analysis.get("total_tickets", 0) == 0:
        return candidates

    for cluster in ticket_analysis.get("cluster_candidates", []):
        if not cluster.get("canonical_candidate"):
            continue

        category = cluster["category"]
        ticket_count = cluster["ticket_count"]
        error_code = cluster.get("dominant_error_code")

        candidates.append({
            "id": str(uuid.uuid4()),
            "app_id": "BRASIL",
            "title": f"Pattern récurrent: {category.replace('_', ' ')}",
            "category": category,
            "error_codes": [error_code] if error_code else [],
            "symptoms": [
                f"Pattern détecté dans {ticket_count} tickets ({cluster.get('percentage', 0)}%)",
            ] + cluster.get("sample_summaries", [])[:3],
            "root_causes": ["Cause à investiguer via tickets N3"],
            "diagnostic_checks": [
                "Consulter les tickets similaires dans JIRA",
                f"Rechercher les tickets avec pattern: {category}",
            ],
            "resolution_steps": [
                "1. Rechercher tickets similaires résolus",
                "2. Appliquer la résolution documentée",
                "3. Documenter la résolution pour améliorer la base de connaissance",
            ],
            "risk_level": "MEDIUM",
            "impact_scope": "Brasil",
            "trust_level": "LOW",  # Généré depuis tickets uniquement → LOW
            "validated_by": "ticket_cluster_analysis",
            "source_fr_numbers": [],
            "ticket_count": ticket_count,
            "ticket_percentage": cluster.get("percentage", 0),
            "usage_count": 0,
            "success_count": 0,
            "_meta": {
                "source": "ticket_cluster",
                "cluster_data": cluster,
            }
        })

    return candidates


def deduplicate_candidates(candidates: List[Dict]) -> List[Dict]:
    """Dédoublonne par codes d'erreur et catégorie"""
    seen_keys = set()
    unique = []
    for c in candidates:
        # Clé de déduplication: catégorie + codes d'erreur triés
        key = c["category"] + "|" + ",".join(sorted(c.get("error_codes", [])))
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(c)
        else:
            # Fusionner: garder le meilleur trust_level
            trust_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            for u in unique:
                u_key = u["category"] + "|" + ",".join(sorted(u.get("error_codes", [])))
                if u_key == key:
                    if trust_order.get(c["trust_level"], 0) > trust_order.get(u["trust_level"], 0):
                        u["trust_level"] = c["trust_level"]
                        u["_meta"]["merged_from"] = c.get("_meta", {}).get("source_file", "")
                    break
    return unique


def print_summary(candidates: List[Dict]):
    """Affiche un résumé des candidats générés"""
    high   = sum(1 for c in candidates if c["trust_level"] == "HIGH")
    medium = sum(1 for c in candidates if c["trust_level"] == "MEDIUM")
    low    = sum(1 for c in candidates if c["trust_level"] == "LOW")

    sources = {
        "fr_quality_scorer":      sum(1 for c in candidates if c.get("validated_by") == "fr_quality_scorer"),
        "ticket_cluster_analysis": sum(1 for c in candidates if c.get("validated_by") == "ticket_cluster_analysis"),
    }

    print("\n" + "=" * 70)
    print("🧱 CANONICAL PROCEDURES GÉNÉRÉES")
    print("=" * 70)
    print(f"  Total: {len(candidates)} procédures candidates")
    print(f"  HIGH trust:   {high}")
    print(f"  MEDIUM trust: {medium}")
    print(f"  LOW trust:    {low}")
    print(f"\n  Sources:")
    for src, count in sources.items():
        print(f"    {src}: {count}")

    print(f"\n  Top 10 par confiance:")
    sorted_cands = sorted(candidates, key=lambda c: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(c["trust_level"], 0), reverse=True)
    for c in sorted_cands[:10]:
        codes = ", ".join(c.get("error_codes", [])[:3]) or "—"
        print(f"    [{c['trust_level']:>6}] {c['title'][:55]:<55} codes: {codes}")


if __name__ == "__main__":
    print("🧱 Canonical Builder — Génération des CanonicalProcedures BRASIL")
    print("-" * 70)

    # Charger les entrées
    fr_scored_list   = load_fr_scored()
    ticket_analysis  = load_ticket_analysis()

    if not fr_scored_list:
        print("❌ Aucun FR scoré trouvé. Pipeline interrompu.")
        exit(1)

    print(f"✅ {len(fr_scored_list)} FRs scorés chargés")
    if ticket_analysis:
        print(f"✅ Analyse tickets chargée: {ticket_analysis.get('total_tickets', 0)} tickets")

    # 1. Convertir les FRs scorés en procédures canoniques
    print("\n📝 Conversion des FRs en procédures...")
    fr_candidates = []
    skipped = 0
    for fr in fr_scored_list:
        candidate = fr_to_canonical(fr, ticket_analysis)
        if candidate:
            fr_candidates.append(candidate)
        else:
            skipped += 1

    print(f"  ✅ {len(fr_candidates)} procédures générées depuis FRs")
    print(f"  ⚠️  {skipped} FRs ignorés (qualité insuffisante)")

    # 2. Ajouter les clusters tickets sans FR correspondant
    ticket_only_candidates = []
    if ticket_analysis:
        print("\n🎫 Génération depuis clusters tickets...")
        ticket_only_candidates = build_from_ticket_clusters(ticket_analysis)
        print(f"  ✅ {len(ticket_only_candidates)} procédures générées depuis tickets")

    # 3. Combiner et dédoublonner
    all_candidates = fr_candidates + ticket_only_candidates
    before_dedup = len(all_candidates)
    all_candidates = deduplicate_candidates(all_candidates)
    print(f"\n🔁 Déduplication: {before_dedup} → {len(all_candidates)} procédures")

    # 4. Trier: HIGH → MEDIUM → LOW
    trust_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    all_candidates.sort(key=lambda c: trust_order.get(c["trust_level"], 0), reverse=True)

    # 5. Afficher et sauvegarder
    print_summary(all_candidates)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, ensure_ascii=False, indent=2)

    print(f"\n💾 {len(all_candidates)} candidats sauvegardés: {OUTPUT_FILE}")
    print("   Prochaine étape: python data_pipeline/canonical_injector.py")
