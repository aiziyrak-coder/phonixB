#!/bin/bash
# Create Django superadmin with specified phone and password

cd /phonix/backend
source venv/bin/activate

echo "=== Django Superadmin Yaratish ==="
echo ""

python manage.py shell << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.users.models import User

admin_phone = '+998939858406'
admin_password = '8406'

# Telefon raqamni tozalash (bo'shliqlarni olib tashlash)
admin_phone_clean = admin_phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

print(f"Telefon raqam: {admin_phone_clean}")
print(f"Parol: {admin_password}")
print("")

# Eski superuser'ni topish va o'chirish (agar mavjud bo'lsa)
old_user = User.objects.filter(phone=admin_phone_clean).first()
if old_user:
    print(f"Eski foydalanuvchi topildi: {old_user.phone}")
    old_user.delete()
    print("Eski foydalanuvchi o'chirildi.")
    print("")

# Yangi superuser yaratish
try:
    user = User.objects.create_superuser(
        phone=admin_phone_clean,
        email='admin@ilmiyfaoliyat.uz',
        first_name='Admin',
        last_name='User',
        password=admin_password,
        is_active=True,
        is_staff=True,
        is_superuser=True,
        role='super_admin'
    )
    print("✅ Superadmin muvaffaqiyatli yaratildi!")
    print("")
    print("Admin panel'ga kirish ma'lumotlari:")
    print(f"  URL: https://api.ilmiyfaoliyat.uz/admin/")
    print(f"  Telefon raqam: {admin_phone_clean}")
    print(f"  Parol: {admin_password}")
    print("")
except Exception as e:
    print(f"❌ Xatolik: {e}")
    print("")
    # Agar create_superuser ishlamasa, manual yaratish
    try:
        user = User.objects.create(
            phone=admin_phone_clean,
            email='admin@ilmiyfaoliyat.uz',
            first_name='Admin',
            last_name='User',
            is_active=True,
            is_staff=True,
            is_superuser=True,
            role='super_admin'
        )
        user.set_password(admin_password)
        user.save()
        print("✅ Superadmin manual yaratildi!")
        print("")
        print("Admin panel'ga kirish ma'lumotlari:")
        print(f"  URL: https://api.ilmiyfaoliyat.uz/admin/")
        print(f"  Telefon raqam: {admin_phone_clean}")
        print(f"  Parol: {admin_password}")
    except Exception as e2:
        print(f"❌ Xatolik (manual): {e2}")
EOF

echo ""
echo "✅ Script yakunlandi!"
