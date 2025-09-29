# Déploiement Simple Todo Hôtel - LXC Proxmox avec Tailscale

Guide simplifié pour déployer l'application Todo Hôtel par copie du répertoire **todo-hotel-production** sur conteneur LXC Proxmox avec accès Tailscale.

## Prérequis

- Conteneur LXC Proxmox Debian 11/12 avec accès root
- Tailscale installé et configuré dans le conteneur
- 1GB RAM minimum, 2GB recommandé
- 1GB espace disque libre (répertoire production = 156K seulement)

## 1. Préparation du Conteneur LXC

```bash
# Mettre à jour le système
apt update && apt upgrade -y

# Installer les dépendances essentielles
apt install -y python3 python3-pip python3-venv sqlite3 cron curl
```

## 2. Copier l'Application

### Depuis votre machine locale :
```bash
# Copier UNIQUEMENT le répertoire de production vers le conteneur LXC via Tailscale
scp -r "/Users/axeldondin/Projet code/Todo-hotel/todo-hotel-production" root@IP-TAILSCALE-LXC:/tmp/
```

### Dans le conteneur LXC :
```bash
# Déplacer vers le répertoire final
mv /tmp/todo-hotel-production /root/todo-hotel

# Les répertoires nécessaires sont déjà créés dans le répertoire de production
ls -la /root/todo-hotel/
# Vous devriez voir: data/, logs/, backups/ déjà présents
```

## 3. Configuration Python

```bash
# Installation dans le conteneur LXC
cd /root/todo-hotel
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configuration de l'Application

```bash
# Créer le fichier de configuration
cat > /root/todo-hotel/.env << EOF
FLASK_APP=app:create_app
FLASK_ENV=production
DATABASE_URL=sqlite:////root/todo-hotel/data/todo_hotel.db
TZ=Europe/Paris
SECRET_KEY=$(openssl rand -base64 32)
GUNICORN_WORKERS=2
GUNICORN_TIMEOUT=30
EOF
```

## 5. Initialisation de la Base de Données

```bash
# Initialiser la base de données
cd /root/todo-hotel
source venv/bin/activate
export FLASK_APP=app:create_app
flask db upgrade

# Vérifier que tout fonctionne
python -c 'from app import create_app; app=create_app(); print("✓ Application OK")'
```

## 6. Configuration du Service Systemd

Le fichier service fourni contient des erreurs de chemins. Nous devons le corriger :

```bash
# Corriger le fichier service avec les bons chemins
cat > /root/todo-hotel/todo-hotel.service << 'EOF'
[Unit]
Description=Todo Hotel Application
Documentation=file:///root/todo-hotel/DEPLOIEMENT_SIMPLE.md
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root/todo-hotel
Environment=PATH=/root/todo-hotel/venv/bin
Environment=FLASK_APP=app:create_app
Environment=FLASK_ENV=production
ExecStart=/root/todo-hotel/venv/bin/gunicorn -w 3 -b 0.0.0.0:8080 wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=10
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
EnvironmentFile=-/root/todo-hotel/.env

[Install]
WantedBy=multi-user.target
EOF

# Copier le fichier service corrigé
cp /root/todo-hotel/todo-hotel.service /etc/systemd/system/

# Recharger la configuration systemd
systemctl daemon-reload

# Activer le service pour démarrage automatique
systemctl enable todo-hotel

# Démarrer le service
systemctl start todo-hotel

# Vérifier que le service démarre correctement
sleep 3
systemctl status todo-hotel
```

## 7. Configuration des Tâches Récurrentes

```bash
# Configurer le cron pour root
(crontab -l 2>/dev/null; echo '# Génération des tâches récurrentes tous les vendredis à 6h00') | crontab -
(crontab -l 2>/dev/null; echo '0 6 * * 5 cd /root/todo-hotel && /root/todo-hotel/venv/bin/python generate_weekly_tasks.py >> /root/todo-hotel/logs/cron.log 2>&1') | crontab -
(crontab -l 2>/dev/null; echo '# Sauvegarde hebdomadaire de la base de données') | crontab -
(crontab -l 2>/dev/null; echo '0 2 * * 0 cp /root/todo-hotel/data/todo_hotel.db /root/todo-hotel/backups/backup_$(date +%Y%m%d_%H%M%S).db') | crontab -
```

## 8. Accès via Tailscale

L'application sera accessible sur :
- **http://IP-TAILSCALE-LXC:8080** 
- Exemple : `http://100.64.x.x:8080`
- Accès sécurisé uniquement depuis votre réseau Tailscale
- **Pas besoin de nginx ni de firewall** avec Tailscale dans LXC

## Vérification du Déploiement

```bash
# Vérifier le statut du service
systemctl status todo-hotel

# Vérifier les logs
journalctl -u todo-hotel -f

# Tester l'application localement
curl http://localhost:8080/healthz

# Vérifier les tâches cron
crontab -l
```

## Tests depuis un autre appareil Tailscale

```bash
# Remplacez IP-TAILSCALE-LXC par l'IP réelle du conteneur
curl http://IP-TAILSCALE-LXC:8080/healthz
curl http://IP-TAILSCALE-LXC:8080/

# Créer une tâche test via API
curl -X POST http://IP-TAILSCALE-LXC:8080/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title": "Test task", "due_date": "2025-08-30", "is_recurring": false}'
```

## Maintenance Courante

### Logs de l'Application
```bash
# Logs du service systemd (recommandé)
journalctl -u todo-hotel -f

# Logs du service (dernières 50 lignes)
journalctl -u todo-hotel -n 50

# Logs des tâches récurrentes (si le fichier existe)
tail -f /root/todo-hotel/logs/cron.log

# En cas de problème, vérifier les erreurs Python
journalctl -u todo-hotel --since "1 hour ago" | grep -i error
```

### Sauvegarde Manuelle
```bash
# Sauvegarde de la base de données
cp /root/todo-hotel/data/todo_hotel.db /root/todo-hotel/backups/backup_$(date +%Y%m%d_%H%M%S).db

# Voir les sauvegardes
ls -la /root/todo-hotel/backups/
```

### Redémarrage de l'Application
```bash
# Redémarrer le service
systemctl restart todo-hotel

# Vérifier le statut
systemctl status todo-hotel
```

## Mise à Jour Future

Pour mettre à jour l'application :

```bash
# Arrêter le service
systemctl stop todo-hotel

# Sauvegarder la base de données
cp /root/todo-hotel/data/todo_hotel.db /root/todo-hotel/backups/backup_avant_maj_$(date +%Y%m%d_%H%M%S).db

# Copier la nouvelle version du répertoire de production (en gardant les fichiers de config)
# scp -r "todo-hotel-production" root@IP-TAILSCALE-LXC:/tmp/
# rsync -av --exclude='.env' --exclude='data/' --exclude='logs/' --exclude='backups/' /tmp/todo-hotel-production/ /root/todo-hotel/

# Mettre à jour les dépendances si nécessaire
cd /root/todo-hotel
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade

# Redémarrer
systemctl start todo-hotel
systemctl status todo-hotel
```

## Architecture Simplifiée LXC

```
Réseau Tailscale
       ↓
LXC Container (IP Tailscale:8080)
       ↓
 Gunicorn (8080) - Root User
       ↓
   Flask App
       ↓
SQLite DB (/opt/todo-hotel/data/)
```

**Avantages LXC + Tailscale + Root :**
- ✅ **Déploiement ultra-léger** : seulement 156K pour le répertoire production
- ✅ **Conteneurisation légère** avec LXC Proxmox
- ✅ **Accès sécurisé** via Tailscale sans firewall
- ✅ **Simplicité maximale** avec utilisateur root (pas de gestion de permissions)
- ✅ **Isolation** du service dans le conteneur LXC
- ✅ **Sauvegarde/snapshot** facile via Proxmox
- ✅ **Accès universel** depuis tous vos appareils Tailscale

## Notes Spécifiques LXC Proxmox

- **Sauvegarde** : Le conteneur peut être facilement sauvegardé via Proxmox
- **Snapshots** : Possibilité de faire des snapshots avant mise à jour
- **Ressources** : CPU/RAM ajustables à chaud
- **Réseau** : Tailscale fonctionne parfaitement dans LXC
- **Taille** : Application très légère (156K) parfaite pour LXC

## Résumé Rapide du Déploiement

1. **Copier** le répertoire `todo-hotel-production` (156K)
2. **Installer** les dépendances Python dans un venv
3. **Configurer** le fichier `.env` avec une clé secrète
4. **Initialiser** la base de données SQLite
5. **Activer** le service systemd
6. **Accéder** via Tailscale sur le port 8080

🎉 **L'application Todo Hôtel est maintenant déployée sur votre conteneur LXC Proxmox avec Tailscale !**