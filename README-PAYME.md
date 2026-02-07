# 🚀 Payme To'lov - Bitta Buyruq bilan O'rnatish

## ⚡ SUPER OSON - FAQAT 1 TA BUYRUQ!

---

## 📋 BOSHLASH (2 daqiqa)

### 1️⃣ Payme Credentials Oling

1. https://business.payme.uz ga kiring
2. **Yozib oling:**
   - Merchant ID
   - Production Key  
   - Test Key

### 2️⃣ Server'ga Kirish

```bash
ssh root@your-server-ip
```

### 3️⃣ Bitta Buyruq - Hammasi Tayyor!

```bash
cd /phonix/backend
git pull origin master
chmod +x INSTALL-PAYME.sh
./INSTALL-PAYME.sh
```

**Script so'raydi:**
- Payme Merchant ID: `sizning_id`
- Payme Production Key: `sizning_key`
- Payme Test Key: `sizning_test_key`
- Test rejimda? (y/n): `y`

**Hammasi!** Script avtomatik:
- ✅ Backend'ni yangilaydi
- ✅ .env faylini o'zgartiradi (nano kerak emas!)
- ✅ Migration qo'llaydi
- ✅ Payme service test qiladi
- ✅ Backend restart qiladi
- ✅ Frontend yangilaydi

---

## 🎯 KEYINGI QADAM (1 daqiqa)

Faqat Payme merchant panel'da endpoint kiriting:

1. https://business.payme.uz ga kiring
2. Service → Endpoint URL:
   ```
   https://api.ilmiyfaoliyat.uz/api/v1/payments/payme/
   ```
3. Method: **POST**
4. Protocol: **JSON-RPC 2.0**
5. Saqlang

---

## ✅ TAYYOR!

To'lovlar ishlaydi:
- ✅ Click (avval qo'shilgan)
- ✅ Payme (yangi qo'shildi)

---

## 🧪 TEST

### Backend Test

```bash
cd /phonix/backend
source venv/bin/activate
python << 'EOF'
from apps.payments.payme_service import PaymeService
s = PaymeService()
print(f"Merchant ID: {s.merchant_id}")
print(f"Test Mode: {s.is_test}")
EOF
deactivate
```

### Frontend Test

1. https://ilmiyfaoliyat.uz
2. To'lov sahifasi
3. Provider: **Payme**
4. To'lov qiling

---

## 📊 LOG'LAR

```bash
# Payme callback'lar
sudo tail -f /phonix/backend/logs/gunicorn-error.log | grep payme

# Backend status
sudo systemctl status phoenix-backend
```

---

## 🎉 MUVAFFAQIYAT!

**Bitta buyruq bilan hammasi tayyor!** 🚀
