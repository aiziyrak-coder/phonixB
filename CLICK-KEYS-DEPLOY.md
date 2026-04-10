# 🚀 Click Service Keys - Server'da Deploy Qilish

## ✅ CLICK'DAN BERILGAN KALITLAR

### **Service 82154 (Ilmiyfaoliyat.uz):**
- SECRET_KEY: `<CLICK_82154_SECRET>`
- MERCHANT_USER_ID: `63536`

### **Service 82155 (Phoenix publication):**
- SECRET_KEY: `<CLICK_82155_SECRET>`
- MERCHANT_USER_ID: `64985`

---

## ⚡ BITTA BUYRUQ BILAN DEPLOY

### **Server'da:**

```bash
cd /phonix/backend

# Log fayl o'zgarishlarini bekor qilish
git checkout -- logs/django.log

# Git pull
git pull origin master

# Avtomatik script bilan kalitlarni qo'shish
chmod +x SET-CLICK-KEYS.sh
./SET-CLICK-KEYS.sh
```

**Hammasi!** Script avtomatik:
- ✅ .env fayliga ikkala service uchun ham kalitlarni qo'shadi
- ✅ Backend'ni restart qiladi
- ✅ Test qiladi

---

## 📋 YOKI QO'LDA (Nano Orqali)

```bash
cd /phonix/backend

# Log fayl o'zgarishlarini bekor qilish
git checkout -- logs/django.log

# Git pull
git pull origin master

# .env faylini tahrirlash
nano .env
```

**Faylning oxiriga qo'shing:**

```env
# Click Service-specific secret keys (Click'dan berilgan kalitlar)
# Service 82154 uchun (Ilmiyfaoliyat.uz)
CLICK_SERVICE_82154_SECRET_KEY=<CLICK_82154_SECRET>
CLICK_SERVICE_82154_MERCHANT_USER_ID=63536
# Service 82155 uchun (Phoenix publication)
CLICK_SERVICE_82155_SECRET_KEY=<CLICK_82155_SECRET>
CLICK_SERVICE_82155_MERCHANT_USER_ID=64985
```

**Saqlash:** `Ctrl+O`, `Enter`, `Ctrl+X`

**Migration va restart:**

```bash
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate
deactivate
sudo systemctl restart phoenix-backend
sudo systemctl status phoenix-backend
```

---

## 🧪 TEST QILISH

```bash
cd /phonix/backend
source venv/bin/activate
python << 'EOF'
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/phonix/backend')
django.setup()

from apps.payments.services import ClickPaymentService

service = ClickPaymentService()

print("=" * 80)
print("CLICK SERVICE SECRET KEYS:")
print("=" * 80)
print(f"Service 82154 (Ilmiyfaoliyat.uz): {service.get_secret_key_for_service('82154')[:15]}...")
print(f"Service 82155 (Phoenix publication): {service.get_secret_key_for_service('82155')[:15]}...")
print(f"Service 89248 (PHOENIX): {service.get_secret_key_for_service('89248')[:15]}...")
print("=" * 80)
EOF
deactivate
```

**Ko'rinishi kerak:**
```
Service 82154 (Ilmiyfaoliyat.uz): <CLICK_82154_SECRET>...
Service 82155 (Phoenix publication): <CLICK_82155_SECRET>...
Service 89248 (PHOENIX): <REDACTED_CLICK_SECRET>...
```

---

## ✅ NATIJA

Endi backend **3 ta service** uchun ham kalitlarni biladi:

- ✅ **Service 82154** (Ilmiyfaoliyat.uz) → `<CLICK_82154_SECRET>`
- ✅ **Service 82155** (Phoenix publication) → `<CLICK_82155_SECRET>`
- ✅ **Service 89248** (PHOENIX) → `<REDACTED_CLICK_SECRET>`

**Click'dan qaysi service_id bilan callback kelsa ham, to'g'ri secret key ishlatiladi!**

---

## 🎯 XULOSA

**Hammasi tayyor!** Faqat server'da scriptni ishga tushiring yoki .env faylini yangilang.

**"Invalid signature" muammosi endi hal bo'ladi!** 🚀
