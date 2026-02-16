#!/bin/bash
# Check and create Django admin superuser

cd /phonix/backend
source venv/bin/activate

echo "=== Django Admin Superuser Tekshirish ==="
echo ""

python manage.py shell << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.users.models import User

# Superuser'larni tekshirish
superusers = User.objects.filter(is_superuser=True, is_staff=True, is_active=True)
print(f"Jami superuser'lar: {superusers.count()}")
print("")

if superusers.exists():
    print("Superuser'lar ro'yxati:")
    for user in superusers:
        print(f"  - Phone: {user.phone}")
        print(f"    Email: {user.email}")
        print(f"    Name: {user.first_name} {user.last_name}")
        print(f"    Active: {user.is_active}, Staff: {user.is_staff}, Superuser: {user.is_superuser}")
        print("")
else:
    print("❌ Superuser topilmadi!")
    print("")
    print("Superuser yaratish kerak.")
EOF

echo ""
echo "=== Superuser yaratish ==="
echo ""
echo "Telefon raqam: +998910574905"
echo "Parol: (environment variable'dan olinadi yoki 'changeme123!' default)"
echo ""

# Superuser yaratish yoki parolni o'zgartirish
python manage.py shell << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.users.models import User

admin_phone = '+998910574905'
admin_password = os.environ.get('ADMIN_PASSWORD', 'changeme123!')

# Superuser'ni topish yoki yaratish
user, created = User.objects.get_or_create(
    phone=admin_phone,
    defaults={
        'email': 'admin@ilmiyfaoliyat.uz',
        'first_name': 'Admin',
        'last_name': 'User',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'role': 'super_admin'
    }
)

if created:
    user.set_password(admin_password)
    user.save()
    print(f"✅ Superuser yaratildi!")
    print(f"   Phone: {admin_phone}")
    print(f"   Password: {admin_password}")
else:
    # Parolni o'zgartirish
    user.set_password(admin_password)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.save()
    print(f"✅ Superuser paroli yangilandi!")
    print(f"   Phone: {admin_phone}")
    print(f"   Password: {admin_password}")

print("")
print("Admin panel'ga kirish:")
print(f"  URL: https://api.ilmiyfaoliyat.uz/admin/")
print(f"  Phone: {admin_phone}")
print(f"  Password: {admin_password}")
EOF

echo ""
echo "✅ Tekshirish yakunlandi!"
