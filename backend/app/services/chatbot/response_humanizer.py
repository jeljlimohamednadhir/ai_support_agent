"""
Response Humanizer — Phase 5 & 6
==================================
Transforms technical chatbot responses into natural, collaborative, and
friendly messages without sacrificing accuracy.

Also provides resolution summary generation (Phase 6):
  • Technical incident report for N3 engineers
  • Plain-language message for the depositor

Usage::

    from app.services.chatbot.response_humanizer import humanize, build_resolution_summary
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────── #
# Phase 5 — Natural language persona layer                            #
# ─────────────────────────────────────────────────────────────────── #

# Patterns that indicate a dry, robotic opening we want to replace
_ROBOTIC_OPENINGS = re.compile(
    r"^(erreur\s+\d+\s+détect[eé]e?\s*\.|"
    r"code\s+(d'erreur|retour)\s*:\s*\d+\s*\.|"
    r"le\s+syst[eè]me\s+a\s+retourné\s+une\s+erreur\s*\.|"
    r"r[eé]férez[- ]vous\s+(à|a)\s+la?\s+FR[-\s]?\d+\s*\.|"
    r"consulter\s+la?\s+FR[-\s]?\d+\s*\.|"
    r"voir\s+la?\s+FR[-\s]?\d+\s*\.)",
    re.IGNORECASE,
)

# Friendly connector phrases
_REASONING_BRIDGE = (
    "Voici ce que j'ai trouvé dans la base de connaissance et les incidents passés :"
)
_ACTION_BRIDGE = "Voici les étapes que je vous recommande de vérifier :"
_CONFIRM_BRIDGE = "Pour confirmer, voyons quelques points ensemble :"


@dataclass
class HumanizeContext:
    """Context hints that drive the humanization style."""
    has_error_code: bool = False
    has_procedure_steps: bool = False
    has_hypothesis: bool = False
    has_correlation: bool = False
    phase: str = "diagnostic"          # diagnostic | investigation | resolution | closing
    error_code: str = ""
    entity: str = ""


def humanize(
    response_text: str,
    context: Optional[HumanizeContext] = None,
) -> str:
    """
    Apply human-style transformations to a raw LLM response.
    The function is non-destructive: it only adds/reformats structure,
    never removes valid technical content.
    """
    if not response_text or len(response_text) < 20:
        return response_text

    ctx = context or HumanizeContext()
    text = response_text.strip()

    # 1. Replace robotic "Error NNN detected. Refer to FR-42." openings
    text = _replace_robotic_opening(text, ctx)

    # 2. Add reasoning bridge before lists of steps
    text = _add_reasoning_bridge(text, ctx)

    # 3. Soften imperative commands into collaborative suggestions
    text = _soften_imperatives(text)

    # 4. Ensure the response ends with a forward-looking question/offer
    text = _add_followup_offer(text, ctx)

    return text


def _replace_robotic_opening(text: str, ctx: HumanizeContext) -> str:
    """Replace dry 'Error X detected. See FR-Y.' with a contextual intro."""
    if not _ROBOTIC_OPENINGS.match(text):
        return text

    if ctx.error_code:
        intro = (
            f"J'ai repéré le code d'erreur **{ctx.error_code}** dans votre message.\n"
            f"Ce code apparaît généralement lorsqu'une ressource ne peut pas être allouée "
            f"ou qu'une contrainte empêche l'opération.\n\n"
            f"D'après la base de connaissance et les incidents similaires, "
            f"la cause la plus probable est un conflit de provisionnement.\n\n"
            f"Vérifions quelques points ensemble pour confirmer cela.\n\n"
        )
    elif ctx.entity:
        intro = (
            f"Je vois que le composant **{ctx.entity}** est impliqué dans cet incident.\n\n"
        )
    else:
        intro = "Voici ce que j'ai identifié concernant votre incident :\n\n"

    # Remove the robotic opening sentence(s) and prepend human intro
    cleaned = _ROBOTIC_OPENINGS.sub("", text).strip()
    return intro + cleaned


def _add_reasoning_bridge(text: str, ctx: HumanizeContext) -> str:
    """
    Before a numbered/bulleted list of steps, add a reasoning bridge
    explaining *why* we are doing these steps.
    """
    # Detect if text contains a numbered procedure list
    has_list = bool(re.search(r'^\s*[1-9]\.\s', text, re.MULTILINE))
    if not has_list:
        return text

    # Check if there is already a bridge / explanation before the list
    first_list_pos = re.search(r'^\s*[1-9]\.\s', text, re.MULTILINE)
    if not first_list_pos:
        return text

    pre_list = text[:first_list_pos.start()].strip()
    # If the pre-list content is shorter than 40 chars, it's likely just a title
    if len(pre_list) < 40:
        bridge = _ACTION_BRIDGE if ctx.phase in ("investigation", "resolution") else _REASONING_BRIDGE
        return pre_list + ("\n\n" if pre_list else "") + bridge + "\n\n" + text[first_list_pos.start():]
    return text


def _soften_imperatives(text: str) -> str:
    """
    Replace abrupt imperative forms with collaborative suggestions.
    Applies only to sentence-starting imperatives to avoid false positives.
    """
    substitutions = [
        # "Vérifiez X." → "Je vous invite à vérifier X."
        (re.compile(r'(?m)^(Vérifiez|Contrôlez|Consultez|Exécutez|Lancez)\b'),
         r'Je vous invite à \1'),
        # "Relancez le script." → "Vous pouvez relancer le script."
        (re.compile(r'(?m)^(Relancez|Redémarrez|Supprimez|Forcez|Réinitialisez)\b'),
         r'Vous pouvez \1'),
    ]
    for pattern, replacement in substitutions:
        text = pattern.sub(replacement, text)
    return text


def _add_followup_offer(text: str, ctx: HumanizeContext) -> str:
    """
    If the response doesn't already end with a question or offer,
    append a short collaborative closing line.
    """
    # Already ends with a question mark or an offer phrase → keep as-is
    closing_indicators = re.compile(
        r"(\?|dites[- ]moi|n'hésitez\s+pas|faites[- ]moi|avez[- ]vous|"
        r"pouvez[- ]vous|est[- ]ce\s+que|qu'en\s+pensez|souhaitez[- ]vous)",
        re.IGNORECASE,
    )
    last_200 = text[-200:] if len(text) > 200 else text
    if closing_indicators.search(last_200):
        return text

    # Phase-appropriate closing
    phase_closings = {
        "diagnostic":    "\n\nN'hésitez pas à me donner plus de détails sur le contexte — cela m'aidera à affiner l'analyse.",
        "investigation": "\n\nAvez-vous déjà eu l'occasion de vérifier ces points ? Je peux vous guider étape par étape.",
        "resolution":    "\n\nDites-moi si la correction a bien fonctionné, et nous pourrons passer à la clôture de l'incident.",
        "closing":       "\n\nEst-ce qu'il y a autre chose à documenter avant de clôturer ?",
    }
    return text + phase_closings.get(ctx.phase, "")


# ─────────────────────────────────────────────────────────────────── #
# Phase 6 — Resolution summary generator                              #
# ─────────────────────────────────────────────────────────────────── #

@dataclass
class IncidentResolutionData:
    """All data needed to generate the resolution summary."""
    incident_description: str = ""
    root_cause: str = ""
    diagnostic_steps: list[str] = None          # type: ignore[assignment]
    resolution_applied: str = ""
    preventive_recommendation: str = ""
    application: str = "BRASIL"
    affected_component: str = ""
    jira_ticket_id: str = ""
    confirmed_by: str = ""

    def __post_init__(self):
        if self.diagnostic_steps is None:
            self.diagnostic_steps = []


def build_resolution_summary(data: IncidentResolutionData) -> dict[str, str]:
    """
    Build two messages from resolution data:
      • 'technical'  — structured report for N3 engineers
      • 'depositor'  — plain-language message for the end user

    Returns::

        {
            "technical":  "...",
            "depositor":  "...",
        }
    """
    # ── Technical report ────────────────────────────────────────── #
    steps_text = ""
    if data.diagnostic_steps:
        steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(data.diagnostic_steps))
    else:
        steps_text = "  (Non documentées dans cette session)"

    jira_line = f"\n**Ticket Jira :** {data.jira_ticket_id}" if data.jira_ticket_id else ""
    component_line = f"\n**Composant impacté :** {data.affected_component}" if data.affected_component else ""

    technical = (
        f"## Rapport d'incident — {data.application}\n\n"
        f"**Incident**\n{data.incident_description or 'Non renseigné'}\n"
        f"{component_line}"
        f"{jira_line}\n\n"
        f"**Cause racine**\n{data.root_cause or 'Non confirmée'}\n\n"
        f"**Étapes de diagnostic**\n{steps_text}\n\n"
        f"**Résolution appliquée**\n{data.resolution_applied or 'Non documentée'}\n\n"
        f"**Recommandation préventive**\n{data.preventive_recommendation or 'Surveiller les alertes similaires dans les 48h.'}\n"
    )

    # ── Depositor message ────────────────────────────────────────── #
    # Plain French, no jargon
    root_cause_plain = _simplify_technical_jargon(data.root_cause)
    resolution_plain = _simplify_technical_jargon(data.resolution_applied)

    depositor = (
        f"Bonjour,\n\n"
        f"Nous vous informons que le problème affectant votre demande a été résolu.\n\n"
        f"**Cause du problème :** {root_cause_plain or 'Un dysfonctionnement technique interne a été identifié.'}\n\n"
        f"**Ce qui a été fait :** {resolution_plain or 'La configuration a été corrigée et le service a été rétabli.'}\n\n"
        f"Le service devrait désormais fonctionner normalement. "
        f"N'hésitez pas à nous contacter si le problème venait à se reproduire.\n\n"
        f"Cordialement,\nL'équipe Support N3"
    )

    return {"technical": technical.strip(), "depositor": depositor.strip()}


# Simplify common technical terms for depositor messages
_JARGON_SUBSTITUTIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bPPPoE\b', re.I),               "le protocole d'authentification"),
    (re.compile(r'\bRADIUS\b', re.I),               "le serveur d'authentification"),
    (re.compile(r'\bVLAN\b', re.I),                 "la configuration réseau"),
    (re.compile(r'\bDSLAM\b', re.I),                "l'équipement réseau"),
    (re.compile(r'\bOLT\b', re.I),                  "l'équipement fibre optique"),
    (re.compile(r'\bprovisionnement\b', re.I),       "l'activation du service"),
    (re.compile(r'\bDHCP\b', re.I),                 "l'attribution d'adresse IP"),
    (re.compile(r'\bexception Java\b', re.I),        "une erreur applicative"),
    (re.compile(r'\bstack trace\b', re.I),           "le journal d'erreurs"),
    (re.compile(r'\bNRO\b', re.I),                  "le nœud réseau"),
    (re.compile(r'\bSRO\b', re.I),                  "le sous-répartiteur réseau"),
]


def _simplify_technical_jargon(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in _JARGON_SUBSTITUTIONS:
        text = pattern.sub(replacement, text)
    return text


# ─────────────────────────────────────────────────────────────────── #
# Helper: build IncidentResolutionData from conversation state        #
# ─────────────────────────────────────────────────────────────────── #

def build_resolution_data_from_state(
    conv_state,             # ConversationState from diagnostic_behavior
    history: list[dict],
    application: str = "BRASIL",
) -> IncidentResolutionData:
    """
    Reconstruct IncidentResolutionData from the conversation state and
    history.  Used by the closing phase handler.
    """
    # Root cause
    root_cause = getattr(conv_state, "confirmed_root_cause", "") or ""

    # Incident description: first user message
    incident_desc = ""
    for msg in history:
        if msg.get("role") == "user":
            incident_desc = msg["content"][:300]
            break

    # Affected component: scan history for equipment names
    component = ""
    _eq_pattern = re.compile(
        r"\b(DSLAM[-\s]?\w+|NRO\w+|SRO\w+|OLT\w+|BSAU\w+|NENIC\w+|NBLIL\w+)\b",
        re.IGNORECASE,
    )
    for msg in history:
        m = _eq_pattern.search(msg.get("content", ""))
        if m:
            component = m.group(0).upper()
            break

    # Diagnostic steps: collect assistant messages that contain numbered lists
    diag_steps: list[str] = []
    for msg in history:
        if msg.get("role") == "assistant":
            found = re.findall(r'^\s*[1-9]\.\s+(.+)$', msg["content"], re.MULTILINE)
            diag_steps.extend(found[:3])
        if len(diag_steps) >= 6:
            break

    # Resolution applied: last assistant message in RESOLUTION phase (heuristic)
    resolution_applied = ""
    for msg in reversed(history):
        if msg.get("role") == "assistant" and len(msg["content"]) > 50:
            resolution_applied = msg["content"][:400]
            break

    return IncidentResolutionData(
        incident_description=incident_desc,
        root_cause=root_cause,
        diagnostic_steps=diag_steps[:6],
        resolution_applied=resolution_applied,
        application=application,
        affected_component=component,
    )
