# Operations API — Developer Guide

> Base path: `{API_V1_STR}/operations`  
> Auth: Bearer JWT (same token as `/auth/login`)  
> Content-Type: `application/json`

---

## Authentication

All endpoints require a valid JWT:

```bash
TOKEN=$(curl -s -X POST /api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<pw>"}' | jq -r .access_token)
```

---

## POST /operations/diagnose

Quick operational diagnosis: root cause, evidence, next steps.

### Request

```json
{
  "question": "Le ND N3-EQUIP-001 ne peut pas être supprimé",
  "context": {
    "equipment_id": "N3-EQUIP-001",
    "environment": "BRASIL",
    "intent": "delete_equipment"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | ✅ | Natural language question |
| `context.equipment_id` | string | ☐ | Target equipment ND |
| `context.environment` | string | ☐ | BRASIL / NDC / etc. |
| `context.intent` | string | ☐ | Fine-tune engine intent |

### Response `200`

```json
{
  "mode": "diagnostic",
  "diagnostic": "L'équipement possède des liens actifs T3 qui bloquent la suppression.",
  "root_cause": "equipment_has_active_links",
  "confidence": 0.82,
  "evidence": [
    {
      "source_type": "live_db",
      "description": "Résolution: liens actifs bloquants",
      "confidence": 0.82,
      "reference_id": "FR-4521"
    }
  ],
  "workflow": "FR-4521",
  "limitations": [],
  "next_steps": [
    "Supprimer les liens T3 actifs via l'interface N3",
    "Vérifier l'absence de services résiduels"
  ],
  "runtime_capabilities": {
    "ssh_available": false,
    "db_available": true,
    "logs_available": true,
    "mq_available": true
  }
}
```

### Response modes

| `mode` | Meaning |
|--------|---------|
| `diagnostic` | Confidence ≥ 0.55 — root cause identified |
| `investigation` | Confidence < 0.55 — more info needed |

### Error codes

| HTTP | code | Trigger |
|------|------|---------|
| 422 | `DIAGNOSE_ERROR` | Malformed request or engine validation failure |
| 503 | `ENGINE_ERROR` | Internal engine unavailable |

---

## POST /operations/investigate

Deep RCA with timeline reconstruction (temporal engine + causal graph).

### Request

```json
{
  "entity_type": "equipment",
  "entity_id": "N3-EQUIP-001",
  "question": "Pourquoi la suppression échoue-t-elle en boucle depuis 48h ?"
}
```

### Response `200`

```json
{
  "mode": "diagnostic",
  "timeline": [
    {
      "timestamp": "2024-01-15T14:30:00+00:00",
      "event_type": "DELETE_ATTEMPT",
      "description": "Tentative de suppression bloquée par contrainte FK",
      "severity": "ERROR",
      "source": "temporal_engine"
    }
  ],
  "rca_chain": [
    {
      "cause": "equipment_has_residual_data",
      "confidence": 0.78,
      "evidence": ["FK_VIOLATION", "RESIDUAL_LINKS"],
      "description": "Données résiduelles empêchent la suppression"
    }
  ],
  "anomalies": ["Boucle retry: DELETE_ATTEMPT x5"],
  "evidence": [...],
  "confidence": 0.78,
  "missing_information": [],
  "limitations": [],
  "next_steps": [],
  "runtime_capabilities": {...}
}
```

---

## POST /operations/workflow

FSM state validation and workflow analysis.

### Valid `workflow_type` values

| Value | Description |
|-------|-------------|
| `equipment_delete` | Suppression d'équipement N3 |
| `vlan_delete` | Suppression de VLAN |
| `tp_fix` | Correction TP bloqué |
| `bas_delete` | Suppression BAS |
| `operator_delete` | Suppression opérateur |
| `card_delete` | Suppression carte |

### Request

```json
{
  "workflow_type": "equipment_delete",
  "entity_id": "N3-EQUIP-001",
  "current_state": "ACTIVE"
}
```

### Response `200`

```json
{
  "workflow": "delete_equipment",
  "current_state": null,
  "expected_next_state": null,
  "invalid_transitions": [],
  "blocking_conditions": [],
  "business_rules_triggered": ["RULE_NO_ACTIVE_LINKS", "RULE_NO_RESIDUAL_DATA"],
  "recommended_actions": [
    "Vérifier les services actifs sur l'équipement",
    "Désactiver les liens avant suppression"
  ],
  "runtime_capabilities": {...}
}
```

### Error codes

| HTTP | code | Trigger |
|------|------|---------|
| 422 | `WORKFLOW_UNKNOWN` | `workflow_type` not in valid list |
| 404 | `WORKFLOW_ERROR` | Entity not found |

---

## POST /operations/validate

Validate an operational hypothesis using KB + causal graph.

> ⚠️ Returns `valid: false` if no concrete evidence is found, regardless of LLM confidence.

### Request

```json
{
  "hypothesis": "L'équipement N3-EQUIP-001 a des données résiduelles MQ",
  "context": {
    "nd": "N3-EQUIP-001"
  },
  "mode": "deterministic"
}
```

### Response `200`

```json
{
  "valid": true,
  "confidence": 0.71,
  "supporting_evidence": [
    "RCA: equipment_has_residual_data (conf=0.71)",
    "KB: FR-4521 Suppression équipement (score=0.83)"
  ],
  "contradictions": [],
  "missing_evidence": [],
  "validation_mode": "deterministic",
  "runtime_capabilities": {...}
}
```

---

## POST /operations/search

Semantic search in the FR/KB operational knowledge base.

### Request

```json
{
  "query": "suppression équipement liens actifs BRASIL",
  "top_k": 5,
  "source_types": ["kb", "fr"]
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | — | Search query |
| `top_k` | int | 5 | Max results (1–20) |
| `source_types` | string[] | null | Filter by source: `kb`, `fr`, `live_db` |

### Response `200`

```json
{
  "results": [
    {
      "source_type": "kb",
      "title": "FR-4521: Suppression équipement N3",
      "relevance": 0.91,
      "summary": "Procédure de suppression d'équipement avec vérification des liens actifs...",
      "reference_id": "FR-4521"
    }
  ],
  "total": 1,
  "runtime_capabilities": {...}
}
```

---

## Runtime Capabilities

Every response includes a `runtime_capabilities` block:

```json
{
  "ssh_available": false,
  "db_available": true,
  "logs_available": true,
  "mq_available": true
}
```

When a capability is `false`, actions requiring it are **automatically suppressed** from `next_steps` and `recommended_actions`.

---

## Common Error Response

```json
{
  "code": "ENGINE_ERROR",
  "message": "Erreur moteur interne — réessayez ultérieurement.",
  "details": ["ConnectionRefusedError: [Errno 111]"]
}
```

---

## Integration Examples

### Teams / Slack bot (webhook)

```python
import httpx

async def ask_n3_agent(question: str, nd: str, token: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://your-host/api/v1/operations/diagnose",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": question, "context": {"equipment_id": nd}},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
```

### NOC Dashboard poll

```python
# Validate a known failure hypothesis on every ticket
for ticket in open_tickets:
    result = requests.post(
        f"{BASE_URL}/operations/validate",
        headers=auth_headers,
        json={
            "hypothesis": ticket["description"],
            "context": {"nd": ticket["nd"]},
        },
    ).json()
    if result["valid"] and result["confidence"] > 0.7:
        ticket["auto_rca"] = result["supporting_evidence"][0]
```
