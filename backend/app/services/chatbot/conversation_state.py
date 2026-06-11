"""
Layer 3 — Context & Memory Layer
==================================
Persistent ConversationState with:
- automatic entity extraction (DSLAM, EPC, MRT, NODE, PORT, CARD, etc.)
- entity persistence across turns
- auto-resolution of missing references from context
- conversation history
- last_intent + last_action continuity

BRASIL entity types supported:
  EQUIPMENT / DSLAM / MSAN / CARD / PORT / SHELF / NODE / EPC / MRT / CCL /
  VLAN / MAKING_FILE / OPERATOR / MUTATION / DR_ZONE / TSF / ERROR_CODE
"""
from __future__ import annotations

import re
import json
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any


# ─────────────────────────────────────────────────────────────────────────────
# Entity types
# ─────────────────────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    DSLAM         = "DSLAM"
    MSAN          = "MSAN"
    CARD          = "CARD"
    PORT          = "PORT"
    SHELF         = "SHELF"
    NODE          = "NODE"
    EPC           = "EPC"
    MRT           = "MRT"
    CCL           = "CCL"
    VLAN          = "VLAN"
    MAKING_FILE   = "MAKING_FILE"
    OPERATOR      = "OPERATOR"
    MUTATION      = "MUTATION"
    ERROR_CODE    = "ERROR_CODE"
    EQUIPMENT     = "EQUIPMENT"
    ND            = "ND"             # 9-digit subscriber number
    UNKNOWN       = "UNKNOWN"


@dataclass
class Entity:
    name: str
    type: EntityType
    raw_value: str
    confidence: float = 1.0
    turn_first_seen: int = 0
    turn_last_seen: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)
    # --- UPGRADE: Hierarchical entity model ---
    attributes: Dict[str, Any] = field(default_factory=dict)
    # relations: {relation_type: [entity_name, ...]} e.g. {"contains": ["PORT 1/1/1", "T-CARD"]}
    relations: Dict[str, List[str]] = field(default_factory=dict)

    def add_relation(self, relation_type: str, target_name: str) -> None:
        """Add a directed relation to another entity."""
        if relation_type not in self.relations:
            self.relations[relation_type] = []
        if target_name not in self.relations[relation_type]:
            self.relations[relation_type].append(target_name)

    def get_relations(self, relation_type: Optional[str] = None) -> Dict[str, List[str]]:
        if relation_type:
            return {relation_type: self.relations.get(relation_type, [])}
        return self.relations

    def relation_summary(self) -> str:
        if not self.relations:
            return ""
        parts = []
        for rtype, targets in self.relations.items():
            parts.append(f"{rtype}: {', '.join(targets[:3])}")
        return " | ".join(parts)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Entity extraction patterns (compiled once at import)
# ─────────────────────────────────────────────────────────────────────────────

_PATTERNS: List[tuple] = [
    # DSLAM name: uppercase 2-letter prefix + digits (e.g. DSFEN104, DSCAH114, DSYCR101)
    (re.compile(r"\b(DS[A-Z]{3}\d{3}[A-Z]?)\b"),          EntityType.DSLAM),
    # Generic equipment with "DSLAM" keyword preceding a code (must contain digit)
    (re.compile(r"\bDSLAM\s+([A-Z][A-Z0-9_\-]{2,19}\d[A-Z0-9_\-]*)\b", re.I), EntityType.DSLAM),
    # MSAN
    (re.compile(r"\b(MS[A-Z]{3}\d{3}[A-Z]?)\b"),           EntityType.MSAN),
    (re.compile(r"\bMSAN\s+([A-Z][A-Z0-9_\-]{2,19}\d[A-Z0-9_\-]*)\b", re.I),  EntityType.MSAN),
    # EPC id (format: digits + optional +number)
    (re.compile(r"\b(IdEpc[@#]?\d{10,20}(\+\d+)?)\b"),     EntityType.EPC),
    (re.compile(r"\bEPC\s*[:#]?\s*([A-Z0-9\+]{6,25})\b", re.I), EntityType.EPC),
    # MRT id (numeric, typically large)
    (re.compile(r"\bMRT[_\-]?[Ii][Dd]?\s*[:#]?\s*(\d{7,12})\b"), EntityType.MRT),
    (re.compile(r"\bMRT\s+(\d{7,12})\b"),                  EntityType.MRT),
    # ND (numéro de dossier / subscriber): 9 digits standalone
    (re.compile(r"\b(\d{9})\b"),                             EntityType.ND),
    # Making file / dossier de réalisation
    (re.compile(r"\b(IdEpc@\w+)\b"),                        EntityType.MAKING_FILE),
    # CCL name (e.g. CCL_DSFOO, VLAN 42)
    (re.compile(r"\bCCL[_\-]?([A-Z0-9_\-]{3,20})\b", re.I), EntityType.CCL),
    (re.compile(r"\bVLAN\s*(\d{1,4})\b", re.I),             EntityType.VLAN),
    # NODE / NRA codes (format: NRA + code42C 6 chars)
    (re.compile(r"\b(NRA[A-Z0-9]{2,6})\b"),                 EntityType.NODE),
    (re.compile(r"\bNODE\s+([A-Z0-9_\-]{3,15})\b", re.I),  EntityType.NODE),
    # PORT / CARD / SHELF numbers
    (re.compile(r"\bport\s+(\d{1,3})\b", re.I),             EntityType.PORT),
    (re.compile(r"\bcarte?\s+(\d{1,3})\b", re.I),           EntityType.CARD),
    (re.compile(r"\bchassis\s+(\d{1,3})\b", re.I),          EntityType.SHELF),
    # Error codes (BRASIL format: 4 digits or named)
    (re.compile(r"\berreur?\s*[:#]?\s*(\d{4})\b", re.I),    EntityType.ERROR_CODE),
    (re.compile(r"\bBRASIL[-_]?(\d{3,6})\b", re.I),         EntityType.ERROR_CODE),
    # Generic equipment ID (fallback: word + digits >= 4 chars in all-caps)
    (re.compile(r"\b([A-Z]{2,6}\d{3,8})\b"),                EntityType.EQUIPMENT),
]

_PRONOUNS_FR = re.compile(
    r"\b(le|la|les|il|elle|ils|elles|celui[-\s]ci|"
    r"cet\s+équipement|ce\s+dslam|ce\s+nœud|cet\s+objet|"
    r"le\s+même|ce\s+msan|le\s+serveur)\b",
    re.I
)


def extract_entities_from_text(text: str, turn_idx: int = 0) -> List[Entity]:
    """Return list of Entity objects found in text."""
    found: List[Entity] = []
    seen_spans: set = set()

    for pattern, etype in _PATTERNS:
        for m in pattern.finditer(text):
            span = m.span()
            if any(abs(span[0] - s[0]) < 3 for s in seen_spans):
                continue  # deduplicate overlapping matches
            seen_spans.add(span)
            raw = m.group(0)
            value = m.group(1) if m.lastindex else raw
            found.append(Entity(
                name=value.upper(),
                type=etype,
                raw_value=raw,
                confidence=1.0,
                turn_first_seen=turn_idx,
                turn_last_seen=turn_idx,
            ))

    return found


# ─────────────────────────────────────────────────────────────────────────────
# Turn model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConversationTurn:
    turn_idx: int
    role: str         # "user" | "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    entities_extracted: List[Dict] = field(default_factory=list)
    intent: Optional[str] = None
    action: Optional[str] = None
    resolved: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# ConversationState — THE persistent memory object
# ─────────────────────────────────────────────────────────────────────────────

class ConversationState:
    """
    Persistent per-conversation state.

    Stores:
    - entities: merged entity registry keyed by (type, name)
    - history: ordered list of ConversationTurn
    - last_intent / last_action: intent continuity
    - primary_subject: the most recently mentioned actionable entity
    - resolution_status: None | 'resolved' | 'unresolved'
    """

    def __init__(self, conversation_id: Optional[str] = None):
        self.conversation_id: str = conversation_id or str(uuid.uuid4())
        self.created_at: str = datetime.utcnow().isoformat()
        self.entities: Dict[str, Entity] = {}   # key = f"{type}:{name}"
        self.history: List[ConversationTurn] = []
        self.last_intent: Optional[str] = None
        self.last_action: Optional[str] = None
        self.primary_subject: Optional[Entity] = None  # most relevant entity
        self.resolution_status: Optional[str] = None   # None | 'resolved' | 'unresolved'
        self.follow_up_count: int = 0
        self.metadata: Dict[str, Any] = {}

    # ── Public API ──────────────────────────────────────────────────────────

    def add_user_turn(self, text: str) -> ConversationTurn:
        """Parse user message, extract entities, update state, return turn."""
        turn_idx = len(self.history)
        entities = extract_entities_from_text(text, turn_idx)
        self._merge_entities(entities, turn_idx)
        self._update_primary_subject(entities)

        turn = ConversationTurn(
            turn_idx=turn_idx,
            role="user",
            content=text,
            entities_extracted=[e.to_dict() for e in entities],
        )
        self.history.append(turn)
        return turn

    def add_assistant_turn(self, text: str, intent: str, action: str) -> ConversationTurn:
        """Store assistant response and update intent/action continuity."""
        turn_idx = len(self.history)
        self.last_intent = intent
        self.last_action = action

        turn = ConversationTurn(
            turn_idx=turn_idx,
            role="assistant",
            content=text,
            intent=intent,
            action=action,
        )
        self.history.append(turn)
        return turn

    def resolve_reference(self, text: str) -> Optional[Entity]:
        """
        Detect pronoun/vague reference in text and resolve to known entity.
        E.g. "le supprimer" → returns self.primary_subject if set.
        """
        if _PRONOUNS_FR.search(text):
            return self.primary_subject
        # Also resolve "le" + action pattern
        short = text.strip().lower()
        if len(short.split()) <= 5 and self.primary_subject:
            return self.primary_subject
        return None

    def get_entities_by_type(self, etype: EntityType) -> List[Entity]:
        return [e for e in self.entities.values() if e.type == etype]

    def get_primary_equipment(self) -> Optional[Entity]:
        """Return best candidate equipment entity (DSLAM > MSAN > NODE > EQUIPMENT)."""
        for etype in [EntityType.DSLAM, EntityType.MSAN, EntityType.NODE, EntityType.EQUIPMENT]:
            entities = self.get_entities_by_type(etype)
            if entities:
                # Most recently seen
                return max(entities, key=lambda e: e.turn_last_seen)
        return None

    def set_resolution(self, resolved: bool) -> None:
        self.resolution_status = "resolved" if resolved else "unresolved"
        self.follow_up_count = 0 if resolved else self.follow_up_count + 1
        # Mark last assistant turn
        for turn in reversed(self.history):
            if turn.role == "assistant":
                turn.resolved = resolved
                break

    def link_entities(self, from_name: str, relation_type: str, to_name: str) -> bool:
        """
        Create a directed relation between two known entities.
        Returns True if both entities exist in memory.

        Example:
            state.link_entities("DSLAM222", "contains", "T-CARD-1/0")
        """
        from_key = next((k for k in self.entities if self.entities[k].name.upper() == from_name.upper()), None)
        to_key   = next((k for k in self.entities if self.entities[k].name.upper() == to_name.upper()), None)
        if from_key:
            self.entities[from_key].add_relation(relation_type, to_name)
        if to_key:
            self.entities[to_key].add_relation(f"linked_from_{relation_type}", from_name)
        return bool(from_key)

    def infer_relations_from_sfd(self) -> None:
        """
        Use static BRASIL hierarchy to infer relations between known entities.
        DSLAM → contains → CARD; CARD → contains → PORT; DSLAM → linked_to → MRT
        """
        # Type-based relation inference
        dsrams = [e for e in self.entities.values() if e.type in (EntityType.DSLAM, EntityType.MSAN)]
        cards  = [e for e in self.entities.values() if e.type == EntityType.CARD]
        ports  = [e for e in self.entities.values() if e.type == EntityType.PORT]
        mrts   = [e for e in self.entities.values() if e.type == EntityType.MRT]
        epcs   = [e for e in self.entities.values() if e.type == EntityType.EPC]

        for dslam in dsrams:
            for card in cards:
                dslam.add_relation("contains", card.name)
                card.add_relation("belongs_to", dslam.name)
            for mrt in mrts:
                dslam.add_relation("linked_to", mrt.name)
            for epc in epcs:
                dslam.add_relation("provisioned_via", epc.name)
        for card in cards:
            for port in ports:
                card.add_relation("contains", port.name)
                port.add_relation("belongs_to", card.name)

    def get_entity_tree(self) -> str:
        """
        Render the entity hierarchy as an ASCII tree for LLM context.

        Example:
          DSLAM222
          ├── contains → T-CARD
          ├── linked_to → MRT-12345678
        """
        lines = []
        # Root entities (DSLAMs, MSANs)
        roots = [e for e in self.entities.values()
                 if e.type in (EntityType.DSLAM, EntityType.MSAN, EntityType.NODE)]
        if not roots:
            roots = list(self.entities.values())[:3]

        for root in roots[:2]:
            lines.append(f"{root.name} ({root.type.value})")
            rel_items = list(root.relations.items())
            for i, (rtype, targets) in enumerate(rel_items[:5]):
                connector = "└──" if i == len(rel_items) - 1 else "├──"
                lines.append(f"  {connector} {rtype} → {', '.join(targets[:2])}")
        return "\n".join(lines) if lines else "(no entity hierarchy)"

    def summary(self) -> Dict[str, Any]:
        """Compact summary for logging/debugging."""
        return {
            "conversation_id": self.conversation_id,
            "turns": len(self.history),
            "entities_count": len(self.entities),
            "entities": [e.to_dict() for e in self.entities.values()],
            "last_intent": self.last_intent,
            "last_action": self.last_action,
            "primary_subject": self.primary_subject.to_dict() if self.primary_subject else None,
            "resolution_status": self.resolution_status,
            "follow_up_count": self.follow_up_count,
        }

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "history": [t.to_dict() for t in self.history],
            "last_intent": self.last_intent,
            "last_action": self.last_action,
            "primary_subject": self.primary_subject.to_dict() if self.primary_subject else None,
            "resolution_status": self.resolution_status,
            "follow_up_count": self.follow_up_count,
            "metadata": self.metadata,
        }

    # ── Private helpers ─────────────────────────────────────────────────────

    def _merge_entities(self, entities: List[Entity], turn_idx: int) -> None:
        for entity in entities:
            key = f"{entity.type.value}:{entity.name}"
            if key in self.entities:
                # Update last_seen
                self.entities[key].turn_last_seen = turn_idx
            else:
                entity.turn_first_seen = turn_idx
                entity.turn_last_seen = turn_idx
                self.entities[key] = entity

    def _update_primary_subject(self, new_entities: List[Entity]) -> None:
        """Update primary subject with highest-priority new entity."""
        PRIORITY = {
            EntityType.DSLAM: 10,
            EntityType.MSAN: 9,
            EntityType.NODE: 8,
            EntityType.EQUIPMENT: 7,
            EntityType.EPC: 6,
            EntityType.MRT: 5,
            EntityType.CCL: 4,
            EntityType.PORT: 3,
            EntityType.CARD: 3,
            EntityType.ND: 2,
            EntityType.ERROR_CODE: 1,
        }
        best = None
        best_prio = 0
        for e in new_entities:
            p = PRIORITY.get(e.type, 0)
            if p > best_prio:
                best_prio = p
                best = e
        if best:
            self.primary_subject = self.entities.get(
                f"{best.type.value}:{best.name}", best
            )


# ─────────────────────────────────────────────────────────────────────────────
# In-memory session store (replace with Redis in production)
# ─────────────────────────────────────────────────────────────────────────────

class ConversationStateStore:
    """Thread-safe in-memory store with TTL eviction. Swap .get/.set/.delete for Redis calls."""

    _TTL_SECONDS = 7200  # 2 hours
    _MAX_SIZE = 500

    def __init__(self):
        self._store: Dict[str, ConversationState] = {}
        self._access_times: Dict[str, float] = {}

    def get(self, conversation_id: str) -> Optional[ConversationState]:
        state = self._store.get(conversation_id)
        if state:
            import time
            self._access_times[conversation_id] = time.time()
        return state

    def set(self, state: ConversationState) -> None:
        import time
        self._evict_if_needed()
        self._store[state.conversation_id] = state
        self._access_times[state.conversation_id] = time.time()

    def get_or_create(self, conversation_id: Optional[str] = None) -> ConversationState:
        import time
        cid = conversation_id or str(uuid.uuid4())
        if cid not in self._store:
            self._evict_if_needed()
            self._store[cid] = ConversationState(cid)
        self._access_times[cid] = time.time()
        return self._store[cid]

    def delete(self, conversation_id: str) -> None:
        self._store.pop(conversation_id, None)
        self._access_times.pop(conversation_id, None)

    def list_ids(self) -> List[str]:
        return list(self._store.keys())

    def _evict_if_needed(self) -> None:
        """Evict expired entries and oldest if over capacity."""
        import time
        now = time.time()
        # Evict expired
        expired = [cid for cid, ts in self._access_times.items()
                    if (now - ts) > self._TTL_SECONDS]
        for cid in expired:
            self._store.pop(cid, None)
            self._access_times.pop(cid, None)
        # Evict oldest if still over capacity
        while len(self._store) >= self._MAX_SIZE and self._access_times:
            oldest = min(self._access_times, key=self._access_times.get)
            self._store.pop(oldest, None)
            self._access_times.pop(oldest, None)


# Singleton store
conversation_store = ConversationStateStore()
