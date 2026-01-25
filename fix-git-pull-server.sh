#!/bin/bash
# Git Pull Muammosini Tuzatish - Server'da ishlatish uchun

set -e

echo "🔧 Git pull muammosini tuzatish..."
echo ""

cd /phonix/backend

# 1. Local o'zgarishlarni stash qilish
echo "  → Local o'zgarishlarni stash qilish..."
git stash

# 2. Git pull
echo "  → Git pull qilish..."
git pull origin master

# 3. Stash'dan o'zgarishlarni qaytarish (agar kerak bo'lsa)
echo "  → Stash'dan o'zgarishlarni qaytarish..."
if git stash list | grep -q "stash@{0}"; then
    git stash pop || echo "  ⚠️  Stash pop xatolik (ehtimol conflict)"
fi

# 4. Service restart
echo ""
echo "  → Backend service'ni restart qilish..."
sudo systemctl restart phoenix-backend
sleep 3

# 5. Status tekshirish
echo ""
echo "  → Service status tekshirish..."
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "  ✅ Backend service ishlayapti"
    sudo systemctl status phoenix-backend --no-pager | head -10
else
    echo "  ❌ Backend service ishlamayapti!"
    sudo journalctl -u phoenix-backend --no-pager -n 20 | tail -15
    exit 1
fi

echo ""
echo "✅ Git pull muammosi tuzatildi!"
