#!/bin/bash
# PHONIX Platform - Admin va Editor Users Yaratish Script
# Linux / Mac uchun
# Ishlatish: bash create_users.sh

echo "========================================================================"
echo "   🚀 PHONIX PLATFORM - ADMIN VA EDITOR USERS YARATISH"
echo "========================================================================"
echo ""

# Check if in backend directory
if [ ! -f "manage.py" ]; then
    echo "❌ ERROR: manage.py topilmadi. Backend directory'sida bo'ish kerak."
    echo "   cd backend && bash create_users.sh"
    exit 1
fi

# Check if Python virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  WARNING: Virtual environment faol emas!"
    echo "   Ilk o'rnatish uchun venv'ni activation qiling:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate  # Mac/Linux"
    echo "   venv\\Scripts\\activate     # Windows"
    echo ""
fi

echo "📦 Django dependencies tekshirilmoqda..."

# Check if Django is installed
python -c "import django" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Django o'rnatilmagan"
    echo "   pip install -r requirements.txt"
    exit 1
fi

echo "✅ Django o'rnatilgan"
echo ""

# Run migrations
echo "🔄 Database migrations qo'llanmoqda..."
python manage.py migrate --noinput

if [ $? -ne 0 ]; then
    echo "❌ Migrations xatolik"
    exit 1
fi

echo "✅ Migrations tugallandi"
echo ""

# Create test users
echo "👥 Test users yaratilmoqda..."
python create_admin_editor_users.py

if [ $? -ne 0 ]; then
    echo "❌ Users yaratishda xatolik"
    exit 1
fi

echo ""
echo "========================================================================"
echo "✨ ADMIN VA EDITOR USERS MUVAFFAQIYATLI YARATILDI!"
echo "========================================================================"
echo ""
echo "🌐 FRONTEND LOGIN: https://ilmiyfaoliyat.uz/#/login"
echo "🔐 ADMIN PANEL: http://localhost:8000/admin/"
echo ""
echo "📧 Yuqorida ko'rsatilgan credentials'lardan foydalaning"
echo ""
