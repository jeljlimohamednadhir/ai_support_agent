"""
Test de conversation complète — couverture totale du chatbot BRASIL
=====================================================================
Simule une conversation réelle d'un ingénieur N3 qui :
  1.  Salue le bot (off-topic → redirection)
  2.  Déclare un incident (RAG KB + diagnostic engine)
  3.  Interroge la table impliquée (tech_inference / DB schema)
  4.  Cherche la procédure de résolution (procedure_lookup)
  5.  Cherche les tickets Jira liés (jira search)
  6.  Demande les détails d'un ticket (jira explain)
  7.  Demande la date de création du ticket (jira date_creation)
  8.  Demande qui est assigné (jira assignee)
  9.  Cherche des tickets similaires (jira similar)
  10. Recherche logs par équipement DSLAM (equipment log intent)
  11. Interroge la cause racine (root_cause_exploration)
  12. Confirme la cause racine (Root Cause Lock)
  13. Demande un résumé pour hiérarchie (summarize intent)
  14. Génère le message de clôture (closing phase)
  15. Question hors-sujet en fin de conv (off_topic)
  16. Comptage tickets (jira count)
  17. Tickets haute priorité ouverts (jira priority_filter)
  18. Question de suivi sans contexte explicite (follow-up resolution)
  19. Test cross-sources : combine KB + Jira + logs en une seule réponse
  20. Message de création de ticket (write_ticket_message intent)

Chaque tour :
  - Affiche le message utilisateur
  - Affiche la réponse complète
  - Affiche les sources, trust_score, pipeline_mode, sub_intent
  - Valide que les champs attendus sont présents
  - Accumule l'historique pour le tour suivant
"""
import asyncio
import sys
import json
from typing import List, Dict
from app.services.chatbot.chatbot_service import ChatbotService
from app.schemas.chatbot import ChatMessage

# ─── configuration ─────────────────────────────────────────────────────────────
APP_ID = "BRASIL"
SEPARATOR = "═" * 90

# ─── scenario ──────────────────────────────────────────────────────────────────
SCENARIO: List[Dict] = [
    # ── Phase 0 : accueil ──────────────────────────────────────────────────
    {
        "id": 1,
        "label": "Salutation off-topic",
        "message": "Bonjour, tu vas bien ?",
        "expect_mode": None,
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 1 : déclaration d'incident ──────────────────────────────────
    {
        "id": 2,
        "label": "Déclaration incident — erreur B4002 sur DSLAM",
        "message": (
            "Nous avons une erreur B4002 sur le DSLAM DSABX0312 depuis ce matin. "
            "Les ports ne répondent plus et plusieurs clients signalent une perte de connexion."
        ),
        "expect_mode": None,
        "expect_trust_min": 0,
        "expect_no_hallucination": True,
    },

    # ── Phase 2 : exploration de la table DB impliquée ────────────────────
    {
        "id": 3,
        "label": "Interrogation schéma table t_ports",
        "message": "C'est quoi la table t_ports dans BRASIL ? Quelles sont ses colonnes ?",
        "expect_mode": None,
        "expect_trust_min": 0,
        "expect_no_hallucination": True,
    },

    # ── Phase 3 : procédure de résolution ─────────────────────────────────
    {
        "id": 4,
        "label": "Demande procédure de résolution B4002",
        "message": "Quelle est la procédure pour résoudre l'erreur B4002 sur un DSLAM ?",
        "expect_mode": None,
        "expect_trust_min": 0,
        "expect_no_hallucination": True,
    },

    # ── Phase 4 : recherche Jira ───────────────────────────────────────────
    {
        "id": 5,
        "label": "Recherche tickets Jira liés à B4002",
        "message": "Y a-t-il des tickets Jira liés à l'erreur B4002 sur BRASIL ?",
        "expect_mode": "jira_search",
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 4b : détail ticket ───────────────────────────────────────────
    {
        "id": 6,
        "label": "Explique le premier ticket trouvé",
        "message": "Explique-moi le premier ticket trouvé.",
        "expect_mode": "jira_explain",
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 4c : date de création ────────────────────────────────────────
    {
        "id": 7,
        "label": "Date de création du ticket (sub-intent date_creation)",
        "message": "Quelle est la date de création de ce ticket ?",
        "expect_mode": "jira",
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 4d : assigné ─────────────────────────────────────────────────
    {
        "id": 8,
        "label": "Qui est assigné à ce ticket (sub-intent assignee)",
        "message": "Qui est assigné à ce ticket ?",
        "expect_mode": "jira",
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 4e : tickets similaires ─────────────────────────────────────
    {
        "id": 9,
        "label": "Tickets Jira similaires (sub-intent similar)",
        "message": "Y a-t-il d'autres tickets similaires dans BRASIL ?",
        "expect_mode": "jira",
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 5 : recherche logs équipement ───────────────────────────────
    {
        "id": 10,
        "label": "Recherche logs DSLAM DSABX0312",
        "message": (
            "Cherche-moi les événements du DSLAM DSABX0312 dans les logs."
        ),
        "expect_mode": None,
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 6 : exploration cause racine ────────────────────────────────
    {
        "id": 11,
        "label": "Exploration cause racine (root_cause_exploration)",
        "message": (
            "D'après les logs et la procédure, quelle est la cause racine probable "
            "de l'erreur B4002 sur ce DSLAM ?"
        ),
        "expect_mode": None,
        "expect_trust_min": 0,
        "expect_no_hallucination": True,
    },

    # ── Phase 6b : confirmation Root Cause Lock ────────────────────────────
    {
        "id": 12,
        "label": "Confirmation cause racine (Root Cause Lock)",
        "message": (
            "Confirmé : la cause racine est un masque de nommage de fichier incorrect "
            "dans le module SyncDSLAM, qui empêche la synchronisation des ports."
        ),
        "expect_mode": None,
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 7 : synthèse cross-sources ─────────────────────────────────
    {
        "id": 13,
        "label": "Synthèse cross-sources KB + Jira + logs",
        "message": (
            "En te basant sur la procédure de résolution, les tickets Jira et les logs "
            "du DSLAM DSABX0312, donne-moi un plan d'action complet pour résoudre "
            "le problème et empêcher sa récurrence."
        ),
        "expect_mode": None,
        "expect_trust_min": 0,
        "expect_no_hallucination": True,
    },

    # ── Phase 8 : message pour le dépositaire ─────────────────────────────
    {
        "id": 14,
        "label": "Rédaction message client (write_ticket_message)",
        "message": (
            "Rédige un message professionnel pour informer le dépositaire "
            "que le problème est en cours de traitement et sera résolu sous 2h."
        ),
        "expect_mode": None,
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 9 : résumé hiérarchie ───────────────────────────────────────
    {
        "id": 15,
        "label": "Résumé pour la hiérarchie (summarize intent)",
        "message": "Fais-moi un résumé de la situation pour envoyer à mon responsable.",
        "expect_mode": "SUMMARIZE_MANAGEMENT",
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 10 : clôture ────────────────────────────────────────────────
    {
        "id": 16,
        "label": "Message de clôture (closing phase)",
        "message": (
            "Le problème est résolu. Génère le message de clôture pour ce ticket."
        ),
        "expect_mode": None,
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 11 : comptage Jira ──────────────────────────────────────────
    {
        "id": 17,
        "label": "Comptage tickets (jira count)",
        "message": "Combien de tickets BRASIL sont encore ouverts en 2024 ?",
        "expect_mode": "jira",
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 12 : haute priorité ─────────────────────────────────────────
    {
        "id": 18,
        "label": "Tickets haute priorité ouverts (jira priority_filter)",
        "message": "Quels sont les tickets BRASIL haute priorité encore ouverts ?",
        "expect_mode": "jira",
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },

    # ── Phase 13 : question de suivi sans clé explicite ───────────────────
    {
        "id": 19,
        "label": "Question de suivi implicite (follow-up résolution)",
        "message": "Et si les ports restent bloqués après la correction du masque, que faire ?",
        "expect_mode": None,
        "expect_trust_min": 0,
        "expect_no_hallucination": True,
    },

    # ── Phase 14 : off-topic final ────────────────────────────────────────
    {
        "id": 20,
        "label": "Off-topic final — question hors périmètre",
        "message": "Peux-tu me recommander un restaurant à Paris ?",
        "expect_mode": None,
        "expect_trust_min": None,
        "expect_no_hallucination": False,
    },
]


# ─── helpers ───────────────────────────────────────────────────────────────────
def print_header(turn: Dict) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  TOUR {turn['id']:02d} — {turn['label']}")
    print(SEPARATOR)
    print(f"  👤 USER : {turn['message']}")
    print()


def print_response(resp, turn: Dict) -> None:
    print(f"  🤖 RÉPONSE :")
    # Print with indent
    for line in resp.message.splitlines():
        print(f"     {line}")

    if resp.sources:
        print(f"\n  📚 SOURCES ({len(resp.sources)}) :")
        for s in resp.sources:
            name = s.get("name") or s.get("title") or "?"
            rel  = s.get("relevance") or s.get("score") or 0
            print(f"     • {name} (score: {rel:.2%})" if isinstance(rel, float) else f"     • {name}")

    print(f"\n  📊 trust_score={resp.trust_score}  trust_label={resp.trust_label}  mode={resp.pipeline_mode}")
    print(f"     confidence={resp.confidence:.2f}  diagnostic={resp.diagnostic_available}")


def validate_turn(resp, turn: Dict, issues: List[str]) -> None:
    """Run basic assertions and collect failures."""
    # Check mode
    expected_mode = turn.get("expect_mode")
    if expected_mode and resp.pipeline_mode and expected_mode not in (resp.pipeline_mode or ""):
        issues.append(
            f"[Tour {turn['id']}] mode attendu contenant '{expected_mode}', "
            f"obtenu '{resp.pipeline_mode}'"
        )

    # Check trust minimum
    trust_min = turn.get("expect_trust_min")
    if trust_min is not None and resp.trust_score < trust_min:
        issues.append(
            f"[Tour {turn['id']}] trust_score={resp.trust_score} < min={trust_min}"
        )

    # Check no hallucination (look for invented IDs in response)
    import re
    if turn.get("expect_no_hallucination"):
        invented = re.findall(r"BRASIL-[A-Z]+-\d{3}", resp.message)
        if invented:
            issues.append(
                f"[Tour {turn['id']}] IDs inventés détectés : {invented}"
            )
        invented_fr = re.findall(r"\bFR[-_]?\d{4,6}\b", resp.message)
        # Filter out IDs from sources
        src_ids = " ".join(str(s) for s in resp.sources)
        invented_fr = [f for f in invented_fr if f not in src_ids]
        if invented_fr:
            issues.append(
                f"[Tour {turn['id']}] Numéros FR inventés : {invented_fr}"
            )


# ─── main ──────────────────────────────────────────────────────────────────────
async def run_scenario() -> None:
    print("\n" + "█" * 90)
    print("  🧪  TEST CONVERSATION COMPLÈTE — BRASIL AI SUPPORT CHATBOT")
    print("  Couverture : off-topic · RAG KB · DB schema · procédure · Jira (11 sub-intents)")
    print("               ND logs · equipment logs · root-cause · summarize · closing")
    print("               cross-source synthesis · write_ticket_message · anti-hallucination")
    print("█" * 90 + "\n")

    service = ChatbotService()
    history: List[Dict] = []
    issues: List[str] = []
    passed = 0

    for turn in SCENARIO:
        print_header(turn)

        msg = ChatMessage(
            content=turn["message"],
            app_id=APP_ID,
            conversation_id="test-scenario-001",
            conversation_history=history[-12:],  # last 6 exchanges
        )

        try:
            resp = await service.process_message(msg)
        except Exception as exc:
            issues.append(f"[Tour {turn['id']}] EXCEPTION : {exc}")
            print(f"  ❌ ERREUR : {exc}")
            continue

        print_response(resp, turn)
        validate_turn(resp, turn, issues)

        # Accumulate history for follow-up resolution
        history.append({"role": "user",      "content": turn["message"]})
        history.append({"role": "assistant", "content": resp.message})

        if not any(i.startswith(f"[Tour {turn['id']}]") for i in issues):
            print(f"\n  ✅ Tour {turn['id']} OK")
            passed += 1
        else:
            print(f"\n  ⚠️  Tour {turn['id']} : voir avertissements")

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "═" * 90)
    print(f"  RÉSULTAT : {passed}/{len(SCENARIO)} tours validés")
    if issues:
        print(f"\n  ⚠️  {len(issues)} avertissement(s) :")
        for i in issues:
            print(f"     • {i}")
    else:
        print("  🎉 Aucun problème détecté — couverture complète réussie !")
    print("═" * 90 + "\n")


if __name__ == "__main__":
    # Add backend to path if needed
    import os
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    asyncio.run(run_scenario())
