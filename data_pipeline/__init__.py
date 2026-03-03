"""
data_pipeline — Pipeline de données Brasil Intelligence Platform

Scripts (à exécuter dans l'ordre):
  1. fr_parser.py          — Parse les FRs .docx → fr_parsed.json
  2. fr_quality_scorer.py  — Score la qualité des FRs → fr_scored.json
  3. ticket_analyzer.py    — Analyse le CSV tickets → ticket_analysis.json
  4. canonical_builder.py  — Génère les CanonicalProcedures candidates → canonical_candidates.json
  5. canonical_injector.py — Injecte dans PostgreSQL + Qdrant

Ou tout en une commande:
  python data_pipeline/run_pipeline.py

Structure:
  data_pipeline/
  ├── input/          ← Placer ici le CSV tickets (ex: PARKA_OCEANE_D13_V07.csv)
  └── output/         ← Fichiers intermédiaires générés
"""
