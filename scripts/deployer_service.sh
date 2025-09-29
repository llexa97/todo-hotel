#!/usr/bin/env bash
set -euo pipefail

# Script deploiement service Todo Hotel dans systemd.
# Il deplace le fichier todo-hotel.service vers /etc/systemd/system/,
# sauvegarde l ancienne version et recharge systemd.

SERVICE_NAME="todo-hotel.service"
SYSTEMD_DIR="/etc/systemd/system"

# Localise le repertoire du script puis la racine du depot.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_FILE="${REPO_ROOT}/${SERVICE_NAME}"
TARGET_FILE="${SYSTEMD_DIR}/${SERVICE_NAME}"

# Si on n est pas root, relance le script avec sudo pour avoir les droits.
if [[ $EUID -ne 0 ]]; then
  exec sudo "$0" "$@"
fi

# Verifie que le fichier service existe dans le repo avant de continuer.
if [[ ! -f "$SOURCE_FILE" ]]; then
  echo "Fichier introuvable : ${SOURCE_FILE}" >&2
  exit 1
fi

# Sauvegarde l ancienne version du service s il est deja en place.
if [[ -f "$TARGET_FILE" ]]; then
  BACKUP="${TARGET_FILE}.$(date +%Y%m%d_%H%M%S).bak"
  echo "Sauvegarde du service existant dans ${BACKUP}"
  mv "$TARGET_FILE" "$BACKUP"
fi

# Deplace le fichier du repo vers le dossier systemd.
echo "Deplacement de ${SOURCE_FILE} -> ${TARGET_FILE}";
mv "$SOURCE_FILE" "$TARGET_FILE"

# Recharge systemd pour prendre en compte le nouveau fichier.
systemctl daemon-reload

# Active et demarre immediatement le service (si pas deja actif).
systemctl enable --now "${SERVICE_NAME%.service}"

# Affiche l etat actuel du service pour verification rapide.
systemctl status --no-pager "${SERVICE_NAME%.service}"
