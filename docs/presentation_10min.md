# Présentation — Agent IA Support N3 BRASIL
## 10 minutes | 6 slides

---

## SLIDE 1 — Titre

**Agent IA d'Investigation N3 — BRASIL**

*De 45 min de diagnostic manuel à 30 secondes de réponse structurée*

Équipe : [Votre nom]
Date : Juin 2026

---

## SLIDE 2 — Problématique

### Le support N3 aujourd'hui

| Constat | Impact |
|---------|--------|
| **279 incidents/an** sur BRASIL (10 phases récurrentes) | Charge N3 saturée |
| Temps moyen de diagnostic : **45 min** | SLA dépassés |
| Connaissance dispersée (FR, code Java, logs, BDD, Jira) | Dépendance aux experts |
| Pas de capitalisation : résolutions perdues | Mêmes incidents reviennent |
| Accès SSH/BDD manuel pour chaque investigation | Risque d'erreur humaine |

**Résultat** : L'expert N3 passe 80% de son temps à chercher, 20% à résoudre.

---

## SLIDE 3 — Solution

### Un assistant IA qui investigue comme un expert N3

```
Question utilisateur
    ↓
┌─────────────────────────────────────────┐
│  1. Compréhension (NLP + Intent)        │
│  2. Recherche vectorielle (210 FR)      │
│  3. Diagnostic live (SSH → BDD + logs)  │
│  4. Corrélation multi-sources (L5)      │
│  5. Validation anti-hallucination (L6)  │
│  6. Réponse structurée N3 (L7)         │
│  7. Apprentissage continu (L8)          │
└─────────────────────────────────────────┘
    ↓
Réponse avec : cause racine + preuves + procédure + code source
```

**Stack** : FastAPI · Groq LLM · Qdrant · Neo4j · Paramiko SSH · React

**Sécurité** : Mode lecture seule — aucune modification en production

---

## SLIDE 4 — Démo live (2 min)

### 3 scénarios clés

| # | Question | Ce que l'IA fait |
|---|----------|-----------------|
| 1 | "Suppression DSLAM DSROB362 impossible" | Identifie l'entité → cherche en BDD → cite FR 189 → donne la procédure |
| 2 | "Quelle méthode Java supprime un DSLAM ?" | Trouve `ManageDslamBusinessImpl.deleteDslam()` ligne 1787 |
| 3 | "Pourquoi ce VLAN est occupé ?" | Explique les compteurs `t_res_prod_controlables` → cite FR 136c |

**Score de confiance** affiché sur chaque réponse
**Sources traçables** : chaque affirmation liée à une preuve

---

## SLIDE 5 — Gains espérés

### ROI projeté

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| Temps diagnostic moyen | 45 min | **5 min** | **-89%** |
| Taux de résolution N2→N3 évitable | 0% | **~30%** | Décharge N3 |
| Capitalisation des résolutions | 0% | **100%** automatique | Mémoire collective |
| Onboarding nouvel expert | 3 mois | **3 semaines** | Accélération ×4 |
| Erreurs copier-coller SQL | Fréquent | **0** (lecture seule) | Risque éliminé |

### Chiffres de validation

- **20/20** scénarios GOLD passés (100% pass rate)
- **210 fiches FR** indexées et exploitables
- **279 incidents historiques** analysés et catégorisés
- **5 sources** corrélées en temps réel (BDD, logs, code, FR, graphe)

---

## SLIDE 6 — Vision & Roadmap

### Court terme (T3 2026)

- 🔌 **Intégration Jira bidirectionnelle** — création auto de tickets enrichis
- 📊 **Dashboard temps réel** — tendances incidents, alertes proactives
- 🧠 **Fine-tuning sur historique** — modèle spécialisé BRASIL

### Moyen terme (T4 2026)

- 🤖 **Mode autonome** — l'IA propose des corrections (avec validation humaine)
- 🌐 **Multi-applications** — extension à d'autres apps Orange (pas que BRASIL)
- 📱 **Bot Teams/Slack** — accès direct depuis les outils de l'équipe

### Long terme (2027)

- 🔮 **Prédiction d'incidents** — détection de patterns avant impact client
- 🏗️ **Auto-remédiation** — scripts de correction validés puis exécutés
- 📚 **Génération auto de documentation** — FR créées à partir des résolutions

---

## NOTES POUR LE PRÉSENTATEUR

**Timing suggéré :**
- Slide 1 : 30s (titre)
- Slide 2 : 2 min (problème, douleur actuelle)
- Slide 3 : 2 min (architecture, comment ça marche)
- Slide 4 : 3 min (démo live ou screenshots)
- Slide 5 : 1.5 min (chiffres, ROI)
- Slide 6 : 1 min (vision, next steps)

**Phrase d'accroche** :
> "Aujourd'hui un expert N3 passe 45 minutes à chercher dans 5 sources différentes avant de résoudre un incident. Notre agent IA fait ce travail en 30 secondes — avec les preuves."

**Question piège anticipée** :
- "Et si l'IA se trompe ?" → Validation Layer bloque les hallucinations + score de confiance visible + mode lecture seule
- "Ça remplace les experts ?" → Non, ça les augmente. L'IA cherche, l'humain décide.
- "C'est fiable en prod ?" → 20/20 scénarios validés, feature flags pour rollback instantané
