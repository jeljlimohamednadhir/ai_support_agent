# Guide d'intÃ©gration â€” OpsPilot AI API

Ce guide explique comment consommer les endpoints de l'**OpsPilot AI** depuis un projet externe (dashboard, bot Teams/Slack, NOC, script Python, app React, etc.).

---

## Table des matiÃ¨res

1. [PrÃ©requis](#1-prÃ©requis)
2. [Authentification](#2-authentification)
3. [RÃ©fÃ©rence des endpoints](#3-rÃ©fÃ©rence-des-endpoints)
   - [POST /diagnose](#31-post-diagnose)
   - [POST /investigate](#32-post-investigate)
   - [POST /workflow](#33-post-workflow)
   - [POST /validate](#34-post-validate)
   - [POST /search](#35-post-search)
  - [Cas d'usage de corrÃ©lation live](#36-cas-dusage-de-corrÃ©lation-live)
4. [ModÃ¨les partagÃ©s](#4-modÃ¨les-partagÃ©s)
5. [Codes d'erreur](#5-codes-derreur)
6. [Exemples par technologie](#6-exemples-par-technologie)
   - [Python (httpx / requests)](#61-python)
   - [JavaScript / TypeScript (fetch)](#62-javascript--typescript)
   - [React hook](#63-react-hook)
   - [curl](#64-curl)
7. [CORS â€” autoriser votre domaine](#7-cors--autoriser-votre-domaine)
8. [Pagination et limites](#8-pagination-et-limites)
9. [Checklist de mise en production](#9-checklist-de-mise-en-production)

---

## 1. PrÃ©requis

| Ã‰lÃ©ment | Valeur |
|---------|--------|
| URL de base | `http://<host>:8000` |
| PrÃ©fixe API | `/api/v1` |
| Format | JSON (`Content-Type: application/json`) |
| Auth | Bearer JWT |
| TLS | RecommandÃ© en prod (HTTPS) |

> En local, le serveur tourne sur `http://localhost:8000`. En staging/prod, remplacer par le FQDN.

---

## 2. Authentification

### 2.1 Obtenir un token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "votre_utilisateur",
  "password": "votre_mot_de_passe"
}
```

**RÃ©ponse :**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2.2 Utiliser le token

Inclure le token dans le header `Authorization` de **chaque requÃªte** :

```
Authorization: Bearer <access_token>
```

### 2.3 DurÃ©e de vie

Le token expire selon la configuration serveur (par dÃ©faut 30 min). ImplÃ©menter un mÃ©canisme de rafraÃ®chissement ou re-login automatique dans votre client.

---

## 3. RÃ©fÃ©rence des endpoints

Tous les endpoints opÃ©rationnels sont sous le prÃ©fixe :

```
POST /api/v1/operations/<endpoint>
```

---

### 3.1 POST /diagnose

**Objectif :** Diagnostic opÃ©rationnel rapide â€” identifie la cause racine, renvoie les preuves et les Ã©tapes de rÃ©solution.

#### RequÃªte

```json
{
  "question": "Le ND 0142785811 ne peut pas Ãªtre supprimÃ©, erreur 1300",
  "context": {
    "equipment_id": "OP49MAB11",
    "nd": "0142785811",
    "environment": "BRASIL",
    "intent": "delete_equipment"
  }
}
```

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `question` | string (3â€“2000 car.) | âœ… | Question en langage naturel |
| `context.equipment_id` | string | â˜ | Identifiant Ã©quipement cible |
| `context.nd` | string | â˜ | NumÃ©ro de dossier |
| `context.environment` | string | â˜ | `BRASIL` / `NDC` / â€¦ |
| `context.intent` | string | â˜ | Affinage d'intention moteur |

#### RÃ©ponse `200 OK`

```json
{
  "mode": "diagnostic",
  "diagnostic": "L'Ã©quipement possÃ¨de des liens actifs T3 qui bloquent la suppression.",
  "root_cause": "equipment_has_active_links",
  "confidence": 0.82,
  "evidence": [
    {
      "source_type": "live_db",
      "description": "RÃ©solution : liens actifs bloquants",
      "confidence": 0.82,
      "reference_id": "FR-4521"
    }
  ],
  "workflow": "FR-4521",
  "limitations": [],
  "next_steps": [
    "Supprimer les liens T3 actifs via l'interface N3",
    "VÃ©rifier l'absence de services rÃ©siduels"
  ],
  "runtime_capabilities": {
    "ssh_available": false,
    "db_available": true,
    "logs_available": true,
    "mq_available": true
  }
}
```

#### Valeurs de `mode`

| Valeur | Signification |
|--------|--------------|
| `diagnostic` | Confiance â‰¥ 0.55 â€” cause racine identifiÃ©e |
| `investigation` | Confiance < 0.55 â€” plus d'informations requises |
| `limited_visibility` | Runtime incomplet (pas de DB, pas de logs) |

---

### 3.2 POST /investigate

**Objectif :** RCA profonde avec reconstruction de timeline. Ã€ utiliser quand `/diagnose` retourne `mode: investigation` ou quand vous avez besoin d'un graphe causal complet.

#### RequÃªte

```json
{
  "entity": {
    "type": "ND",
    "id": "0142785811"
  },
  "question": "Pourquoi la suppression Ã©choue-t-elle en boucle depuis 48h ?"
}
```

| Champ | Type | Requis | Valeurs `type` |
|-------|------|--------|---------------|
| `entity.type` | string | âœ… | `ND` / `EQUIPMENT` / `VLAN` / `TP` / `BAS` / `EPC` |
| `entity.id` | string | âœ… | Identifiant de l'entitÃ© |
| `question` | string | âœ… | Question d'investigation |

#### RÃ©ponse `200 OK`

```json
{
  "mode": "diagnostic",
  "timeline": [
    {
      "timestamp": "2026-05-22T14:30:00+00:00",
      "event_type": "DELETE_ATTEMPT",
      "description": "Tentative de suppression bloquÃ©e par contrainte FK",
      "severity": "ERROR",
      "source": "temporal_engine"
    }
  ],
  "rca_chain": [
    {
      "cause": "equipment_has_residual_data",
      "confidence": 0.78,
      "evidence": ["FK_VIOLATION", "RESIDUAL_LINKS"],
      "description": "DonnÃ©es rÃ©siduelles empÃªchent la suppression"
    }
  ],
  "anomalies": ["Boucle retry : DELETE_ATTEMPT x5"],
  "evidence": [...],
  "confidence": 0.78,
  "missing_information": [],
  "limitations": [],
  "next_steps": [],
  "runtime_capabilities": { ... }
}
```

---

### 3.3 POST /workflow

**Objectif :** Analyse d'un workflow opÃ©rationnel â€” transitions FSM, rÃ¨gles mÃ©tier, conditions bloquantes.

#### Types de workflow supportÃ©s

| `workflow_type` | Description |
|-----------------|-------------|
| `equipment_delete` | Suppression d'Ã©quipement N3 |
| `vlan_delete` | Suppression de VLAN |
| `tp_fix` | Correction TP bloquÃ© |
| `bas_delete` | Suppression BAS |
| `operator_delete` | Suppression opÃ©rateur |
| `card_delete` | Suppression carte |

#### RequÃªte

```json
{
  "workflow_type": "equipment_delete",
  "entity_id": "OP49MAB11"
}
```

#### RÃ©ponse `200 OK`

```json
{
  "workflow": "delete_equipment",
  "current_state": null,
  "expected_next_state": null,
  "invalid_transitions": [],
  "blocking_conditions": [
    "Ã‰quipement possÃ¨de des services actifs"
  ],
  "business_rules_triggered": [
    "RULE_NO_ACTIVE_LINKS",
    "RULE_NO_RESIDUAL_DATA"
  ],
  "recommended_actions": [
    "VÃ©rifier les services actifs sur l'Ã©quipement",
    "DÃ©sactiver les liens avant suppression"
  ],
  "runtime_capabilities": { ... }
}
```

---

### 3.4 POST /validate

**Objectif :** Valider une hypothÃ¨se opÃ©rationnelle via la base de connaissances + graphe causal. Ne retourne `valid: true` que si des preuves concrÃ¨tes existent.

#### RequÃªte

```json
{
  "hypothesis": "Le blocage provient d'un MQ ACK absent sur le dossier 0142785811",
  "context": {
    "nd": "0142785811",
    "equipment_id": "OP49MAB11"
  }
}
```

#### RÃ©ponse `200 OK`

```json
{
  "valid": true,
  "confidence": 0.71,
  "supporting_evidence": [
    "RCA : equipment_has_residual_data (conf=0.71)",
    "KB : FR-4521 Suppression Ã©quipement (score=0.83)"
  ],
  "contradictions": [],
  "missing_evidence": [],
  "validation_mode": "deterministic",
  "runtime_capabilities": { ... }
}
```

> âš ï¸ Si `valid: false` avec `missing_evidence` non vide, enrichissez la requÃªte avec plus de contexte avant de conclure.

---

### 3.5 POST /search

**Objectif :** Recherche sÃ©mantique dans la base de connaissances FR/N3. Retourne les rÃ©sultats classÃ©s par pertinence.

#### RequÃªte

```json
{
  "query": "Erreur 1300 suppression Ã©quipement liens actifs BRASIL",
  "top_k": 5,
  "source_types": ["kb", "fr"]
}
```

| Champ | Type | DÃ©faut | Contraintes |
|-------|------|--------|-------------|
| `query` | string | â€” | 3â€“500 caractÃ¨res |
| `top_k` | int | `5` | 1â€“20 |
| `source_types` | string[] | `null` (tous) | `kb` / `fr` / `live_db` |

#### RÃ©ponse `200 OK`

```json
{
  "results": [
    {
      "source_type": "kb",
      "title": "FR-4521 : Suppression Ã©quipement N3",
      "relevance": 0.91,
      "summary": "ProcÃ©dure de suppression d'Ã©quipement avec vÃ©rification des liens actifs...",
      "reference_id": "FR-4521"
    }
  ],
  "total": 1,
  "runtime_capabilities": { ... }
}
```

---

### 3.6 Cas d'usage de corrÃ©lation live

Ces exemples montrent comment consommer l'API quand vous voulez **croiser plusieurs sources** (`kb`, `live_log`, `live_db`, `rca`) dans un autre projet.

#### Cas 1 — Diagnostic enrichi par logs et DB

**Objectif :** dÃ©tecter un blocage ND en combinant la base de connaissance, les signaux logs et la donnÃ©e runtime.

**Flux recommandÃ© :**

1. Appeler `/operations/diagnose`
2. Lire `evidence[]` et `runtime_capabilities`
3. Si la confiance est faible, enchaÃ®ner avec `/operations/investigate`

**Exemple de rÃ©ponse attendue :**

```json
{
  "mode": "diagnostic",
  "root_cause": "equipment_has_residual_data",
  "confidence": 0.78,
  "evidence": [
    {
      "source_type": "live_db",
      "description": "Des liens rÃ©siduels existent encore pour l'Ã©quipement",
      "confidence": 0.82,
      "reference_id": "FR-4521"
    },
    {
      "source_type": "live_log",
      "description": "Erreur FK_VIOLATION observÃ©e dans les logs BRASIL",
      "confidence": 0.74,
      "reference_id": null
    }
  ],
  "runtime_capabilities": {
    "db_available": true,
    "logs_available": true,
    "ssh_available": false,
    "mq_available": true
  }
}
```

**CÃ´tÃ© client :** affichez les preuves par source (`DB`, `Logs`, `KB`) pour rendre la corrÃ©lation visible dans votre UI.

#### Cas 2 — Investigation RCA avec timeline live

**Objectif :** comprendre une boucle d'Ã©chec ou une erreur intermittente grÃ¢ce Ã  la reconstruction temporelle.

**Flux recommandÃ© :**

1. Appeler `/operations/investigate`
2. Afficher `timeline[]`, `rca_chain[]` et `anomalies[]`
3. Remonter les `missing_information[]` si le moteur demande plus de contexte

**Exemple mÃ©tier :**

- Une app NOC reÃ§oit un ticket sur un ND bloquÃ©
- L'API renvoie une sÃ©quence de `DELETE_ATTEMPT`, `RETRY_LOOP`, `FK_VIOLATION`
- Le front reconstruit une chronologie lisible et suggÃ¨re la cause dominante

#### Cas 3 — Vue manager avec corrÃ©lation de sources

**Objectif :** exposer dans un dashboard la rÃ©partition des diagnostics selon leurs preuves.

**Usage typique :**

- `live_db` dominant : problÃ¨mes de cohÃ©rence ou donnÃ©es rÃ©siduelles
- `live_log` dominant : erreurs d'exÃ©cution, exceptions applicatives, timeouts
- `kb` dominant : procÃ©dures connues, incidents dÃ©jÃ  documentÃ©s
- `rca` dominant : hypothÃ¨ses causales et enchaÃ®nements d'Ã©vÃ©nements

#### Bonnes pratiques d'intÃ©gration

- **Toujours lire `runtime_capabilities`** : si `logs_available=false`, ne promettez pas d'analyse live des logs dans l'interface.
- **Afficher `source_type` dans l'UI** : cela rend la corrÃ©lation comprÃ©hensible pour l'utilisateur final.
- **Traiter `mode=investigation` diffÃ©remment** : afficher un message “analyse en cours / preuves insuffisantes” plutÃ´t qu'une cause racine ferme.
- **Regrouper les preuves** : une carte “DB”, une carte “Logs”, une carte “KB” fonctionne bien dans un dashboard ou un copilot support.

---

## 4. ModÃ¨les partagÃ©s

### `RuntimeCapabilities`

PrÃ©sent dans **toutes** les rÃ©ponses. Indique ce qui Ã©tait disponible au moment du traitement.

```json
{
  "ssh_available": false,
  "db_available": true,
  "logs_available": true,
  "mq_available": true
}
```

Quand une capacitÃ© est `false`, les actions dÃ©pendantes sont **automatiquement supprimÃ©es** de `next_steps` et `recommended_actions`. Adapter l'UI en consÃ©quence (ex : griser les actions SSH si `ssh_available: false`).

### `EvidenceItem`

```json
{
  "source_type": "live_db | live_log | ssh | kb | rca",
  "description": "Description de la preuve",
  "confidence": 0.82,
  "reference_id": "FR-4521"
}
```

---

## 5. Codes d'erreur

### Format d'erreur standard

```json
{
  "detail": {
    "code": "WORKFLOW_UNKNOWN",
    "message": "Workflow type 'xyz' non reconnu.",
    "details": ["Types valides : equipment_delete, vlan_delete, ..."]
  }
}
```

### Table des codes

| HTTP | `code` | Cause | Action recommandÃ©e |
|------|--------|-------|--------------------|
| 422 | `LOW_EVIDENCE` | Confiance trop faible | Utiliser `/investigate` |
| 422 | `WORKFLOW_UNKNOWN` | `workflow_type` invalide | VÃ©rifier les types supportÃ©s |
| 422 | `VALIDATION_FAILED` | HypothÃ¨se non validable | Enrichir le contexte |
| 404 | `ENTITY_NOT_FOUND` | EntitÃ© introuvable | VÃ©rifier l'ID |
| 503 | `ENGINE_ERROR` | Moteur interne KO | RÃ©essayer aprÃ¨s dÃ©lai |
| 503 | `RUNTIME_UNAVAILABLE` | Infra inaccessible | VÃ©rifier la connectivitÃ© |
| 401 | `ACCESS_DENIED` | Token absent/expirÃ© | Re-login |

---

## 6. Exemples par technologie

### 6.1 Python

#### Installation

```bash
pip install httpx
```

#### Client rÃ©utilisable

```python
# n3_client.py
import httpx
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000/api/v1"


class N3AgentClient:
    def __init__(self, username: str, password: str):
        self._base = BASE_URL
        self._token: Optional[str] = None
        self._http = httpx.Client(timeout=30)
        self._login(username, password)

    def _login(self, username: str, password: str) -> None:
        r = self._http.post(
            f"{self._base}/auth/login",
            json={"username": username, "password": password},
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def diagnose(self, question: str, context: Optional[Dict] = None) -> Dict:
        r = self._http.post(
            f"{self._base}/operations/diagnose",
            headers=self._headers,
            json={"question": question, "context": context or {}},
        )
        r.raise_for_status()
        return r.json()

    def investigate(self, entity_type: str, entity_id: str, question: str) -> Dict:
        r = self._http.post(
            f"{self._base}/operations/investigate",
            headers=self._headers,
            json={
                "entity": {"type": entity_type, "id": entity_id},
                "question": question,
            },
        )
        r.raise_for_status()
        return r.json()

    def workflow(self, workflow_type: str, entity_id: str) -> Dict:
        r = self._http.post(
            f"{self._base}/operations/workflow",
            headers=self._headers,
            json={"workflow_type": workflow_type, "entity_id": entity_id},
        )
        r.raise_for_status()
        return r.json()

    def validate(self, hypothesis: str, context: Optional[Dict] = None) -> Dict:
        r = self._http.post(
            f"{self._base}/operations/validate",
            headers=self._headers,
            json={"hypothesis": hypothesis, "context": context or {}},
        )
        r.raise_for_status()
        return r.json()

    def search(self, query: str, top_k: int = 5) -> Dict:
        r = self._http.post(
            f"{self._base}/operations/search",
            headers=self._headers,
            json={"query": query, "top_k": top_k},
        )
        r.raise_for_status()
        return r.json()
```

#### Utilisation

```python
from n3_client import N3AgentClient

client = N3AgentClient("admin", "secret")

# Diagnostic rapide
result = client.diagnose(
    question="ND 0142785811 bloquÃ© Ã  l'Ã©tat 2",
    context={"nd": "0142785811", "environment": "BRASIL"}
)
print(result["root_cause"])      # equipment_has_active_links
print(result["confidence"])      # 0.82
print(result["next_steps"])

# Si mode investigation â†’ investigation profonde
if result["mode"] == "investigation":
    deep = client.investigate("ND", "0142785811", result["diagnostic"])
    for hop in deep["rca_chain"]:
        print(f"{hop['cause']} â€” conf={hop['confidence']}")

# Recherche KB
hits = client.search("erreur 1300 suppression Ã©quipement")
for h in hits["results"]:
    print(f"[{h['relevance']:.0%}] {h['title']} â€” {h['summary'][:80]}")
```

#### Version async (httpx)

```python
import httpx

async def diagnose_async(token: str, question: str) -> dict:
    async with httpx.AsyncClient(base_url="http://localhost:8000") as c:
        r = await c.post(
            "/api/v1/operations/diagnose",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": question},
        )
        r.raise_for_status()
        return r.json()
```

---

### 6.2 JavaScript / TypeScript

```typescript
// n3AgentClient.ts

const BASE_URL = "http://localhost:8000/api/v1";

interface DiagnoseContext {
  equipment_id?: string;
  nd?: string;
  environment?: string;
  intent?: string;
}

interface DiagnoseResponse {
  mode: "diagnostic" | "investigation" | "limited_visibility";
  diagnostic: string;
  root_cause: string | null;
  confidence: number;
  next_steps: string[];
  limitations: string[];
  runtime_capabilities: {
    ssh_available: boolean;
    db_available: boolean;
    logs_available: boolean;
    mq_available: boolean;
  };
}

async function login(username: string, password: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
  const data = await res.json();
  return data.access_token;
}

async function diagnose(
  token: string,
  question: string,
  context?: DiagnoseContext
): Promise<DiagnoseResponse> {
  const res = await fetch(`${BASE_URL}/operations/diagnose`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question, context }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail?.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

async function search(
  token: string,
  query: string,
  topK = 5
): Promise<{ results: any[]; total: number }> {
  const res = await fetch(`${BASE_URL}/operations/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

// --- Utilisation ---
const token = await login("admin", "secret");
const result = await diagnose(token, "ND 0142785811 bloquÃ©", {
  nd: "0142785811",
  environment: "BRASIL",
});
console.log(result.mode, result.confidence, result.next_steps);
```

---

### 6.3 React hook

```tsx
// hooks/useN3Diagnose.ts
import { useState, useCallback } from "react";

const BASE = "http://localhost:8000/api/v1";

interface UseDiagnoseResult {
  loading: boolean;
  error: string | null;
  result: any | null;
  run: (question: string, context?: Record<string, string>) => Promise<void>;
}

export function useN3Diagnose(token: string): UseDiagnoseResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const run = useCallback(
    async (question: string, context?: Record<string, string>) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${BASE}/operations/diagnose`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ question, context }),
        });
        if (!res.ok) {
          const e = await res.json();
          throw new Error(e.detail?.message ?? `Erreur ${res.status}`);
        }
        setResult(await res.json());
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  return { loading, error, result, run };
}
```

```tsx
// DiagnosePanel.tsx
import { useN3Diagnose } from "./hooks/useN3Diagnose";

export function DiagnosePanel({ token }: { token: string }) {
  const { loading, error, result, run } = useN3Diagnose(token);

  return (
    <div>
      <button onClick={() => run("ND 0142785811 bloquÃ©", { nd: "0142785811" })}>
        Diagnostiquer
      </button>

      {loading && <p>Analyse en coursâ€¦</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {result && (
        <div>
          <p><strong>Mode :</strong> {result.mode}</p>
          <p><strong>Confiance :</strong> {(result.confidence * 100).toFixed(0)}%</p>
          <p><strong>Cause racine :</strong> {result.root_cause ?? "â€”"}</p>

          {!result.runtime_capabilities.db_available && (
            <p style={{ color: "orange" }}>âš  Base de donnÃ©es indisponible</p>
          )}

          <ul>
            {result.next_steps.map((s: string, i: number) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

---

### 6.4 curl

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secret"}' | jq -r .access_token)

# 2. Diagnostic
curl -s -X POST http://localhost:8000/api/v1/operations/diagnose \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "ND 0142785811 bloquÃ© Ã  l Ã©tat 2",
    "context": {"nd": "0142785811", "environment": "BRASIL"}
  }' | jq .

# 3. Recherche KB
curl -s -X POST http://localhost:8000/api/v1/operations/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "erreur 1300 suppression Ã©quipement", "top_k": 3}' | jq .

# 4. Validation d'hypothÃ¨se
curl -s -X POST http://localhost:8000/api/v1/operations/validate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hypothesis": "Le blocage est dÃ» Ã  un MQ ACK absent",
    "context": {"nd": "0142785811"}
  }' | jq '.valid, .confidence, .supporting_evidence'

# 5. Workflow
curl -s -X POST http://localhost:8000/api/v1/operations/workflow \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"workflow_type": "equipment_delete", "entity_id": "OP49MAB11"}' | jq .
```

---

## 7. CORS â€” autoriser votre domaine

Par dÃ©faut le serveur autorise :
- `http://localhost:3000`
- `http://localhost:5173`

Pour ajouter un domaine (ex : votre app de prod), modifier la variable d'environnement dans `.env` :

```env
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://votre-app.example.com
```

Puis redÃ©marrer le serveur.

---

## 8. Pagination et limites

| Endpoint | Limite max |
|----------|-----------|
| `/search` | `top_k` max = 20 |
| `/diagnose` | `question` max = 2000 car. |
| `/validate` | `hypothesis` max = 1000 car. |
| `/investigate` | timeline max 15 Ã©vÃ©nements retournÃ©s |

---

## 9. Checklist de mise en production

- [ ] Remplacer `http://localhost:8000` par l'URL de prod dans le client
- [ ] Activer HTTPS et valider le certificat (`verify=True` dans httpx/requests)
- [ ] Stocker le token dans un stockage sÃ©curisÃ© (pas dans `localStorage`)
- [ ] ImplÃ©menter le refresh automatique du token avant expiration
- [ ] Ajouter le domaine de votre app dans `BACKEND_CORS_ORIGINS`
- [ ] GÃ©rer les codes 503 avec retry exponentiel (max 3 tentatives)
- [ ] Logger les champs `confidence`, `mode` et `limitations` cÃ´tÃ© client pour le monitoring
- [ ] Griser les actions dÃ©pendantes des capacitÃ©s runtime Ã  `false` dans l'UI
- [ ] Ne jamais exposer le token JWT dans les logs applicatifs

---

## Swagger interactif

L'interface Swagger est disponible Ã  :

```
http://localhost:8000/docs
```

Elle permet de tester tous les endpoints directement depuis le navigateur, avec auto-complÃ©tion des schemas JSON.

