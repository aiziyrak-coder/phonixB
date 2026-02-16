#!/usr/bin/env python
"""
Test users yaratish scripti
Django shell'da ishlatish: python manage.py shell < create_test_users.py
Yoki to'g'ridan-to'g'ri: python create_test_users.py
"""

import os
import django
from django.conf import settings

# Django setup
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from apps.users.models import User

def create_test_users():
    """Turli rol uchun test userlar yaratish"""
    
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
            'description': 'Super Admin - Tizom boshqaruvchi'
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
            'description': 'Reviewer - Maqolalarni tekshiruvchi'
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
            'description': 'Reviewer - Matematics va Fizika'
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
            'description': 'Accountant - To\'lov boshqaruvchi'
        },
    ]
    
    created_users = []
    
    for user_data in test_users:
        phone = user_data.pop('phone')
        email = user_data.pop('email')
        password = user_data.pop('password')
        description = user_data.pop('description', '')
        
        try:
            # Check if user already exists
            if User.objects.filter(phone=phone).exists():
                user = User.objects.get(phone=phone)
                print(f"⚠️  MAVJUD: {description}")
                print(f"   Phone: {phone}")
                print(f"   Email: {email}")
                created_users.append({
                    'status': 'existing',
                    'phone': phone,
                    'email': email,
                    'role': user_data.get('role'),
                    'password': password
                })
            else:
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
                elif user.role in ['super_admin', 'journal_admin']:
                    user.gamification_badges = ['Administrator']
                    user.gamification_points = 1000
                
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
            print(f"❌ XATOLIK: {description}")
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
    print("📊 YARATILGAN USERLAR HISOB-KITOB")
    print("="*60)
    print(f"Jami: {len(created_users)}")
    print(f"Yaratildi: {len([u for u in created_users if u['status'] == 'created'])}")
    print(f"Mavjud: {len([u for u in created_users if u['status'] == 'existing'])}")
    print(f"Xatolik: {len([u for u in created_users if u['status'] == 'error'])}")
    
    # Print table
    print("\n" + "="*60)
    print("🔐 USER CREDENTIALS")
    print("="*60)
    
    for user in created_users:
        if user['status'] in ['created', 'existing']:
            print(f"\n{user['email']}")
            print(f"  Phone: {user['phone']}")
            print(f"  Role: {user['role']}")
            print(f"  Password: {user['password']}")
    
    print("\n" + "="*60)
    
    return created_users


if __name__ == '__main__':
    create_test_users()
