#!/bin/bash
# Fix .env git pull issue and update Click keys

cd /phonix/backend

echo "=== Git Pull va Click Keys Yangilash ==="
echo ""

# 1. .env o'zgarishlarini stash qilish
echo "1. .env o'zgarishlarini stash qilish..."
git stash

# 2. Git pull
echo ""
echo "2. Git'dan yangilanishlarni olish..."
git pull origin master

# 3. Stash'dan o'zgarishlarni qaytarish
echo ""
echo "3. Stash'dan o'zgarishlarni qaytarish..."
git stash pop 2>/dev/null || true

# 4. Service 89248 kalitini to'g'rilash
echo ""
echo "4. Service 89248 kalitini to'g'rilash..."
sed -i 's/CLICK_SERVICE_89248_SECRET_KEY=08ClKUoBemAxyM/CLICK_SERVICE_89248_SECRET_KEY=08CIKUoBemAxyM/g' .env
sed -i 's/CLICK_SECRET_KEY=08ClKUoBemAxyM/CLICK_SECRET_KEY=08CIKUoBemAxyM/g' .env

# 5. Service 88045 kalitini qo'shish (agar yo'q bo'lsa)
if ! grep -q "CLICK_SERVICE_88045_SECRET_KEY" .env; then
    echo ""
    echo "5. Service 88045 kalitini qo'shish..."
    echo "" >> .env
    echo "# Service 88045 uchun (PHOENIX - yangi)" >> .env
    echo "CLICK_SERVICE_88045_SECRET_KEY=EcyUxjPNLqxxZo" >> .env
fi

# 6. Yangilangan kalitlarni tekshirish
echo ""
echo "6. Yangilangan kalitlarni tekshirish..."
grep "CLICK.*SECRET_KEY" .env | grep -v "^#"

# 7. Backend'ni restart qilish
echo ""
echo "7. Backend'ni restart qilish..."
sudo systemctl restart phoenix-backend

echo ""
echo "✅ Barcha o'zgarishlar qo'llandi!"
