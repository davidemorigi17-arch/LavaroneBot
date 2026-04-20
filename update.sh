#!/bin/bash
set -e

echo "==> Pull ultime modifiche da GitHub..."
git pull origin main

echo "==> Rebuild e riavvio del container..."
docker compose up -d --build

echo "==> Fatto. Container aggiornato e attivo."
docker compose ps
