"""
run_knowledge_pipeline.py — Knowledge Intelligence Layer (étapes 6–10 + N3 diagnostic pipeline)
Usage : python data_pipeline/run_knowledge_pipeline.py [OPTIONS]

Ce script autonome exécute les étapes d'intelligence avancée :
  structure   — NLP enrichment des tickets → ticket_structured.json
  normalize   — FRs scored → fr_normalized.json (chunks RAG, trust scoring)
  cluster     — HDBSCAN clustering → cluster_results.json
  graph       — Knowledge graph builder → knowledge_graph.json + .gexf
  index       — RAG indexation Qdrant (trust-filtered)
  log_extract — Extraction de connaissance depuis les logs → log_knowledge.json
  proc_gen    — Génération de procédures N3 → procedures.json
  kb_index    — Indexation log_knowledge + procedures dans Qdrant

Exemples :
  python data_pipeline/run_knowledge_pipeline.py
  python data_pipeline/run_knowledge_pipeline.py --step log_extract
  python data_pipeline/run_knowledge_pipeline.py --step proc_gen
  python data_pipeline/run_knowledge_pipeline.py --step kb_index --dry-run
  python data_pipeline/run_knowledge_pipeline.py --step n3  # log_extract + proc_gen + kb_index
"""
import sys
import argparse
import time
import subprocess
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
OUTPUT_DIR   = PIPELINE_DIR / "output"


def run_step(script: str, args: list = None, label: str = "") -> bool:
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
    return (OUTPUT_DIR / filename).exists()


def print_header():
    print("""
+----------------------------------------------------------------------+
|       BRASIL KNOWLEDGE INTELLIGENCE PIPELINE                         |
|  NLP Structure -> FR Normalize -> Cluster -> Graph -> RAG Index      |
+----------------------------------------------------------------------+
""")


def print_summary(results: dict):
    print(f"\n{'='*70}")
    print("📊 RÉSUMÉ KNOWLEDGE PIPELINE")
    print(f"{'='*70}")
    all_ok = True
    for step, ok in results.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon} {step}")
        if not ok:
            all_ok = False

    print(f"\n  Artefacts générés:")
    files = [
        ("ticket_structured.json",  "Tickets NLP enrichis"),
        ("fr_normalized.json",      "FRs normalisés + RAG chunks"),
        ("cluster_results.json",    "Clusters HDBSCAN"),
        ("knowledge_graph.json",    "Graphe de connaissances"),
        ("knowledge_graph.gexf",    "Graphe au format GEXF"),
        ("log_knowledge.json",      "Connaissance extraite des logs (N3)"),
        ("procedures.json",         "Procédures N3 générées"),
    ]
    for filename, label in files:
        path = OUTPUT_DIR / filename
        if path.exists():
            size = path.stat().st_size // 1024
            print(f"    ✅ {filename:<35} ({size} KB) — {label}")
        else:
            print(f"    ⚠️  {filename:<35} absent")

    if all_ok:
        print(f"\n🧠 Knowledge intelligence layer opérationnel!")
        print(f"   API: GET  /api/v1/intelligence/pipeline-status")
        print(f"   API: POST /api/v1/intelligence/analyze-ticket")
        print(f"   API: GET  /api/v1/intelligence/clusters")
        print(f"   API: GET  /api/v1/intelligence/graph")
        print(f"\n🔬 N3 Diagnostic Engine opérationnel!")
        print(f"   Collections Qdrant: brasil_log_patterns, brasil_procedures")
        print(f"   Étape suivante: python data_pipeline/run_knowledge_pipeline.py --step n3")
    else:
        print(f"\n⚠️  Certaines étapes ont échoué. Vérifiez les prérequis (run_pipeline.py --step score).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Knowledge Intelligence Pipeline — étapes NLP avancées",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--step",
        choices=["structure", "normalize", "cluster", "graph", "index",
                 "log_extract", "proc_gen", "kb_index", "n3", "all"],
        default="all",
        help="Étape à exécuter (défaut: all = toutes les étapes)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Simuler sans écrire dans Qdrant")
    parser.add_argument("--csv", default=None,
                        help="Chemin vers le CSV tickets (pour l'étape structure)")
    parser.add_argument("--min-cluster-size", type=int, default=5,
                        help="Taille minimale d'un cluster HDBSCAN (défaut: 5)")
    args = parser.parse_args()

    print_header()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    step = args.step

    # ── ÉTAPE 6 : STRUCTURE ────────────────────────────────────────────────
    if step in ("all", "structure"):
        structure_args = []
        if args.csv:
            structure_args = ["--csv", args.csv]
        if args.dry_run:
            structure_args.append("--dry-run")
        ok = run_step(
            "ticket_structurer.py",
            args=structure_args,
            label="Étape 1/5 — NLP enrichment tickets → ticket_structured.json"
        )
        results["Ticket Structurer (NLP)"] = ok

    # ── ÉTAPE 7 : NORMALIZE ────────────────────────────────────────────────
    if step in ("all", "normalize"):
        if not check_output_exists("fr_scored.json"):
            print("\n⚠️  fr_scored.json absent.")
            print("   Prérequis: python data_pipeline/run_pipeline.py --step score")
            results["FR Normalizer"] = False
        else:
            ok = run_step(
                "fr_normalizer.py",
                label="Étape 2/5 — Normaliser FRs → fr_normalized.json + RAG chunks"
            )
            results["FR Normalizer"] = ok

    # ── ÉTAPE 8 : CLUSTER ─────────────────────────────────────────────────
    if step in ("all", "cluster"):
        if not check_output_exists("ticket_structured.json"):
            print("\n⚠️  ticket_structured.json absent — lancez d'abord: --step structure")
            results["Clustering Engine"] = False
        else:
            cluster_args = ["--min-size", str(args.min_cluster_size)]
            ok = run_step(
                "clustering_engine.py",
                args=cluster_args,
                label="Étape 3/5 — Clustering HDBSCAN → cluster_results.json"
            )
            results["Clustering Engine"] = ok

    # ── ÉTAPE 9 : GRAPH ───────────────────────────────────────────────────
    if step in ("all", "graph"):
        missing = []
        if not check_output_exists("cluster_results.json"):
            missing.append("cluster_results.json")
        if not check_output_exists("fr_normalized.json"):
            missing.append("fr_normalized.json")

        if missing:
            print(f"\n⚠️  Fichiers manquants: {', '.join(missing)}")
            results["Knowledge Graph Builder"] = False
        else:
            ok = run_step(
                "knowledge_graph_builder.py",
                label="Étape 4/5 — Knowledge graph → knowledge_graph.json + .gexf"
            )
            results["Knowledge Graph Builder"] = ok

    # ── ÉTAPE 10 : INDEX ──────────────────────────────────────────────────
    if step in ("all", "index"):
        if not check_output_exists("fr_normalized.json"):
            print("\n⚠️  fr_normalized.json absent — lancez d'abord: --step normalize")
            results["RAG Indexer (Qdrant)"] = False
        else:
            index_args = []
            if args.dry_run:
                index_args.append("--dry-run")
            ok = run_step(
                "rag_indexer.py",
                args=index_args,
                label="Étape 5/5 — Indexation Qdrant trust-filtered → vecteurs RAG"
            )
            results["RAG Indexer (Qdrant)"] = ok

    # ── ÉTAPE N3-1 : LOG KNOWLEDGE EXTRACTION ─────────────────────────────
    if step in ("all", "n3", "log_extract"):
        log_extract_args = []
        if args.dry_run:
            log_extract_args.append("--dry-run")
        ok = run_step(
            "log_knowledge_extractor.py",
            args=log_extract_args,
            label="N3 Étape 1/3 — Extraction connaissance logs → log_knowledge.json"
        )
        results["Log Knowledge Extractor"] = ok

    # ── ÉTAPE N3-2 : PROCEDURE GENERATION ────────────────────────────────
    if step in ("all", "n3", "proc_gen"):
        proc_args = []
        if args.dry_run:
            proc_args.append("--dry-run")
        ok = run_step(
            "procedure_generator.py",
            args=proc_args,
            label="N3 Étape 2/3 — Génération procédures N3 → procedures.json"
        )
        results["N3 Procedure Generator"] = ok

    # ── ÉTAPE N3-3 : KNOWLEDGE BASE INDEXING ──────────────────────────────
    if step in ("all", "n3", "kb_index"):
        kb_args = []
        if args.dry_run:
            kb_args.append("--dry-run")
        ok = run_step(
            "knowledge_indexer.py",
            args=kb_args,
            label="N3 Étape 3/3 — Indexation KB Qdrant (log_patterns + procedures)"
        )
        results["Knowledge Indexer (N3)"] = ok

    # ── RÉSUMÉ ─────────────────────────────────────────────────────────────
    if results:
        print_summary(results)
    else:
        print("\nℹ️  Aucune étape exécutée.")
