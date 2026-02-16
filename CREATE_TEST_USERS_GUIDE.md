# Phonix Platform - Test Users Yaratish

## 🚀 Usullar

### 1️⃣ Django Management Command (Tavsiyalangan)

```bash
# Backend folderga o'ting
cd backend

# Test users yaratish
python manage.py create_test_users

# Mavjud userlarni qayta yaratish (reset)
python manage.py create_test_users --reset
```

### 2️⃣ Direct Python Script

```bash
# Backend folderga o'ting
cd backend

# Script ishga tushirish
python create_test_users.py
```

### 3️⃣ Django Shell

```bash
# Django shell'ni ochish
python manage.py shell

# Quyidagi kodni copy-paste qiling
from apps.users.models import User

# Admin user
admin = User.objects.create_user(
    phone='998901001001',
    email='admin@ilmiyfaoliyat.uz',
    password='Admin@123456',
    first_name='Admin',
    last_name='Bosh',
    role='super_admin',
    affiliation='Phoenix Scientific Platform',
    is_staff=True,
    is_superuser=True
)

# Editor user
editor = User.objects.create_user(
    phone='998901001002',
    email='editor@ilmiyfaoliyat.uz',
    password='Editor@123456',
    first_name='Tahrirchi',
    last_name='Bosh',
    role='journal_admin',
    affiliation='Phoenix Scientific Platform',
    is_staff=True,
    is_superuser=False
)

print("✅ Admin va Editor userlar yaratildi!")
```

---

## 👥 YARATILADI USERLAR

### 1. **Super Admin (Tizom Boshqaruvchi)**
```
Email: admin@ilmiyfaoliyat.uz
Phone: 998901001001
Password: Admin@123456
Role: super_admin
Huquqlar: Barcha huquqlar
```

### 2. **Journal Admin / Editor (Tahrirchi)**
```
Email: editor@ilmiyfaoliyat.uz
Phone: 998901001002
Password: Editor@123456
Role: journal_admin
Huquqlar: Maqola boshqaruvi, review approval
```

### 3. **Reviewer 1 (Tekshiruvchi)**
```
Email: reviewer1@ilmiyfaoliyat.uz
Phone: 998901001003
Password: Reviewer@123456
Role: reviewer
Specializations: Computer Science, IT
```

### 4. **Reviewer 2 (Tekshiruvchi)**
```
Email: reviewer2@ilmiyfaoliyat.uz
Phone: 998901001004
Password: Reviewer@123456
Role: reviewer
Specializations: Mathematics, Physics
```

### 5. **Author (Muallif)**
```
Email: author1@ilmiyfaoliyat.uz
Phone: 998901001005
Password: Author@123456
Role: author
```

### 6. **Accountant (Buxgalter)**
```
Email: accountant@ilmiyfaoliyat.uz
Phone: 998901001006
Password: Accountant@123456
Role: accountant
Huquqlar: To'lovlar boshqaruvi
```

---

## ✅ TEST QILISH

### Login Test
```bash
# Frontend'dan login
https://ilmiyfaoliyat.uz/#/login

# Yoki API orqali
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "998901001001", "password": "Admin@123456"}'
```

### Admin Panel
```
URL: http://localhost:8000/admin/
Email: admin@ilmiyfaoliyat.uz
Password: Admin@123456
```

---

## 🔒 PASSWORD TALABLARI (Optional)

Xuvddi parollarni o'zgartirish parol tahlili uchun:
- Min 8 belgisi
- Raqam + harf + maxsus belgi
- Lexicon bilan tekshirish

Frontend'dan profil yangilash orqali:
```
PUT /api/v1/auth/update_profile/
{
    "password": "NovyPassword@123456"
}
```

---

## 🗑️ USERS O'CHIRISH

```bash
# Django shell'da
python manage.py shell

from apps.users.models import User
User.objects.filter(email='test@example.com').delete()
```

---

## 📝 NOTES

- Barcha test Password'lar `@123456` bilan tugaydi
- Production'da complex parollar ishlating
- Admin user Django admin panel'ga kirish uchun
- Email'lar birlamchi uchun haqiqiy bo'lishi shart emas (test uchun)
- Phone raqamlari noqun uchun "998901001XXX" pattern'ini ishlatishi mumkin

---

**Created:** 2026-02-16
**Updated:** 2026-02-16
