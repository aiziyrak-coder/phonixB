# 🚀 Server'da Payme To'lovni Deploy Qilish - Oson Yo'riqnoma

## ⚡ 3 QADAM - 10 DAQIQA

---

## 📋 QADAM 1: Payme Merchant Account (5 daqiqa)

### 1. Payme Business'ga kiring
- URL: https://business.payme.uz
- Login yoki ro'yxatdan o'ting

### 2. Credentials Oling
Quyidagi 3 ta ma'lumotni yozib oling:
- **Merchant ID** (masalan: `12345`)
- **Production Key** (masalan: `ABCDEF123456...`)
- **Test Key** (masalan: `TESTKEY123...`)

**Screenshot oling yoki yozib qo'ying!**

---

## 📋 QADAM 2: Server'da Deploy (3 daqiqa)

### 1. Server'ga Kirish

```bash
ssh root@your-server-ip
```

### 2. Payme Credentials Kiritish

```bash
cd /phonix/backend
nano .env
```

**Fayldagi eng oxiriga qo'shing:**

```env
# Payme Payment (Sizning ma'lumotlaringizni kiriting!)
PAYME_MERCHANT_ID=12345
PAYME_MERCHANT_KEY=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456
PAYME_TEST_KEY=TESTKEY123456789
PAYME_IS_TEST=True
PAYME_ENDPOINT=https://checkout.paycom.uz
```

**⚠️ MUHIM:** `12345`, `ABCDEF...` va `TESTKEY...` o'rniga **o'zingizning** Payme'dan olgan ma'lumotlaringizni kiriting!

**Saqlash:**
- `Ctrl + O` (Save)
- `Enter` (Tasdiqlash)
- `Ctrl + X` (Chiqish)

### 3. Deploy Qilish

```bash
cd /phonix/backend
git pull origin master
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate
deactivate
sudo systemctl restart phoenix-backend
```

**Tayyor!** Backend yangilandi! ✅

---

## 📋 QADAM 3: Payme Merchant Panel Sozlash (2 daqiqa)

### 1. Payme Business'ga Kiring
- URL: https://business.payme.uz

### 2. Service Sozlash
1. **Сервисы** (Services) bo'limiga o'ting
2. Service yarating yoki tahrirlang
3. **Endpoint URL** ga kiriting:
   ```
   https://api.ilmiyfaoliyat.uz/api/v1/payments/payme/
   ```
4. **HTTP Method:** POST
5. **Protocol:** JSON-RPC 2.0
6. **Saqlang**

---

## ✅ TEST QILISH

### Backend Test (Server'da)

```bash
cd /phonix/backend
source venv/bin/activate
python << 'EOF'
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/phonix/backend')
django.setup()

from apps.payments.payme_service import PaymeService

service = PaymeService()
print("=" * 60)
print("PAYME SERVICE:")
print("=" * 60)
print(f"Merchant ID: {service.merchant_id}")
print(f"Test Mode: {service.is_test}")

if service.merchant_id and service.merchant_id != 'YOUR_MERCHANT_ID':
    print("\n✅ PAYME TAYYOR!")
else:
    print("\n❌ Credentials to'ldirilmagan!")
print("=" * 60)
EOF
deactivate
```

**Ko'rinishi kerak:**
```
✅ PAYME TAYYOR!
```

### Frontend Test

1. https://ilmiyfaoliyat.uz ga kiring
2. To'lov sahifasiga o'ting
3. **Provider: Payme** tanlang
4. To'lovni amalga oshiring
5. Payme sahifasiga yo'naltirilishingiz kerak

---

## 🎯 HAMMASI SHU!

**✅ Backend deployed**  
**✅ Frontend deployed**  
**✅ Payme tayyor**

Endi foydalanuvchilar Click yoki Payme orqali to'lov qilishlari mumkin!

---

## 📊 LOG'LARNI KUZATISH (Ixtiyoriy)

```bash
# Payme callback'larni ko'rish
sudo tail -f /phonix/backend/logs/gunicorn-error.log | grep payme

# Backend status
sudo systemctl status phoenix-backend
```

---

## ❓ MUAMMOLAR?

### Credentials noto'g'ri

```bash
cd /phonix/backend
nano .env
# PAYME_MERCHANT_ID va boshqalarni tekshiring
sudo systemctl restart phoenix-backend
```

### Backend ishlamayapti

```bash
sudo journalctl -u phoenix-backend -n 50 --no-pager
# Xatolarni o'qing
```

### Frontend'da Payme ko'rinmayapti

```bash
cd /phonix/frontend
git pull origin master
npm run build
```

---

## 🎉 TAYYOR!

**Click + Payme = 2 ta to'lov tizimi!**

Foydalanuvchilar endi:
- ✅ Click orqali to'lov qilishlari mumkin
- ✅ Payme orqali to'lov qilishlari mumkin

**Muvaffaqiyat!** 🚀
