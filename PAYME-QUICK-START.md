# 🚀 Payme To'lov Tizimi - Tezkor Boshlash

## ⚡ BIR QADAMDA DEPLOY

### Server'da faqat 3 ta buyruq:

```bash
# 1. Deploy scriptni yuklab olish
cd /phonix
curl -O https://raw.githubusercontent.com/aiziyrak-coder/phonixB/master/DEPLOY-PAYME.sh
chmod +x DEPLOY-PAYME.sh

# 2. Payme credentials kiritish
nano /phonix/backend/.env
# Quyidagilarni qo'shing:
# PAYME_MERCHANT_ID=sizning_id
# PAYME_MERCHANT_KEY=sizning_key
# PAYME_TEST_KEY=sizning_test_key

# 3. Deploy qilish
./DEPLOY-PAYME.sh
```

**Hammasi tayyor!** 🎉

---

## 📋 BATAFSIL QADAMLAR

### 1️⃣ Server'ga Kirish

```bash
ssh root@your-server-ip
```

### 2️⃣ Payme Credentials Olish

1. https://business.payme.uz ga kiring
2. Merchant account yarating
3. Quyidagilarni yozib oling:
   - **Merchant ID**
   - **Production Key**
   - **Test Key**

### 3️⃣ Credentials Kiritish

```bash
cd /phonix/backend
nano .env
```

**Faylga qo'shing:**
```env
PAYME_MERCHANT_ID=12345
PAYME_MERCHANT_KEY=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456
PAYME_TEST_KEY=TESTKEY123456789
PAYME_IS_TEST=True
PAYME_ENDPOINT=https://checkout.paycom.uz
```

**Saqlash:** `Ctrl+O`, `Enter`, `Ctrl+X`

### 4️⃣ Deploy Script Yuklab Olish

```bash
cd /phonix
wget https://raw.githubusercontent.com/aiziyrak-coder/phonixB/master/DEPLOY-PAYME.sh
chmod +x DEPLOY-PAYME.sh
```

**YOKI qo'lda yaratish:**
```bash
cd /phonix
nano DEPLOY-PAYME.sh
# Script kodini ko'chirib joylashtiring (DEPLOY-PAYME.sh faylidan)
chmod +x DEPLOY-PAYME.sh
```

### 5️⃣ Deploy Qilish

```bash
./DEPLOY-PAYME.sh
```

Script avtomatik:
- ✅ Backend'ni Git'dan yangilaydi
- ✅ Migration qo'llaydi
- ✅ Payme service test qiladi
- ✅ Backend restart qiladi
- ✅ Frontend yangilaydi

---

## 🧪 TEST QILISH

### Backend Test

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
print(f"✅ Merchant ID: {service.merchant_id}")
print(f"✅ Test Mode: {service.is_test}")
EOF
deactivate
```

### Frontend Test

1. https://ilmiyfaoliyat.uz ga kiring
2. To'lov sahifasiga o'ting
3. Provider: **Payme** tanlang
4. To'lovni amalga oshiring

---

## 🔧 PAYME MERCHANT PANEL

### Endpoint URL Kiritish

1. https://business.payme.uz ga kiring
2. **Сервисы** → Service'ni tahrirlang
3. **Endpoint URL:**
   ```
   https://api.ilmiyfaoliyat.uz/api/v1/payments/payme/
   ```
4. **Method:** POST
5. **Protocol:** JSON-RPC 2.0
6. Saqlang

---

## 📊 LOG'LARNI KUZATISH

```bash
# Payme callback'lar
sudo tail -f /phonix/backend/logs/gunicorn-error.log | grep -i payme

# Backend status
sudo systemctl status phoenix-backend

# Access log
sudo tail -f /phonix/backend/logs/gunicorn-access.log | grep payme
```

---

## ❓ MUAMMOLARNI HAL QILISH

### "Credentials not configured"

**Yechim:**
```bash
cd /phonix/backend
nano .env
# PAYME_MERCHANT_ID va boshqalarni to'ldiring
sudo systemctl restart phoenix-backend
```

### "Migration failed"

**Yechim:**
```bash
cd /phonix/backend
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate --run-syncdb
deactivate
sudo systemctl restart phoenix-backend
```

### Backend ishlamayapti

**Yechim:**
```bash
sudo journalctl -u phoenix-backend -n 50 --no-pager
# Xatolarni o'qing va tuzating
```

---

## 📞 YORDAM

**Payme Support:**
- Website: https://help.paycom.uz
- Telegram: @PaymeSupport
- Email: support@paycom.uz

**Texnik Yordam:**
- PAYME-INTEGRATION-GUIDE.md ni o'qing
- Log'larni tekshiring

---

## ✅ CHECKLIST

Deploy qilishdan oldin:

- [ ] Payme merchant account yaratildi
- [ ] Merchant ID, keys olindi
- [ ] Server'ga SSH orqali kirish mumkin
- [ ] `/phonix/backend/.env` fayliga credentials kiritildi
- [ ] `DEPLOY-PAYME.sh` script yuklab olindi

Deploy qilgandan keyin:

- [ ] Backend restart qilindi
- [ ] Migration qo'llandi
- [ ] Payme service test qilindi
- [ ] Payme merchant panel'da endpoint URL kiritildi
- [ ] Test to'lov amalga oshirildi

---

**🎉 TAYYOR! Payme to'lovlar ishlaydi!** 🚀
