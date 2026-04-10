#!/bin/bash
# Git pull paytida .env ni saqlab qolish (maxfiy kalitlarni repoga yozmaydi).
set -e
cd /phonix/backend

echo "=== Stash .env → pull → pop ==="
git stash push -m "env-local" -- .env 2>/dev/null || true
git pull origin master || git pull origin main
git stash pop 2>/dev/null || true

echo ""
echo "Tekshiruv: CLICK_* va GEMINI kalitlari .env da Click panel bilan mosligini qo'lda tasdiqlang."
echo "Restart:"
sudo systemctl restart phoenix-backend
sleep 2
sudo systemctl is-active phoenix-backend && echo "phoenix-backend: active"
