#!/usr/bin/env python
"""
PHONIX Platform - Operator foydalanuvchini yaratish
Ishlatish: python create_operator_user.py

Operator - Barcha so'rovlarni nazorat qiluvchi rol
- Phone: 998901001007
- Password: Operator@1234567890
- Email: operator@ilmiyfaoliyat.uz
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.users.models import User

def create_operator_user():
    """Operator foydalanuvchini yaratish yoki yangilash"""
    
    phone = '998901001007'
    password = 'Operator@1234567890'
    email = 'operator@ilmiyfaoliyat.uz'
    first_name = 'Operator'
    last_name = 'User'
    patronymic = ''
    affiliation = 'Phoenix Platform'
    role = 'operator'
    
    try:
        # Foydalanuvchi mavjud bo'lsa, parolni yangilash
        user = User.objects.get(phone=phone)
        user.set_password(password)
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.patronymic = patronymic
        user.affiliation = affiliation
        user.role = role
        user.is_active = True
        user.save()
        print(f"[UPDATE] Yangilandi: {phone} | Parol: {password}")
        
    except User.DoesNotExist:
        # Yangi foydalanuvchi yaratish
        user = User.objects.create_user(
            phone=phone,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            patronymic=patronymic,
            affiliation=affiliation,
            role=role,
        )
        print(f"[CREATE] Yaratildi: {phone} | Parol: {password}")
    
    except Exception as e:
        print(f"[ERROR] Xatolik: {str(e)}")
        return False
    
    return True

if __name__ == '__main__':
    print("="*60)
    print("PHOENIX PLATFORM - OPERATOR FOYDALANUVCHI YARATISH")
    print("="*60)
    print("")
    
    success = create_operator_user()
    
    if success:
        print("")
        print("="*60)
        print("✅ OPERATOR MUVAFFAQIYATLI YARATILDI!")
        print("="*60)
        print("")
        print("📋 Operator ma'lumotlari:")
        print("   📱 Phone: 998901001007")
        print("   🔑 Password: Operator@1234567890")
        print("   📧 Email: operator@ilmiyfaoliyat.uz")
        print("   👤 Role: operator")
        print("")
        print("🌐 Kirish:")
        print("   URL: https://ilmiyfaoliyat.uz")
        print("   Login: 998901001007")
        print("   Password: Operator@1234567890")
        print("")
    else:
        print("")
        print("❌ Xatolik yuz berdi!")
        sys.exit(1)
