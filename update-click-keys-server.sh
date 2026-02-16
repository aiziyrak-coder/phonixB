#!/bin/bash
# Update Click secret keys on server

cd /phonix/backend

echo "=== Click Secret Keys Yangilash ==="
echo ""

# Service 89248 kalitini to'g'rilash
echo "1. Service 89248 kalitini yangilash..."
sed -i 's/CLICK_SERVICE_89248_SECRET_KEY=08ClKUoBemAxyM/CLICK_SERVICE_89248_SECRET_KEY=08CIKUoBemAxyM/g' .env
sed -i 's/CLICK_SECRET_KEY=08ClKUoBemAxyM/CLICK_SECRET_KEY=08CIKUoBemAxyM/g' .env

echo "2. Yangilangan kalitlarni tekshirish..."
grep "CLICK.*SECRET_KEY" .env | grep -v "^#"

echo ""
echo "3. Backend'ni restart qilish..."
sudo systemctl restart phoenix-backend

echo ""
echo "✅ Kalitlar yangilandi va backend restart qilindi!"
