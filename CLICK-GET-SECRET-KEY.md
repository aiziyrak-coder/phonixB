# 🔑 Click Secret Key Olish - To'liq Yo'riqnoma

## ⚠️ MUAMMO

Server'da `.env` fayliga `CLICK_SERVICE_82154_SECRET_KEY` ni qo'yish kerak, lekin kalit topilmagan.

---

## 📞 CLICK SUPPORT BILAN BOG'LANISH

### **1. Telegram Orqali (Eng Tezkor)**

**Telegram:** @clicksupport

**Xabar matni (Ruscha):**

```
Здравствуйте!

Мне нужен secret key для моего сервиса.

Service ID: 82154
Merchant ID: 45730

В prepare callback приходит ошибка "Invalid signature".

Прошу предоставить secret key для service 82154.

Спасибо!
```

**Yoki O'zbekcha:**

```
Ассалому алейкум!

Менга service 82154 учун secret key керак.

Service ID: 82154
Merchant ID: 45730

Prepare callback'да "Invalid signature" хато келяпти.

Service 82154 учун secret key беринг.

Раҳмат!
```

---

### **2. Email Orqali**

**Email:** support@click.uz

**Mavzu:** Secret key для service 82154

**Xabar matni:**

```
Здравствуйте!

Мне нужен secret key для моего сервиса.

Данные сервиса:
- Service ID: 82154
- Merchant ID: 45730
- Домен: api.ilmiyfaoliyat.uz

Проблема:
В prepare callback приходит ошибка "Invalid signature".
Это происходит потому, что я не знаю правильный secret key для service 82154.

Прошу предоставить secret key для service 82154.

Спасибо!
```

---

### **3. Telefon Orqali**

**Telefon:** +998 78 150 01 50

**Nima demoqchi bo'lishingiz kerak:**

> "Ассалому алейкум! Менга service 82154 учун secret key керак. Prepare callback'да signature хато келяпти."

---

## 🔍 CLICK MERCHANT PANEL'DA TEKSHIRISH

1. **https://merchant.click.uz** ga kiring
2. Login qiling
3. **Сервисы** (Services) bo'limiga o'ting
4. **Service ID 82154** ni toping va oching
5. Service sozlamalarida **secret key** ko'rsatilgan bo'lishi mumkin

**⚠️ Eslatma:** Ba'zida secret key merchant panel'da ko'rsatilmaydi, faqat Click support orqali olish mumkin.

---

## 🧪 MUVAQQAT YECHIM (Test Uchun)

Agar Click'dan kalitni ololmasangiz, muvaqqat yechim:

### **Server'da .env faylini yangilash:**

```bash
cd /phonix/backend
nano .env
```

**Quyidagi qatorni qo'shing:**

```env
# Click Service 82154 secret key (MUVAQQAT - Click'dan olgan to'g'ri kalitni kiriting!)
CLICK_SERVICE_82154_SECRET_KEY=<CLICK_82154_SECRET>
```

**⚠️ MUHIM:** `<CLICK_82154_SECRET>` - bu muvaqqat kalit. Click'dan olgan **to'g'ri kalitni** kiriting!

**Saqlash:** `Ctrl+O`, `Enter`, `Ctrl+X`

**Backend restart:**

```bash
sudo systemctl restart phoenix-backend
```

---

## ✅ CLICK'DAN KALIT OLGANDAN KEYIN

1. **Click'dan olgan to'g'ri kalitni** `.env` fayliga kiriting:

```bash
cd /phonix/backend
nano .env
```

**Yangilash:**

```env
CLICK_SERVICE_82154_SECRET_KEY=CLICK_DAN_OLGAN_TOGRI_KALIT
```

2. **Backend restart:**

```bash
sudo systemctl restart phoenix-backend
```

3. **Test qiling:**

```bash
# Backend test
cd /phonix/backend
source venv/bin/activate
python << 'EOF'
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/phonix/backend')
django.setup()

from apps.payments.services import ClickPaymentService

service = ClickPaymentService()
key_82154 = service.get_secret_key_for_service('82154')
print(f"Service 82154 secret key: {key_82154[:10]}...")
EOF
deactivate
```

4. **Yangi to'lov qiling va log'larni kuzating:**

```bash
sudo tail -f /phonix/backend/logs/gunicorn-error.log | grep -i "signature\|service_id"
```

**Ko'rinishi kerak:**
```
Using secret key for service_id=82154
Expected signature: ..., Received signature: ...
✅ Signature match!
```

---

## 📋 CHECKLIST

- [ ] Click support'ga murojaat qilindi (@clicksupport yoki support@click.uz)
- [ ] Service 82154 uchun secret key so'raldi
- [ ] Click'dan kalit olindi
- [ ] `.env` fayliga kalit kiritildi
- [ ] Backend restart qilindi
- [ ] Test to'lov amalga oshirildi
- [ ] Signature mismatch muammosi hal bo'ldi

---

## 🎯 XULOSA

**Secret key Click support'dan olinishi kerak!**

- ✅ Telegram: @clicksupport (eng tezkor)
- ✅ Email: support@click.uz
- ✅ Telefon: +998 78 150 01 50

**Kalitni olgandan keyin `.env` fayliga kiriting va backend'ni restart qiling!**

---

*Yo'riqnoma: 2026-02-07*
