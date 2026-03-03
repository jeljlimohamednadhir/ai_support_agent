# 🐋 Guide Podman - AI Support Agent

## Installation de Podman sur Windows

### Option 1: Podman Desktop (Recommandé)
1. Téléchargez: https://podman-desktop.io/downloads
2. Installez l'application
3. Lancez Podman Desktop
4. Vérifiez: `podman --version`

### Option 2: Podman CLI uniquement
```powershell
# Avec winget
winget install RedHat.Podman

# Ou téléchargement manuel
# https://github.com/containers/podman/releases
```

### Installation de podman-compose
```powershell
pip install podman-compose
```

---

## 🚀 Démarrage Rapide

### Méthode 1: Avec le script PowerShell (Le plus simple)

```powershell
# Démarrer tous les services en arrière-plan
.\podman.ps1 up -Detached

# Voir l'état des conteneurs
.\podman.ps1 ps

# Voir les logs d'un service
.\podman.ps1 logs postgres

# Arrêter tout
.\podman.ps1 down
```

### Méthode 2: Avec podman-compose

```powershell
# Démarrer tous les services
podman-compose up -d

# Voir les logs
podman-compose logs -f

# Arrêter
podman-compose down

# Redémarrer un service
podman-compose restart backend
```

### Méthode 3: Podman directement

```powershell
# Créer le réseau
podman network create ai-support-network

# PostgreSQL
podman run -d `
  --name ai-support-postgres `
  --network ai-support-network `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres_secure_2024 `
  -e POSTGRES_DB=ai_support_agent `
  -p 5432:5432 `
  -v ai-support-postgres-data:/var/lib/postgresql/data `
  docker.io/library/postgres:15-alpine

# Redis
podman run -d `
  --name ai-support-redis `
  --network ai-support-network `
  -p 6379:6379 `
  -v ai-support-redis-data:/data `
  docker.io/library/redis:7-alpine

# Neo4j
podman run -d `
  --name ai-support-neo4j `
  --network ai-support-network `
  -e NEO4J_AUTH=neo4j/neo4j_secure_2024 `
  -p 7474:7474 `
  -p 7687:7687 `
  -v ai-support-neo4j-data:/data `
  docker.io/library/neo4j:5-community

# Qdrant
podman run -d `
  --name ai-support-qdrant `
  --network ai-support-network `
  -p 6333:6333 `
  -v ai-support-qdrant-data:/qdrant/storage `
  docker.io/qdrant/qdrant:latest
```

---

## 📊 Vérification des Services

### URLs d'accès

| Service | URL | Credentials |
|---------|-----|-------------|
| **Backend API** | http://localhost:8000 | - |
| **API Docs** | http://localhost:8000/docs | - |
| **Neo4j Browser** | http://localhost:7474 | neo4j / neo4j_secure_2024 |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | - |
| **PostgreSQL** | localhost:5432 | postgres / postgres_secure_2024 |
| **Redis** | localhost:6379 | - |

### Commandes de vérification

```powershell
# Lister les conteneurs
podman ps

# Vérifier les logs
podman logs ai-support-postgres
podman logs ai-support-redis
podman logs ai-support-neo4j
podman logs ai-support-qdrant

# Inspecter un conteneur
podman inspect ai-support-postgres

# Entrer dans un conteneur
podman exec -it ai-support-postgres psql -U postgres -d ai_support_agent

# Vérifier les volumes
podman volume ls

# Vérifier le réseau
podman network ls
```

---

## 🔧 Commandes Utiles

### Gestion des conteneurs

```powershell
# Démarrer un conteneur spécifique
podman start ai-support-postgres

# Arrêter un conteneur
podman stop ai-support-postgres

# Redémarrer
podman restart ai-support-postgres

# Supprimer (après stop)
podman rm ai-support-postgres

# Voir les stats en temps réel
podman stats
```

### Gestion des volumes

```powershell
# Lister les volumes
podman volume ls

# Inspecter un volume
podman volume inspect ai-support-postgres-data

# Nettoyer les volumes non utilisés
podman volume prune

# Supprimer un volume spécifique
podman volume rm ai-support-postgres-data
```

### Gestion des images

```powershell
# Lister les images
podman images

# Télécharger une image
podman pull docker.io/library/postgres:15-alpine

# Supprimer une image
podman rmi postgres:15-alpine

# Nettoyer les images non utilisées
podman image prune -a
```

---

## 🐛 Dépannage

### Problème: Les conteneurs ne démarrent pas

```powershell
# Vérifier les logs
podman logs ai-support-postgres --tail 50

# Vérifier l'état
podman ps -a

# Redémarrer la machine Podman (si nécessaire)
podman machine stop
podman machine start
```

### Problème: Port déjà utilisé

```powershell
# Trouver le processus utilisant le port
netstat -ano | findstr :5432

# Arrêter tous les conteneurs
podman stop $(podman ps -aq)

# Relancer avec d'autres ports
podman run -d -p 5433:5432 ...
```

### Problème: Erreur de réseau

```powershell
# Recréer le réseau
podman network rm ai-support-network
podman network create ai-support-network

# Vérifier la connectivité
podman network inspect ai-support-network
```

### Problème: Volumes corrompus

```powershell
# ATTENTION: Cela supprimera toutes les données!
podman volume rm ai-support-postgres-data
podman volume create ai-support-postgres-data
```

---

## 🔄 Migration depuis Docker

Si vous avez déjà des conteneurs Docker:

```powershell
# 1. Exporter les données de Docker
docker exec ai-support-postgres pg_dump -U postgres ai_support_agent > backup.sql

# 2. Arrêter Docker
docker-compose down

# 3. Démarrer Podman
.\podman.ps1 up -Detached

# 4. Restaurer les données
podman exec -i ai-support-postgres psql -U postgres -d ai_support_agent < backup.sql
```

---

## 💡 Astuces

### Alias PowerShell

Ajoutez à votre profil PowerShell (`notepad $PROFILE`):

```powershell
# Alias pour Podman
Set-Alias p podman
Set-Alias pc podman-compose

# Fonctions raccourcies
function pup { .\podman.ps1 up -Detached }
function pdown { .\podman.ps1 down }
function pps { podman ps }
function plogs { param($service) podman logs -f "ai-support-$service" }
```

### Auto-démarrage

Pour démarrer automatiquement les conteneurs au boot:

```powershell
# Créer une tâche planifiée
$trigger = New-ScheduledTaskTrigger -AtStartup
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\path\to\ai-support-agent\podman.ps1 up -Detached"
Register-ScheduledTask -TaskName "AI Support Agent" -Trigger $trigger -Action $action -RunLevel Highest
```

---

## 📚 Ressources

- **Documentation Podman**: https://docs.podman.io/
- **Podman Desktop**: https://podman-desktop.io/
- **podman-compose**: https://github.com/containers/podman-compose
- **Migration Docker→Podman**: https://podman.io/getting-started/migration

---

## ✅ Checklist de démarrage

- [ ] Podman installé (`podman --version`)
- [ ] podman-compose installé (`podman-compose --version`)
- [ ] Script `podman.ps1` exécutable
- [ ] Fichier `.env` configuré dans `backend/`
- [ ] Services démarrés (`.\podman.ps1 up -Detached`)
- [ ] Services accessibles (vérifier les URLs ci-dessus)
- [ ] Backend lancé (`cd backend; python -m uvicorn app.main:app --reload`)

**Prêt à développer ! 🚀**
