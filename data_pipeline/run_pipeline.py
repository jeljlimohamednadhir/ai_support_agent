"""
run_pipeline.py — Pipeline complet Brasil (FR → Score → Tickets → Canonical → Injection → Knowledge)
Usage : python data_pipeline/run_pipeline.py [--step STEP] [--dry-run] [--csv path]

Étapes classiques:
  1. parse      — Parser les FRs .docx → fr_parsed.json
  2. score      — Scorer la qualité FR → fr_scored.json
  3. tickets    — Analyser le CSV tickets → ticket_analysis.json
  4. build      — Générer les CanonicalProcedures → canonical_candidates.json
  5. inject     — Injecter dans PostgreSQL + Qdrant

Étapes knowledge (NLP enrichment + indexation avancée):
  6. structure  — NLP enrichment des tickets → ticket_structured.json
  7. normalize  — Normalisation FRs → fr_normalized.json (chunks RAG)
  8. cluster    — Clustering HDBSCAN → cluster_results.json
  9. graph      — Graphe de connaissances → knowledge_graph.json
  10. index     — Indexation Qdrant trust-filtered

  all           — Toutes les étapes classiques (défaut)
  knowledge     — Étapes 6–10 uniquement (intelligence layer)
  full          — Étapes 1–10 (pipeline complet)
"""
import sys
import argparse
import time
import subprocess
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
OUTPUT_DIR   = PIPELINE_DIR / "output"


def run_step(script: str, args: list = None, label: str = "") -> bool:
    """Lance un script Python du pipeline et retourne True si succès"""
    script_path = PIPELINE_DIR / script
    if not script_path.exists():
        print(f"  ❌ Script introuvable: {script_path}")
        return False

    cmd = [sys.executable, str(script_path)] + (args or [])
    label = label or script

    print(f"\n{'='*70}")
    print(f"▶️  {label}")
    print(f"{'='*70}")

    start = time.time()
    result = subprocess.run(cmd, cwd=str(PIPELINE_DIR.parent))
    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"  ✅ Terminé en {elapsed:.1f}s")
        return True
    else:
        print(f"  ❌ Échec (code {result.returncode}) après {elapsed:.1f}s")
        return False


def check_output_exists(filename: str) -> bool:
    """Vérifie si un fichier de sortie existe"""
    return (OUTPUT_DIR / filename).exists()


def print_pipeline_header():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║          PIPELINE DATA — BRASIL INTELLIGENCE PLATFORM               ║
║  FR Parser → Quality Scorer → Ticket Analyzer → Canonical Builder   ║
║     → PostgreSQL + Qdrant → NLP Structure → Cluster → Graph → RAG  ║
╚══════════════════════════════════════════════════════════════════════╝
""")


def print_pipeline_summary(results: dict):
    print(f"\n{'='*70}")
    print("📊 RÉSUMÉ DU PIPELINE")
    print(f"{'='*70}")
    all_ok = True
    for step, ok in results.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon} {step}")
        if not ok:
            all_ok = False

    # Vérifier les fichiers générés
    print(f"\n  Fichiers générés:")
    files = [
        ("fr_parsed.json",              "FRs parsés"),
        ("fr_scored.json",              "FRs scorés"),
        ("ticket_analysis.json",        "Analyse tickets"),
        ("canonical_candidates.json",   "Procédures candidates"),
        ("ticket_structured.json",      "Tickets NLP enrichis"),
        ("fr_normalized.json",          "FRs normalisés + RAG chunks"),
        ("cluster_results.json",        "Clusters HDBSCAN"),
        ("knowledge_graph.json",        "Graphe de connaissances"),
    ]
    for filename, label in files:
        path = OUTPUT_DIR / filename
        if path.exists():
            size = path.stat().st_size // 1024
            print(f"    ✅ {filename:<40} ({size} KB) — {label}")
        else:
            print(f"    ⚠️  {filename:<40} absent")

    if all_ok:
        print(f"\n🎉 Pipeline complet — Brasil Intelligence Platform opérationnel!")
        print(f"   Démarrer l'API: uvicorn backend.app.main:app --reload")
        print(f"   Tester: POST /api/v1/chat  avec {{ \"message\": \"...\", \"app_id\": \"BRASIL\" }}")
    else:
        print(f"\n⚠️  Pipeline partiel — Vérifier les erreurs ci-dessus.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline Brasil Intelligence")
    parser.add_argument(
        "--step",
        choices=[
            "parse", "score", "tickets", "build", "inject",
            "structure", "normalize", "cluster", "graph", "index",
            "all", "knowledge", "full",
        ],
        default="all",
        help="Étape à exécuter (défaut: all)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simuler l'injection sans écrire")
    parser.add_argument("--csv", default=None, help="Chemin vers le CSV tickets")
    parser.add_argument("--skip-tickets", action="store_true", help="Passer l'étape tickets")
    parser.add_argument("--skip-inject", action="store_true", help="Passer l'étape injection")
    args = parser.parse_args()

    print_pipeline_header()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    step = args.step

    # Étapes "classiques" (1–5)
    CLASSIC_STEPS = {"parse", "score", "tickets", "build", "inject", "all", "full"}
    # Étapes "knowledge" (6–10)
    KNOWLEDGE_STEPS = {"structure", "normalize", "cluster", "graph", "index", "knowledge", "full"}

    # ── ÉTAPE 1 : PARSE FRs ────────────────────────────────────────────────
    if step in ("all", "parse"):
        ok = run_step("fr_parser.py", label="Étape 1/10 — Parser les FRs .docx")
        results["1. FR Parser"] = ok
        if not ok and step == "parse":
            sys.exit(1)

    # ── ÉTAPE 2 : SCORE FRs ────────────────────────────────────────────────
    if step in ("all", "score"):
        if not check_output_exists("fr_parsed.json"):
            print("⚠️  fr_parsed.json absent — lancer d'abord: --step parse")
            results["2. FR Scorer"] = False
        else:
            ok = run_step("fr_quality_scorer.py", label="Étape 2/10 — Scorer la qualité des FRs")
            results["2. FR Scorer"] = ok

    # ── ÉTAPE 3 : TICKETS ──────────────────────────────────────────────────
    if step in ("all", "tickets") and not args.skip_tickets:
        ticket_args = []
        if args.csv:
            ticket_args = ["--csv", args.csv]
        ok = run_step(
            "ticket_analyzer.py",
            args=ticket_args,
            label="Étape 3/10 — Analyser les tickets CSV"
        )
        results["3. Ticket Analyzer"] = ok
    elif args.skip_tickets:
        print("\nℹ️  Étape tickets ignorée (--skip-tickets)")
        results["3. Ticket Analyzer"] = True  # considéré OK

    # ── ÉTAPE 4 : BUILD CANONICAL ──────────────────────────────────────────
    if step in ("all", "build"):
        if not check_output_exists("fr_scored.json"):
            print("⚠️  fr_scored.json absent — lancer d'abord: --step score")
            results["4. Canonical Builder"] = False
        else:
            ok = run_step("canonical_builder.py", label="Étape 4/10 — Générer les CanonicalProcedures")
            results["4. Canonical Builder"] = ok

    # ── ÉTAPE 5 : INJECT ──────────────────────────────────────────────────
    if step in ("all", "inject") and not args.skip_inject:
        if not check_output_exists("canonical_candidates.json"):
            print("⚠️  canonical_candidates.json absent — lancer d'abord: --step build")
            results["5. Injector"] = False
        else:
            inject_args = []
            if args.dry_run:
                inject_args.append("--dry-run")
            ok = run_step(
                "canonical_injector.py",
                args=inject_args,
                label="Étape 5/10 — Injecter dans PostgreSQL + Qdrant"
            )
            results["5. Injector"] = ok
    elif args.skip_inject:
        print("\nℹ️  Étape injection ignorée (--skip-inject)")

    # ══════════════════════════════════════════════════════════════════════
    # COUCHE KNOWLEDGE INTELLIGENCE (étapes 6–10)
    # ══════════════════════════════════════════════════════════════════════

    # ── ÉTAPE 6 : STRUCTURE (NLP enrichment des tickets) ──────────────────
    if step in ("structure", "knowledge", "full"):
        structure_args = []
        if args.csv:
            structure_args = ["--csv", args.csv]
        if args.dry_run:
            structure_args.append("--dry-run")
        ok = run_step(
            "ticket_structurer.py",
            args=structure_args,
            label="Étape 6/10 — NLP enrichment des tickets → ticket_structured.json"
        )
        results["6. Ticket Structurer (NLP)"] = ok

    # ── ÉTAPE 7 : NORMALIZE (FRs → structured procedures + RAG chunks) ────
    if step in ("normalize", "knowledge", "full"):
        if not check_output_exists("fr_scored.json"):
            print("⚠️  fr_scored.json absent — lancer d'abord: --step score")
            results["7. FR Normalizer"] = False
        else:
            ok = run_step(
                "fr_normalizer.py",
                label="Étape 7/10 — Normaliser FRs → fr_normalized.json + RAG chunks"
            )
            results["7. FR Normalizer"] = ok

    # ── ÉTAPE 8 : CLUSTER (HDBSCAN clustering) ────────────────────────────
    if step in ("cluster", "knowledge", "full"):
        if not check_output_exists("ticket_structured.json"):
            print("⚠️  ticket_structured.json absent — lancer d'abord: --step structure")
            results["8. Clustering Engine"] = False
        else:
            ok = run_step(
                "clustering_engine.py",
                label="Étape 8/10 — Clustering HDBSCAN → cluster_results.json"
            )
            results["8. Clustering Engine"] = ok

    # ── ÉTAPE 9 : GRAPH (Knowledge graph builder) ─────────────────────────
    if step in ("graph", "knowledge", "full"):
        if not check_output_exists("cluster_results.json"):
            print("⚠️  cluster_results.json absent — lancer d'abord: --step cluster")
            results["9. Knowledge Graph"] = False
        elif not check_output_exists("fr_normalized.json"):
            print("⚠️  fr_normalized.json absent — lancer d'abord: --step normalize")
            results["9. Knowledge Graph"] = False
        else:
            ok = run_step(
                "knowledge_graph_builder.py",
                label="Étape 9/10 — Construire le graphe de connaissances → knowledge_graph.json"
            )
            results["9. Knowledge Graph"] = ok

    # ── ÉTAPE 10 : INDEX (RAG indexation Qdrant) ──────────────────────────
    if step in ("index", "knowledge", "full"):
        if not check_output_exists("fr_normalized.json"):
            print("⚠️  fr_normalized.json absent — lancer d'abord: --step normalize")
            results["10. RAG Indexer"] = False
        else:
            index_args = []
            if args.dry_run:
                index_args.append("--dry-run")
            ok = run_step(
                "rag_indexer.py",
                args=index_args,
                label="Étape 10/10 — Indexer dans Qdrant (trust-filtered) → vecteurs RAG"
            )
            results["10. RAG Indexer"] = ok

    # ── RÉSUMÉ ─────────────────────────────────────────────────────────────
    if results:
        print_pipeline_summary(results)