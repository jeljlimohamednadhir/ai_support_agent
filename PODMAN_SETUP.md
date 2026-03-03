# Installation et Configuration Podman

## 🐳 Pourquoi Podman ?

- **Open source** et gratuit
- **Sans daemon** (plus sécurisé que Docker)
- **Compatible** avec les images et syntaxe Docker
- **Rootless** par défaut
- Pas de rate limit sur les téléchargements

## 📦 Installation sur WSL Ubuntu

```bash
# 1. Mettre à jour les paquets
sudo apt update && sudo apt upgrade -y

# 2. Installer Podman
sudo apt install -y podman

# 3. Installer podman-compose
sudo apt install -y python3-pip
pip3 install podman-compose

# 4. Vérifier l'installation
podman --version
podman-compose --version

# 5. Configurer Podman (optionnel)
mkdir -p ~/.config/containers
```

## ⚙️ Configuration Podman

Créer le fichier `~/.config/containers/registries.conf` :

```toml
[registries.search]
registries = ['docker.io', 'quay.io']

[registries.insecure]
registries = []

[registries.block]
registries = []
```

## 🚀 Lancer l'application

```bash
# Aller dans le dossier du projet
cd "/mnt/c/Users/n.jeljli/OneDrive - orange.com/Bureau/Genergy_IA/ai-support-agent"

# Lancer avec podman-compose (même syntaxe que docker-compose)
podman-compose up -d

# Voir les conteneurs en cours
podman ps

# Voir les logs
podman-compose logs -f

# Arrêter tous les services
podman-compose down
```

## 🔧 Commandes utiles Podman

```bash
# Lister les conteneurs
podman ps -a

# Lister les images
podman images

# Voir les logs d'un conteneur
podman logs <container-name>

# Entrer dans un conteneur
podman exec -it <container-name> bash

# Supprimer tous les conteneurs arrêtés
podman container prune

# Supprimer toutes les images non utilisées
podman image prune -a
```

## 🆚 Différences Docker vs Podman

| Commande Docker | Commande Podman | Notes |
|----------------|-----------------|-------|
| `docker` | `podman` | Syntaxe identique |
| `docker-compose` | `podman-compose` | Compatible à 95% |
| `docker ps` | `podman ps` | Même résultat |
| `sudo docker` | `podman` | Pas besoin de sudo |

## 🐛 Résolution de problèmes courants

### Problème : "permission denied"
```bash
# Ajouter l'utilisateur au groupe
sudo usermod -aG podman $USER
newgrp podman
```

### Problème : "network not found"
```bash
# Créer le réseau manuellement
podman network create ai-support-agent_default
```

### Problème : Ports déjà utilisés
```bash
# Vérifier les ports utilisés
sudo netstat -tulpn | grep LISTEN

# Arrêter le processus sur le port
sudo kill <PID>
```

## 📊 Services de l'application

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Interface React |
| Backend | 8000 | API FastAPI |
| PostgreSQL | 5432 | Base de données |
| Redis | 6379 | Cache & Queue |
| Neo4j | 7474, 7687 | Graphe de connaissances |
| Qdrant | 6333 | Base vectorielle |
| Flower | 5555 | Monitoring Celery |

## ✅ Vérification post-installation

```bash
# Tester Podman
podman run hello-world

# Vérifier que podman-compose fonctionne
podman-compose version

# Lancer l'application
cd "/mnt/c/Users/n.jeljli/OneDrive - orange.com/Bureau/Genergy_IA/ai-support-agent"
podman-compose up -d

# Vérifier que tous les services sont UP
podman ps
```

## 🌐 Accès aux services

Une fois lancé avec `podman-compose up -d` :

- **Frontend** : http://localhost:3000
- **Backend API** : http://localhost:8000
- **API Docs** : http://localhost:8000/docs
- **Neo4j Browser** : http://localhost:7474
- **Flower** : http://localhost:5555
- **Qdrant Dashboard** : http://localhost:6333/dashboard

## 🔄 Migration depuis Docker

Si vous aviez Docker installé :

```bash
# Arrêter les conteneurs Docker
docker-compose down

# Utiliser Podman avec la même syntaxe
podman-compose up -d

# Podman peut utiliser les images Docker existantes
podman images
```

## 💡 Conseils

1. **Alias pratique** : Ajoutez à `~/.bashrc` :
   ```bash
   alias docker='podman'
   alias docker-compose='podman-compose'
   ```

2. **Auto-démarrage** : Podman ne démarre pas automatiquement (pas de daemon)

3. **Performance** : Podman est généralement plus léger que Docker

4. **Compatibilité** : 99% des images Docker fonctionnent avec Podman

## 📚 Documentation officielle

- Podman : https://podman.io/
- podman-compose : https://github.com/containers/podman-compose
- Podman Desktop : https://podman-desktop.io/ (GUI alternative à Docker Desktop)
