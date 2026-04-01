# 🔐 PHOENIX PLATFORM - TEST FOYDALANUVCHILAR

## 📋 Barcha Rollar va Login Ma'lumotlari

### 1. 👑 Super Admin (Bosh Administrator)
```
Email: admin@ilmiyfaoliyat.uz
Phone: 998901001001
Password: Admin@1234567890
Role: super_admin
```
**Imkoniyatlari:**
- Tizimni to'liq boshqarish
- Barcha foydalanuvchilarni boshqarish
- Narxlarni o'zgartirish
- Moliyaviy hisobotlar
- DOI va UDK so'rovlarini ko'rish

---

### 2. 📝 Journal Admin (Tahrirchi)
```
Email: editor@ilmiyfaoliyat.uz
Phone: 998901001002
Password: Editor@1234567890
Role: journal_admin
```
**Imkoniyatlari:**
- Jurnal maqolalarini boshqarish
- Nashrga tayyor maqolalarni ko'rish
- Nashr etilgan maqolalar
- Muallif nashrlarini ko'rish

---

### 3. ✅ Reviewer 1 (Taqrizchi - Kompyuter fanlari)
```
Email: reviewer1@ilmiyfaoliyat.uz
Phone: 998901001003
Password: Reviewer@1234567890
Role: reviewer
```
**Imkoniyatlari:**
- Taqrizga kelgan maqolalarni ko'rish
- DOI so'rovlari
- UDK so'rovlari
- Profilini boshqarish

---

### 4. ✅ Reviewer 2 (Taqrizchi - Matematika va Fizika)
```
Email: reviewer2@ilmiyfaoliyat.uz
Phone: 998901001004
Password: Reviewer@1234567890
Role: reviewer
```
**Imkoniyatlari:**
- Taqrizga kelgan maqolalarni ko'rish
- DOI so'rovlari
- UDK so'rovlari
- Profilini boshqarish

---

### 5. ✍️ Author (Muallif)
```
Email: author1@ilmiyfaoliyat.uz
Phone: 998901001005
Password: Author@1234567890
Role: author
```
**Imkoniyatlari:**
- Maqola yuborish
- Xizmatlardan foydalanish (DOI, UDK, Antiplagiat, Tarjima)
- Maqolalarini kuzatish
- To'plamlar yaratish
- Arxiv hujjatlar

---

### 6. 💰 Accountant (Buxgalter)
```
Email: accountant@ilmiyfaoliyat.uz
Phone: 998901001006
Password: Accountant@1234567890
Role: accountant
```
**Imkoniyatlari:**
- Moliyaviy operatsiyalarni ko'rish
- Tranzaksiyalar statistikasi
- To'lov hisobotlari

---

### 7. 📋 Operator (Koordinator) - YANGI!
```
Email: operator@ilmiyfaoliyat.uz
Phone: 998901001007
Password: Operator@1234567890
Role: operator
```
**Imkoniyatlari:**
- ⭐ Barcha so'rovlarni ko'rish (DOI, UDK, Namuna, va boshqalar)
- ⭐ Har bir jurnal adminiga qaysi buyurtma tushganini ko'rish
- ⭐ Qaysi taqrizchiga qaysi maqola yuborilganini monitoring qilish
- ⭐ Barcha xizmatlar bo'yicha to'liq nazorat
- ⭐ Filtrlash va qidirish imkoniyati
- ⭐ Statistikalar (Jami, Tekshiruvda, Yakunlangan, Rad etilgan)

---

## 🚀 Tezkor Kirish

### Localhost (Development)
```
URL: http://localhost:3000
Backend: http://localhost:8000
```

### Demo Hisoblar
- **Admin:** admin@ilmiyfaoliyat.uz / Admin@1234567890
- **Operator:** operator@ilmiyfaoliyat.uz / Operator@1234567890
- **Author:** author1@ilmiyfaoliyat.uz / Author@1234567890

---

## 🎭 Rol Tavsiflari

| Rol | Vazifasi | Asosiy Funksiyalari |
|-----|----------|---------------------|
| 👑 Super Admin | Tizim boshqaruvchisi | User management, narxlar, moliya, barcha so'rovlar |
| 📝 Journal Admin | Jurnal tahrirchisi | Maqolalarni qabul qilish, tahrirlash, nashr etish |
| ✅ Reviewer | Taqrizchi | Maqolalarni tekshirish, DOI/UDK so'rovlari |
| ✍️ Author | Muallif | Maqola yuborish, xizmatlardan foydalanish |
| 💰 Accountant | Buxgalter | To'lovlarni kuzatish, moliyaviy hisobotlar |
| 📋 Operator | Koordinator | **Barcha so'rovlarni monitoring qilish**, nazorat |

---

## ⚠️ Muhim Eslatmalar

1. **Xavfsizlik:** Bu test parollar! Production muhitda parollarni o'zgartiring.
2. **Telefon raqamlar:** Barcha test raqamlar `99890100XXXX` formatida
3. **Parol talablari:** Kamida 10 ta belgi, katta/kichik harflar va raqamlar
4. **Gamification:** Har bir rol uchun boshlang'ich ball va nishonlar berilgan

---

## 🔄 Userlarni Qayta Yaratish

Agar userlarni qaytadan yaratish kerak bo'lsa:

```bash
cd backend
python recreate_all_users.py
```

Bu script:
1. ✅ Avval mavjud test userlarni o'chiradi
2. ✅ Yangidan barchasini yaratadi
3. ✅ Gamification ball va nishonlarni o'rnatadi
4. ✅ Barcha login ma'lumotlarini konsolda ko'rsatadi

---

## 📞 Qo'llab-quvvatlash

Savollar yoki muammolar bo'lsa:
- Telegram: https://t.me/Iskandar_Abdurakhimov
- Platform: https://ilmiyfaoliyat.uz

---

**📅 Oxirgi yangilanish:** 2026-03-13
**✨ Yangi rol qo'shildi:** Operator (Barcha so'rovlarni nazorat qiluvchi)
