# 🔑 Click Secret Key Olish - Qisqa Yo'riqnoma

## ⚡ TEZKOR YECHIM

### **1. Click Support'ga Xabar Yuborish (2 daqiqa)**

**Telegram:** @clicksupport

**Xabar (Copy-paste qiling):**

```
Ассалому алейкум!

Менга service 82154 учун secret key керак.

Service ID: 82154
Merchant ID: 45730

Prepare callback'да "Invalid signature" хато келяпти.

Service 82154 учун secret key беринг.

Раҳмат!
```

**Yoki Ruscha:**

```
Здравствуйте!

Мне нужен secret key для service 82154.

Service ID: 82154
Merchant ID: 45730

В prepare callback ошибка "Invalid signature".

Прошу предоставить secret key.

Спасибо!
```

---

### **2. Kalitni Olgandan Keyin Server'da Qo'yish**

#### **Variant A: Script Orqali (Oson)**

```bash
cd /phonix/backend
chmod +x SET-CLICK-KEY.sh
./SET-CLICK-KEY.sh
```

Script so'raydi:
```
Click'dan olgan Service 82154 secret key'ni kiriting: 
```

**Kalitni kiriting va Enter bosing.**

---

#### **Variant B: Qo'lda (Nano Orqali)**

```bash
cd /phonix/backend
nano .env
```

**Faylning oxiriga qo'shing:**

```env
CLICK_SERVICE_82154_SECRET_KEY=CLICK_DAN_OLGAN_KALIT
```

**⚠️ MUHIM:** `CLICK_DAN_OLGAN_KALIT` o'rniga **Click'dan olgan to'g'ri kalitni** kiriting!

**Saqlash:** `Ctrl+O`, `Enter`, `Ctrl+X`

**Restart:**

```bash
sudo systemctl restart phoenix-backend
```

---

## 🧪 MUVAQQAT YECHIM (Kalitni Olmaguncha)

Agar Click'dan kalitni ololmasangiz, muvaqqat yechim:

```bash
cd /phonix/backend
nano .env
```

**Qo'shing:**

```env
# MUVAQQAT - Click'dan olgan to'g'ri kalitni kiriting!
CLICK_SERVICE_82154_SECRET_KEY=<CLICK_82154_SECRET>
```

**⚠️ Eslatma:** Bu muvaqqat kalit. Click'dan olgan **to'g'ri kalitni** kiriting!

---

## ✅ TEKSHIRISH

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
key = service.get_secret_key_for_service('82154')
print(f"✅ Service 82154 secret key: {key[:15]}...")
EOF
deactivate
```

---

## 📞 CLICK SUPPORT

- **Telegram:** @clicksupport ⚡ (Eng tezkor!)
- **Email:** support@click.uz
- **Telefon:** +998 78 150 01 50

---

## 🎯 XULOSA

1. ✅ Click support'ga xabar yuboring (@clicksupport)
2. ✅ Service 82154 uchun secret key so'rang
3. ✅ Kalitni olgandan keyin server'da `.env` fayliga qo'ying
4. ✅ Backend'ni restart qiling
5. ✅ Test qiling

**Hammasi tayyor!** 🚀
