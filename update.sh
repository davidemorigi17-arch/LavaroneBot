#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "==> Controllo aggiornamenti su GitHub..."
git fetch origin main

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "==> Nessun aggiornamento disponibile."
    exit 0
fi

echo "==> Nuovi aggiornamenti trovati! Aggiorno..."
git pull origin main

echo "==> Rebuild e riavvio del container..."
docker compose up -d --build

echo "==> Fatto. Container aggiornato e attivo."
docker compose ps
