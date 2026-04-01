#!/usr/bin/env python
"""
Barcha test userlarni qayta yaratish scripti
Avval mavjud userlarni o'chiradi, keyin yangidan yaratadi
Django shell'da ishlatish: python manage.py shell < recreate_all_users.py
Yoki to'g'ridan-to'g'ri: python recreate_all_users.py
"""

import os
import django
from django.conf import settings

# Django setup
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from apps.users.models import User

def recreate_all_users():
    """Barcha test userlarni qayta yaratish"""
    
    # Avval barcha test userlarni o'chirish
    print("="*60)
    print("🗑️  MAVJUD TEST USERLARNI O'CHIRISH")
    print("="*60)
    
    test_phones = [
        '998901001001', '998901001002', '998901001003',
        '998901001004', '998901001005', '998901001006',
        '998901001007'
    ]
    
    deleted_count = 0
    for phone in test_phones:
        try:
            users = User.objects.filter(phone=phone)
            if users.exists():
                count = users.count()
                users.delete()
                deleted_count += count
                print(f"✅ O'chirildi: {phone} ({count} ta)")
            else:
                print(f"⚠️  Topilmadi: {phone}")
        except Exception as e:
            print(f"❌ Xatolik o'chirishda {phone}: {str(e)}")
    
    print(f"\n📊 Jami o'chirildi: {deleted_count} ta user\n")
    
    # Endi yangi userlarni yaratish
    print("="*60)
    print("🆕 YANGI USERLAR YARATISH")
    print("="*60)
    
    test_users = [
        {
            'phone': '998901001001',
            'email': 'admin@ilmiyfaoliyat.uz',
            'first_name': 'Admin',
            'last_name': 'Bosh',
            'patronymic': 'Superuser',
            'role': 'super_admin',
            'affiliation': 'Phoenix Scientific Platform',
            'password': 'Admin@1234567890',
            'is_staff': True,
            'is_superuser': True,
            'description': 'Super Admin - Tizim boshqaruvchi'
        },
        {
            'phone': '998901001002',
            'email': 'editor@ilmiyfaoliyat.uz',
            'first_name': 'Tahrirchi',
            'last_name': 'Bosh',
            'patronymic': 'Admin',
            'role': 'journal_admin',
            'affiliation': 'Phoenix Scientific Platform',
            'password': 'Editor@1234567890',
            'is_staff': True,
            'is_superuser': False,
            'description': 'Jurnal Admin - Maqolalar boshqaruvchi'
        },
        {
            'phone': '998901001003',
            'email': 'reviewer1@ilmiyfaoliyat.uz',
            'first_name': 'Reviewer',
            'last_name': 'Birinchi',
            'patronymic': 'Ilmiy',
            'role': 'reviewer',
            'affiliation': 'Tashkent State University',
            'password': 'Reviewer@1234567890',
            'is_staff': False,
            'is_superuser': False,
            'specializations': ['Computer Science', 'Information Technology'],
            'description': 'Reviewer 1 - Kompyuter fanlari'
        },
        {
            'phone': '998901001004',
            'email': 'reviewer2@ilmiyfaoliyat.uz',
            'first_name': 'Reviewer',
            'last_name': 'Ikkinchi',
            'patronymic': 'Ilmiy',
            'role': 'reviewer',
            'affiliation': 'National University of Uzbekistan',
            'password': 'Reviewer@1234567890',
            'is_staff': False,
            'is_superuser': False,
            'specializations': ['Mathematics', 'Physics'],
            'description': 'Reviewer 2 - Matematika va Fizika'
        },
        {
            'phone': '998901001005',
            'email': 'author1@ilmiyfaoliyat.uz',
            'first_name': 'Muallif',
            'last_name': 'Birinchi',
            'patronymic': 'Ilmiy',
            'role': 'author',
            'affiliation': 'Tashkent Institute of Technology',
            'password': 'Author@1234567890',
            'is_staff': False,
            'is_superuser': False,
            'description': 'Author - Maqola yozuvchi'
        },
        {
            'phone': '998901001006',
            'email': 'accountant@ilmiyfaoliyat.uz',
            'first_name': 'Buxgalter',
            'last_name': 'Bosh',
            'patronymic': 'Moliyaviy',
            'role': 'accountant',
            'affiliation': 'Phoenix Scientific Platform',
            'password': 'Accountant@1234567890',
            'is_staff': True,
            'is_superuser': False,
            'description': 'Accountant - To\\lov boshqaruvchi'
        },
        {
            'phone': '998901001007',
            'email': 'operator@ilmiyfaoliyat.uz',
            'first_name': 'Operator',
            'last_name': 'Bosh',
            'patronymic': 'Koordinator',
            'role': 'operator',
            'affiliation': 'Phoenix Scientific Platform',
            'password': 'Operator@1234567890',
            'is_staff': True,
            'is_superuser': False,
            'description': 'Operator - Barcha so\\rovlarni nazorat qiluvchi'
        },
    ]
    
    created_users = []
    
    for user_data in test_users:
        phone = user_data.pop('phone')
        email = user_data.pop('email')
        password = user_data.pop('password')
        description = user_data.pop('description', '')
        
        try:
            # Create new user
            user = User.objects.create_user(
                phone=phone,
                email=email,
                password=password,
                **user_data
            )
            
            # Add gamification badges
            if user.role == 'author':
                user.gamification_badges = ['Yangi Muallif']
                user.gamification_points = 0
            elif user.role == 'reviewer':
                user.gamification_badges = ['Yangi Reviewer']
                user.gamification_points = 0
            elif user.role in ['super_admin', 'journal_admin', 'operator']:
                user.gamification_badges = ['Administrator']
                user.gamification_points = 1000
            elif user.role == 'accountant':
                user.gamification_badges = ['Buxgalter']
                user.gamification_points = 500
            
            user.save()
            
            print(f"\n✅ YARATILDI: {description}")
            print(f"   Phone: {phone}")
            print(f"   Email: {email}")
            print(f"   Role: {user.role}")
            print(f"   Password: {password}")
            
            created_users.append({
                'status': 'created',
                'phone': phone,
                'email': email,
                'role': user.role,
                'password': password,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'affiliation': user.affiliation,
            })
        
        except Exception as e:
            print(f"\n❌ XATOLIK: {description}")
            print(f"   Phone: {phone}")
            print(f"   Error: {str(e)}")
            created_users.append({
                'status': 'error',
                'phone': phone,
                'email': email,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*60)
    print("📊 YAKUNIY HISOB")
    print("="*60)
    print(f"Jami yaratildi: {len(created_users)}")
    print(f"Muvaffaqiyatli: {len([u for u in created_users if u['status'] == 'created'])}")
    print(f"Xatolik: {len([u for u in created_users if u['status'] == 'error'])}")
    
    # Print credentials table
    print("\n" + "="*70)
    print("🔐 BARCHA FOYDALANUVCHILAR LOGIN MA'LUMOTLARI")
    print("="*70)
    
    for user in created_users:
        if user['status'] == 'created':
            role_emoji = {
                'super_admin': '👑',
                'journal_admin': '📝',
                'reviewer': '✅',
                'author': '✍️',
                'accountant': '💰',
                'operator': '📋'
            }.get(user['role'], '👤')
            
            print(f"\n{role_emoji} {user['email']}")
            print(f"   📱 Phone: {user['phone']}")
            print(f"   🎭 Role: {user['role']}")
            print(f"   🔑 Password: {user['password']}")
    
    print("\n" + "="*70)
    print("ℹ️  DIQQAT! Barcha parollar oshkor ko'rsatilgan.")
    print("   Production muhitda parollarni o'zgartiring!")
    print("="*70)
    
    return created_users


if __name__ == '__main__':
    recreate_all_users()
