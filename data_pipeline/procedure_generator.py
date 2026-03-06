"""
N3 Procedure Generator — Synthesizes structured troubleshooting procedures from:
  1. Ticket clusters (cluster_results.json)
  2. Log knowledge records (log_knowledge.json)
  3. Taxonomy-defined incident types

For each cluster (≥ MIN_CLUSTER_SIZE tickets) the generator:
  - Identifies the incident type and involved applications
  - Extracts symptoms from cluster top terms + error codes
  - Enriches with matching log knowledge records
  - Builds structured diagnostic steps, root causes, resolution steps
  - Computes a composite trust score across all sources

Output: data_pipeline/output/procedures.json

Usage:
  python data_pipeline/procedure_generator.py
  python data_pipeline/procedure_generator.py --min-trust 0.50 --dry-run
"""
import json
import re
import sys
import math
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter

BACKEND_DIR    = Path(__file__).parents[1] / "backend"
PIPELINE_DIR   = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PIPELINE_DIR.parent))  # project root → enables data_pipeline.* imports

CLUSTER_FILE       = Path(__file__).parent / "output" / "cluster_results.json"
LOG_KNOWLEDGE_FILE = Path(__file__).parent / "output" / "log_knowledge.json"
OUTPUT_FILE        = Path(__file__).parent / "output" / "procedures.json"

# Minimum trust score to emit a procedure
MIN_TRUST_SCORE = 0.40

# Procedure ID counter prefix
PROC_PREFIX = "PROC-BRASIL"

# Application cross-system call chains for enriching procedure context
CROSS_SYSTEM_CHAINS: Dict[str, List[str]] = {
    "provisioning_failure":    ["BRASIL", "SEBA", "ORCHESTRA"],
    "data_inconsistency":      ["BRASIL", "SEBA", "ADELIA"],
    "system_integration_error": ["BRASIL", "SEBA", "IPON", "ARTEMIS", "SCA"],
    "command_failure":         ["BRASIL", "ADELIA", "SEBA"],
    "network_equipment_issue": ["BRASIL", "ORCHESTRA", "SEBA"],
    "access_management_error": ["BRASIL"],
    "scheduling_issue":        ["BRASIL", "ORCHESTRA"],
    "data_sync_failure":       ["BRASIL", "SEBA", "ADELIA"],
}

# Incident type → short code for procedure ID
INCIDENT_TYPE_CODES: Dict[str, str] = {
    "provisioning_failure":     "PROV",
    "data_inconsistency":       "DATA",
    "system_integration_error": "INT",
    "command_failure":          "CMD",
    "network_equipment_issue":  "NET",
    "access_management_error":  "ACC",
    "access_issue.login_failure":    "ACC",
    "access_issue.permission_denied": "ACC",
    "command_failure.command_blocked": "CMD",
    "command_failure.command_timeout": "CMD",
    "data_inconsistency.mapping_error": "DATA",
    "scheduling_issue":         "SCH",
    "unknown":                  "GEN",
}


# ─────────────────────────────────────────────────────────────────────────────
# Procedure trust scoring
# ─────────────────────────────────────────────────────────────────────────────

def compute_procedure_trust(
    cluster_trust: float,
    cluster_size: int,
    log_records_count: int,
    has_catalog_exception: bool,
    max_log_freq: int,
) -> float:
    """
    Composite trust score for a generated procedure.

    Weights:
      - cluster trust (base)     : 40%
      - cluster size (frequency) : 25%
      - log knowledge matched    : 25%
      - catalog validation       : 10%
    """
    # Cluster base trust
    s_cluster = cluster_trust

    # Size component (log-normalized)
    s_size = min(math.log1p(cluster_size) / math.log1p(200), 1.0)

    # Log knowledge component
    s_log = min(
        math.log1p(log_records_count) / math.log1p(10) * 0.8
        + (math.log1p(max_log_freq) / math.log1p(200)) * 0.2,
        1.0,
    ) if log_records_count > 0 else 0.0

    # Catalog validation bonus
    s_catalog = 1.0 if has_catalog_exception else 0.0

    score = (
        0.40 * s_cluster
        + 0.25 * s_size
        + 0.25 * s_log
        + 0.10 * s_catalog
    )
    return round(min(score, 1.0), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Symptom / step builders
# ─────────────────────────────────────────────────────────────────────────────

def build_symptoms(
    cluster: Dict,
    log_records: List[Dict],
) -> List[str]:
    """Build a de-duplicated list of symptoms from cluster + log knowledge."""
    symptoms = []

    # From cluster common_symptoms
    for s in cluster.get("common_symptoms", []):
        clean = s.strip()
        if clean and clean not in symptoms:
            symptoms.append(clean)

    # From log patterns — translate error pattern to symptom language
    for rec in log_records:
        template = rec.get("error_pattern", "")
        if template and "<CATALOG>" not in template:
            symptom = f"Log contient: « {template[:100]} »"
            if symptom not in symptoms:
                symptoms.append(symptom)

    # From error codes
    for code in cluster.get("top_error_codes", []):
        s = f"Code erreur {code} affiché"
        if s not in symptoms:
            symptoms.append(s)

    # Add exception names as symptoms
    for rec in log_records:
        exc = rec.get("exception", "")
        if exc:
            s = f"Exception {exc} dans les logs applicatifs"
            if s not in symptoms:
                symptoms.append(s)

    return symptoms[:8]


def build_diagnostic_steps(
    cluster: Dict,
    log_records: List[Dict],
    incident_type: str,
    applications: List[str],
) -> List[Dict[str, Any]]:
    """Build numbered diagnostic steps merging cluster steps + log diagnostic actions."""
    steps = []
    step_num = 1

    # Step 1: Always check logs first
    app = applications[0] if applications else "BRASIL"
    error_codes = cluster.get("top_error_codes", [])
    code_filter = f" — filtrer sur {error_codes[0]}" if error_codes else ""
    steps.append({
        "step": step_num,
        "action": f"Vérifier les logs {app} sur la période d'incident{code_filter}",
        "tool": f"{app} Admin Console → Logs → Recherche temporelle",
        "expected_output": "Identifier le message d'erreur exact et le timestamp",
    })
    step_num += 1

    # Steps from log diagnostic actions
    seen_actions = set()
    for rec in log_records[:2]:  # Top 2 most relevant log records
        for action in rec.get("diagnostic_actions", [])[:3]:
            clean = action.strip()
            # Deduplicate similar actions
            key = clean[:50].lower()
            if key not in seen_actions:
                seen_actions.add(key)
                # Parse tool from action if format is "Action → Tool"
                parts = clean.split("→")
                steps.append({
                    "step": step_num,
                    "action": parts[0].strip(),
                    "tool": parts[1].strip() if len(parts) > 1 else "BRASIL Admin Console",
                    "expected_output": "Confirmer ou infirmer la cause probable",
                })
                step_num += 1
            if step_num > 6:
                break

    # Generic steps from cluster troubleshooting
    for generic_step in cluster.get("suggested_troubleshooting_steps", [])[:2]:
        # Strip numbering if present
        clean = re.sub(r"^\d+\.\s*", "", generic_step).strip()
        key = clean[:50].lower()
        if key not in seen_actions:
            seen_actions.add(key)
            steps.append({
                "step": step_num,
                "action": clean,
                "tool": "BRASIL Admin Console",
                "expected_output": "Confirmer le diagnostic",
            })
            step_num += 1

    return steps[:8]


def build_root_causes(
    cluster: Dict,
    log_records: List[Dict],
) -> List[str]:
    """Build root cause list from cluster + log records."""
    causes = []

    # From log knowledge
    for rec in log_records:
        cause = rec.get("probable_root_cause", "")
        if cause and cause not in causes:
            causes.append(cause)

    # From taxonomy (via cluster probable causes)
    for c in cluster.get("probable_causes", []):
        if c and c not in causes:
            causes.append(c)

    return causes[:5]


def build_resolution_steps(
    cluster: Dict,
    log_records: List[Dict],
    incident_type: str,
) -> List[str]:
    """Build resolution step list from log records + cluster."""
    steps = []
    seen = set()

    for rec in log_records[:2]:
        for step in rec.get("resolution_actions", []):
            key = step[:50].lower()
            if key not in seen:
                seen.add(key)
                steps.append(step)

    # Always add: document and escalate as last resort
    escalation = (
        f"Si le problème persiste : escalader à l'équipe N3 avec les logs et le numéro de ticket"
    )
    if escalation[:40].lower() not in seen:
        steps.append(escalation)

    return steps[:7]


def estimate_resolution_time(incident_type: str, has_network: bool) -> str:
    """Estimate resolution time based on incident type."""
    times = {
        "provisioning_failure":      "2–4h (avec coordination réseau)",
        "data_inconsistency":        "1–2h",
        "system_integration_error":  "1–3h (selon disponibilité système tiers)",
        "command_failure":           "30min–1h",
        "network_equipment_issue":   "4–8h (intervention terrain possible)",
        "access_management_error":   "15–30min",
    }
    base = times.get(incident_type, "1–2h")
    if has_network and "réseau" not in base:
        return base + " (+ coordination réseau si DSLAM)"
    return base


def get_escalation_path(incident_type: str, applications: List[str]) -> str:
    """Build escalation path based on incident type and applications."""
    paths = {
        "provisioning_failure":      "N3 BRASIL → Équipe Réseau → ORCHESTRA Admin",
        "data_inconsistency":        "N3 BRASIL → Équipe Data → DBA",
        "system_integration_error":  "N3 BRASIL → Équipe Intégration → Admin système tiers",
        "command_failure":           "N3 BRASIL → Responsable Métier",
        "network_equipment_issue":   "N3 BRASIL → Équipe Réseau → NOC",
        "access_management_error":   "N3 BRASIL → Admin Sécurité → LDAP Admin",
    }
    category = incident_type.split(".")[0] if "." in incident_type else incident_type
    return paths.get(incident_type, paths.get(category, f"N3 BRASIL → Équipe {applications[0]}"))


# ─────────────────────────────────────────────────────────────────────────────
# Matching log records to a cluster
# ─────────────────────────────────────────────────────────────────────────────

def find_matching_log_records(
    cluster: Dict,
    all_log_records: List[Dict],
    max_records: int = 3,
) -> List[Dict]:
    """
    Find log knowledge records relevant to a cluster.

    Matching criteria (in priority order):
      1. Exception name present in cluster top terms or error codes
      2. Incident type match
      3. Application match
    """
    cluster_incident = cluster.get("incident_type", "")
    cluster_app      = cluster.get("application", "BRASIL")
    cluster_terms    = " ".join(cluster.get("top_terms", [])).lower()
    cluster_codes    = [c.lower() for c in cluster.get("top_error_codes", [])]

    scored: List[tuple] = []

    for rec in all_log_records:
        score = 0

        # Match by exception name in cluster terms
        exc = rec.get("exception", "").lower()
        if exc and exc in cluster_terms:
            score += 10

        # Match by incident type (full or partial)
        rec_type = rec.get("incident_type", "")
        if rec_type and (rec_type == cluster_incident or
                         rec_type.split(".")[0] == cluster_incident.split(".")[0]):
            score += 6

        # Match by application
        if rec.get("application", "") == cluster_app:
            score += 3

        # Match by error code
        for code in cluster_codes:
            if any(code in str(ec).lower() for ec in rec.get("error_codes", [])):
                score += 4
                break

        # Prefer catalog-validated records
        if rec.get("catalog_validated"):
            score += 2

        if score > 0:
            scored.append((score, rec))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [rec for _, rec in scored[:max_records]]


# ─────────────────────────────────────────────────────────────────────────────
# Procedure generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_procedure(
    cluster: Dict,
    log_records: List[Dict],
    proc_sequence: int,
) -> Dict[str, Any]:
    """
    Generate a structured N3 troubleshooting procedure from a cluster.
    """
    incident_type = cluster.get("incident_type", "unknown")
    application   = cluster.get("application", "BRASIL")
    cluster_size  = cluster.get("size", 0)

    # Determine involved applications from cross-system chains
    base_category = incident_type.split(".")[0] if "." in incident_type else incident_type
    apps_chain    = CROSS_SYSTEM_CHAINS.get(
        incident_type,
        CROSS_SYSTEM_CHAINS.get(base_category, [application])
    )
    # Merge with systems detected in log records
    for rec in log_records:
        for sys in rec.get("related_systems", []):
            if sys not in apps_chain:
                apps_chain.append(sys)

    # Build procedure ID
    type_code  = INCIDENT_TYPE_CODES.get(incident_type, INCIDENT_TYPE_CODES.get(base_category, "GEN"))
    proc_id    = f"{PROC_PREFIX}-{type_code}-{proc_sequence:04d}"

    # Title: use cluster name + incident type
    cluster_name = cluster.get("cluster_name", "incident").replace("_", " ").title()
    title        = f"{cluster_name} — procédure N3"

    # Composite trust
    has_catalog  = any(r.get("catalog_validated") for r in log_records)
    max_log_freq = max((r.get("frequency", 0) for r in log_records), default=0)
    trust = compute_procedure_trust(
        cluster_trust=cluster.get("trust_score", 0.40),
        cluster_size=cluster_size,
        log_records_count=len(log_records),
        has_catalog_exception=has_catalog,
        max_log_freq=max_log_freq,
    )

    symptoms         = build_symptoms(cluster, log_records)
    diagnostic_steps = build_diagnostic_steps(cluster, log_records, incident_type, apps_chain)
    root_causes      = build_root_causes(cluster, log_records)
    resolution_steps = build_resolution_steps(cluster, log_records, incident_type)
    resolution_time  = estimate_resolution_time(incident_type, "ORCHESTRA" in apps_chain)
    escalation       = get_escalation_path(incident_type, apps_chain)

    # Source metadata
    source_types = ["ticket_cluster"]
    if log_records:
        source_types.append("log_derived")
    if has_catalog:
        source_types.append("catalog_validated")

    exceptions_used = list({
        r["exception"] for r in log_records if r.get("exception")
    })

    procedure = {
        "procedure_id": proc_id,
        "title": title,
        "incident_type": incident_type,
        "applications_involved": apps_chain,
        "symptoms": symptoms,
        "diagnostic_steps": diagnostic_steps,
        "root_causes": root_causes,
        "resolution_steps": resolution_steps,
        "estimated_resolution_time": resolution_time,
        "escalation_path": escalation,
        "trust_score": trust,
        "source_types": source_types,
        "ticket_count": cluster_size,
        "cluster_id": cluster.get("cluster_id"),
        "exceptions_referenced": exceptions_used,
        "error_codes_referenced": cluster.get("top_error_codes", []),
        "version": "1.0",
        "created_at": datetime.utcnow().isoformat(),
        "last_updated": datetime.utcnow().isoformat(),
    }

    return procedure


# ─────────────────────────────────────────────────────────────────────────────
# Standalone catalog procedures
# Generate procedures for well-known exceptions even without cluster data
# ─────────────────────────────────────────────────────────────────────────────

def generate_catalog_procedures(
    log_knowledge_records: List[Dict],
    existing_proc_exceptions: set,
    start_seq: int,
) -> List[Dict]:
    """
    For catalog-validated log records not covered by any cluster procedure,
    generate standalone procedures directly from the exception catalog.
    """
    from log_knowledge_extractor import EXCEPTION_CATALOG  # noqa: E402

    procs = []
    seq = start_seq

    for rec in log_knowledge_records:
        exc = rec.get("exception", "")
        if not exc or not rec.get("catalog_validated"):
            continue
        if exc in existing_proc_exceptions:
            continue
        if rec.get("trust_score", 0) < 0.55:
            continue

        incident_type = rec.get("incident_type", "unknown")
        application   = rec.get("application", "BRASIL")
        apps_chain    = CROSS_SYSTEM_CHAINS.get(incident_type, [application]) + rec.get("related_systems", [])
        apps_chain    = list(dict.fromkeys(apps_chain))  # Deduplicate while preserving order

        type_code = INCIDENT_TYPE_CODES.get(incident_type, "GEN")
        proc_id   = f"{PROC_PREFIX}-{type_code}-{seq:04d}"

        proc = {
            "procedure_id": proc_id,
            "title": f"{exc.replace('Exception', '').replace('Error', '')} — procédure N3",
            "incident_type": incident_type,
            "applications_involved": apps_chain,
            "symptoms": [
                f"Exception {exc} dans les logs applicatifs",
                f"Pattern: « {rec.get('error_pattern', '')[:120]} »",
            ],
            "diagnostic_steps": [
                {
                    "step": i + 1,
                    "action": action,
                    "tool": "BRASIL Admin Console → Logs",
                    "expected_output": "Confirmer le diagnostic",
                }
                for i, action in enumerate(rec.get("diagnostic_actions", [])[:6])
            ],
            "root_causes": [rec.get("probable_root_cause", "")],
            "resolution_steps": rec.get("resolution_actions", [])[:6],
            "estimated_resolution_time": estimate_resolution_time(incident_type, False),
            "escalation_path": get_escalation_path(incident_type, apps_chain),
            "trust_score": rec.get("trust_score", 0.65),
            "source_types": ["catalog_validated", "log_derived"],
            "ticket_count": rec.get("frequency", 0),
            "cluster_id": None,
            "exceptions_referenced": [exc],
            "error_codes_referenced": rec.get("error_codes", []),
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
        }
        procs.append(proc)
        existing_proc_exceptions.add(exc)
        seq += 1

    return procs


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run(min_trust: float = MIN_TRUST_SCORE, dry_run: bool = False) -> bool:
    """
    Main procedure generation pipeline.
    """
    # Load clusters
    if not CLUSTER_FILE.exists():
        print(f"  ⚠️  cluster_results.json introuvable ({CLUSTER_FILE})")
        print("     Lancer d'abord: python data_pipeline/clustering_engine.py")
        clusters = []
    else:
        with open(CLUSTER_FILE, "r", encoding="utf-8") as f:
            cluster_data = json.load(f)
        clusters = cluster_data.get("clusters", [])
        print(f"  📂 {len(clusters)} clusters chargés")

    # Load log knowledge records
    log_records = []
    if LOG_KNOWLEDGE_FILE.exists():
        with open(LOG_KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            log_data = json.load(f)
        log_records = log_data.get("records", [])
        print(f"  📂 {len(log_records)} enregistrements log chargés")
    else:
        print("  ⚠️  log_knowledge.json introuvable — procédures sans enrichissement log")

    # Generate procedures from clusters
    procedures = []
    skipped    = 0
    seq        = 1

    for cluster in clusters:
        matching_logs = find_matching_log_records(cluster, log_records)
        proc = generate_procedure(cluster, matching_logs, seq)

        if proc["trust_score"] < min_trust:
            skipped += 1
            continue

        procedures.append(proc)
        seq += 1
        logs_info = (
            f" + {len(matching_logs)} logs [{','.join(r['exception'] for r in matching_logs if r.get('exception'))[:40]}]"
            if matching_logs else ""
        )
        print(
            f"  ✅ {proc['procedure_id']}: trust={proc['trust_score']:.2f}, "
            f"tickets={proc['ticket_count']}{logs_info}"
        )

    print(f"\n  📊 {len(procedures)} procédures générées, {skipped} ignorées (trust < {min_trust})")

    # Generate standalone catalog procedures for uncovered exceptions
    covered_exceptions: set = set()
    for p in procedures:
        covered_exceptions.update(p.get("exceptions_referenced", []))

    catalog_procs = generate_catalog_procedures(log_records, covered_exceptions, seq)
    print(f"  📚 {len(catalog_procs)} procédures catalog générées (exceptions non couvertes)")

    all_procedures = procedures + catalog_procs

    # Trust summary
    high   = sum(1 for p in all_procedures if p["trust_score"] >= 0.75)
    medium = sum(1 for p in all_procedures if 0.50 <= p["trust_score"] < 0.75)
    low    = sum(1 for p in all_procedures if p["trust_score"] < 0.50)
    print(f"\n  📊 Trust distribution:")
    print(f"     Haut (≥0.75): {high} | Moyen (0.50–0.75): {medium} | Faible (<0.50): {low}")

    if dry_run:
        print("  🔍 Mode DRY-RUN — pas d'écriture")
        return True

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_procedures": len(all_procedures),
        "from_clusters": len(procedures),
        "from_catalog": len(catalog_procs),
        "min_trust_used": min_trust,
        "procedures": all_procedures,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  💾 Sauvegardé: {OUTPUT_FILE}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="N3 Procedure Generator — Build structured troubleshooting procedures"
    )
    parser.add_argument(
        "--min-trust", type=float, default=MIN_TRUST_SCORE,
        help=f"Score de confiance minimum (défaut: {MIN_TRUST_SCORE})"
    )
    parser.add_argument("--dry-run", action="store_true", help="Ne pas écrire les fichiers de sortie")
    args = parser.parse_args()

    success = run(min_trust=args.min_trust, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
