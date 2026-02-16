# PHONIX Platform - Admin va Editor Users Yaratish

**Status:** ✅ Tayyor  
**Created:** 2026-02-16  
**Updated:** 2026-02-16

---

## 🎯 ADMIN VA EDITOR USERS YARATILDI

### ✅ Yaratilgan Files

1. **Management Command**
   - `backend/apps/users/management/commands/create_test_users.py` - Django command

2. **Python Scripts**
   - `backend/create_admin_editor_users.py` - Direct Python script (asosiy)
   - `backend/create_test_users.py` - Alternative script

3. **Shell Scripts**
   - `backend/create_users.sh` - Linux/Mac script
   - `backend/create_users.bat` - Windows batch script

4. **Database**
   - `backend/create_users.sql` - SQL insert script

5. **Documentation**
   - `backend/CREATE_TEST_USERS_GUIDE.md` - To'liq guide

---

## 🚀 ADMIN VA EDITOR USERS YARATISH

### 1️⃣ **Recommended Method** - Python Script Ishlatish

```bash
# Backend directory'ga o'tish
cd backend

# Virtual environment activation (agar kerak bo'lsa)
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Requirements o'rnatish
pip install -r requirements.txt

# Users yaratish
python create_admin_editor_users.py
```

### 2️⃣ **Windows Batch** - Windows'da ishlatish

```bash
cd backend
create_users.bat
```

### 3️⃣ **Linux/Mac Shell** - Linux/Mac'da ishlatish

```bash
cd backend
bash create_users.sh
```

### 4️⃣ **Django Management Command**

```bash
cd backend
python manage.py create_test_users
```

---

## 👥 YARATILADI USERS

### 1. **SUPER ADMIN** (Admin Panel'ga kirish)
```
Email: admin@ilmiyfaoliyat.uz
Phone: 998901001001
Password: Admin@123456
Role: super_admin

Huquqlar:
- Barcha Django admin functions
- User management
- System configuration
```

### 2. **JOURNAL ADMIN / EDITOR** (Tahrirchi)
```
Email: editor@ilmiyfaoliyat.uz
Phone: 998901001002
Password: Editor@123456
Role: journal_admin

Huquqlar:
- Maqola boshqaruvi
- Review approval
- Author management
- Journal settings
```

### 3. **REVIEWER 1** (Tekshiruvchi)
```
Email: reviewer1@ilmiyfaoliyat.uz
Phone: 998901001003
Password: Reviewer@123456
Role: reviewer
Specializations: Computer Science, IT
```

### 4. **REVIEWER 2** (Tekshiruvchi)
```
Email: reviewer2@ilmiyfaoliyat.uz
Phone: 998901001004
Password: Reviewer@123456
Role: reviewer
Specializations: Mathematics, Physics
```

### 5. **AUTHOR** (Muallif)
```
Email: author1@ilmiyfaoliyat.uz
Phone: 998901001005
Password: Author@123456
Role: author
```

### 6. **ACCOUNTANT** (Buxgalter)
```
Email: accountant@ilmiyfaoliyat.uz
Phone: 998901001006
Password: Accountant@123456
Role: accountant

Huquqlar:
- To'lov boshqaruvi
- Invoice management
```

---

## 🔐 LOGIN USULLARI

### Frontend'dan Login
```
URL: https://ilmiyfaoliyat.uz/#/login
Email va Password'ni kiriting (yuqorida ko'rsatilgan)
```

### Admin Panel'ga Login
```
URL: http://localhost:8000/admin/
Email: admin@ilmiyfaoliyat.uz
Password: Admin@123456
```

### API orqali Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "998901001001",
    "password": "Admin@123456"
  }'
```

---

## ✨ FEATURES

### Admin User
- ✅ Django admin panel access
- ✅ Barcha settings o'zgartirishga ruxsat
- ✅ User management
- ✅ System monitoring

### Editor/Journal Admin User
- ✅ Maqolalar boshqaruvi
- ✅ Review process boshqaruvi
- ✅ Author management
- ✅ Journal settings
- ✅ Statistics view

### Reviewer Users
- ✅ Maqolalarni tekshirish
- ✅ Recommendations berish
- ✅ Review history
- ✅ Specialization management

### Author User
- ✅ Maqola yuborish
- ✅ Maqola boshqaruvi
- ✅ Review qayt ko'rish
- ✅ Payment history

---

## 🧪 TEST QILISH

### Test Flow
1. Admin'ga login qilish
2. Editor'ga login qilish
3. Reviewer'ga login qilish
4. Author'ga login qilish
5. Har birining huquqlarini tekshirish

### Test Scenarios
- [ ] Admin panel'ga kirish
- [ ] User create/edit
- [ ] Maqola submission (author)
- [ ] Review process (reviewer)
- [ ] Approval process (editor)
- [ ] Content view (anonymous)

---

## 📝 NOTES

- **Password Format:** `Role@123456` (test uchun)
- **Phone Pattern:** `998901001XXX` (test uchun)
- **Email:** Real email bo'lishi shart emas (test uchun)
- **Reset:** Qayta yaratish uchun `--reset` flag'ni ishlatish mumkin

### Password O'zgartirish
```
Profile > Settings > Change Password
Yoki API:
PUT /api/v1/auth/update_profile/
```

---

## 🛠️ TROUBLESHOOTING

### Error: Django not found
```bash
pip install -r requirements.txt
```

### Error: Database locked
```bash
# SQLite uchun temp files o'chirish
rm db.sqlite3-wal
rm db.sqlite3-shm
```

### Error: Migrations needed
```bash
python manage.py migrate
```

### Users o'chirish (qayta yaratish)
```bash
python manage.py create_test_users --reset
```

---

## 📊 USER STATISTICS

**Faollangan Rollar:**
- ✅ author (1)
- ✅ reviewer (2)
- ✅ journal_admin (1)
- ✅ super_admin (1)
- ✅ accountant (1)

**Jami:** 6 ta test user

---

## 🔗 RELATED FILES

- [CREATE_TEST_USERS_GUIDE.md](CREATE_TEST_USERS_GUIDE.md) - To'liq guide
- [PLATFORM-ISSUES-FIXES.md](../PLATFORM-ISSUES-FIXES.md) - Issue fixelar
- [FINAL-AUDIT-REPORT.md](../FINAL-AUDIT-REPORT.md) - Audit report

---

**Prepared by:** Phonix Development Team  
**Last Updated:** 2026-02-16 16:30 UTC+5
