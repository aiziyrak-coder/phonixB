#!/bin/bash
# Check Click secret keys match with merchant panel

cd /phonix/backend
source venv/bin/activate

echo "=== Click Secret Keys Tekshirish ==="
echo ""

python manage.py shell << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings

print("Backend'dagi Click Secret Keys:")
print("=" * 80)

# Service 82154
key_82154 = getattr(settings, 'CLICK_SERVICE_82154_SECRET_KEY', 'NOT SET')
print(f"Service 82154 (Ilmiyfaoliyat.uz):")
print(f"  Backend: {key_82154}")
print(f"  Merchant Panel: XZC6u3JBBh")
print(f"  Match: {'✅ TO\'G\'RI' if key_82154 == 'XZC6u3JBBh' else '❌ NOTO\'G\'RI'}")
print("")

# Service 82155
key_82155 = getattr(settings, 'CLICK_SERVICE_82155_SECRET_KEY', 'NOT SET')
print(f"Service 82155 (Phoenix publication):")
print(f"  Backend: {key_82155}")
print(f"  Merchant Panel: icHbYQnMBx")
print(f"  Match: {'✅ TO\'G\'RI' if key_82155 == 'icHbYQnMBx' else '❌ NOTO\'G\'RI'}")
print("")

# Service 89248
key_89248 = getattr(settings, 'CLICK_SERVICE_89248_SECRET_KEY', 'NOT SET')
print(f"Service 89248 (PHOENIX):")
print(f"  Backend: {key_89248}")
print(f"  Merchant Panel: 08CIKUoBemAxyM")
print(f"  Match: {'✅ TO\'G\'RI' if key_89248 == '08CIKUoBemAxyM' else '❌ NOTO\'G\'RI'}")
if key_89248 != '08CIKUoBemAxyM':
    print(f"  ⚠️  Farq: Backend'da '{key_89248}', Merchant Panel'da '08CIKUoBemAxyM'")
print("")

# Service 88045 (yangi)
print(f"Service 88045 (PHOENIX - yangi):")
print(f"  Backend: NOT SET (yo'q)")
print(f"  Merchant Panel: EcyUxjPNLqxxZo")
print(f"  ⚠️  Bu service backend'da sozlanmagan")
print("")

print("=" * 80)
print("Xulosa:")
print("  - Service 82154: " + ('✅ TO\'G\'RI' if key_82154 == 'XZC6u3JBBh' else '❌ NOTO\'G\'RI'))
print("  - Service 82155: " + ('✅ TO\'G\'RI' if key_82155 == 'icHbYQnMBx' else '❌ NOTO\'G\'RI'))
print("  - Service 89248: " + ('✅ TO\'G\'RI' if key_89248 == '08CIKUoBemAxyM' else '❌ NOTO\'G\'RI (to\'g\'rilash kerak)'))
print("  - Service 88045: ⚠️  Backend'da yo'q (qo\'shish kerak)")
EOF

echo ""
echo "✅ Tekshirish yakunlandi!"
