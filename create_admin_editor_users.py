#!/usr/bin/env python
"""
PHONIX Platform - Admin va Editor test users yaratish
Ishlatish: python create_admin_editor_users.py
"""

import os
import sys
import django

# Django sozlamalari
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django initialize
django.setup()

from apps.users.models import User
from django.db import transaction


def create_users():
    """Admin va Editor userlarni yaratish"""
    
    print("\n" + "="*70)
    print("🚀 PHONIX PLATFORM - TEST USERS YARATISH")
    print("="*70 + "\n")
    
    # Users to create
    test_users = [
        {
            'name': 'SUPER ADMIN (Tizom boshqaruvchi)',
            'phone': '998901001001',
            'email': 'admin@ilmiyfaoliyat.uz',
            'first_name': 'Admin',
            'last_name': 'Bosh',
            'patronymic': 'Superuser',
            'password': 'Admin@123456',
            'role': 'super_admin',
            'affiliation': 'Phoenix Scientific Platform',
            'is_staff': True,
            'is_superuser': True,
        },
        {
            'name': 'JOURNAL ADMIN / EDITOR (Tahrirchi)',
            'phone': '998901001002',
            'email': 'editor@ilmiyfaoliyat.uz',
            'first_name': 'Tahrirchi',
            'last_name': 'Bosh',
            'patronymic': 'Admin',
            'password': 'Editor@123456',
            'role': 'journal_admin',
            'affiliation': 'Phoenix Scientific Platform',
            'is_staff': True,
            'is_superuser': False,
        },
        {
            'name': 'REVIEWER 1 (Tekshiruvchi)',
            'phone': '998901001003',
            'email': 'reviewer1@ilmiyfaoliyat.uz',
            'first_name': 'Reviewer',
            'last_name': 'Birinchi',
            'patronymic': 'Ilmiy',
            'password': 'Reviewer@123456',
            'role': 'reviewer',
            'affiliation': 'Tashkent State University',
            'is_staff': False,
            'is_superuser': False,
            'specializations': ['Computer Science', 'Information Technology'],
        },
        {
            'name': 'REVIEWER 2 (Tekshiruvchi)',
            'phone': '998901001004',
            'email': 'reviewer2@ilmiyfaoliyat.uz',
            'first_name': 'Reviewer',
            'last_name': 'Ikkinchi',
            'patronymic': 'Ilmiy',
            'password': 'Reviewer@123456',
            'role': 'reviewer',
            'affiliation': 'National University of Uzbekistan',
            'is_staff': False,
            'is_superuser': False,
            'specializations': ['Mathematics', 'Physics', 'Statistics'],
        },
        {
            'name': 'AUTHOR (Muallif)',
            'phone': '998901001005',
            'email': 'author1@ilmiyfaoliyat.uz',
            'first_name': 'Muallif',
            'last_name': 'Birinchi',
            'patronymic': 'Ilmiy',
            'password': 'Author@123456',
            'role': 'author',
            'affiliation': 'Tashkent Institute of Technology',
            'is_staff': False,
            'is_superuser': False,
        },
        {
            'name': 'ACCOUNTANT (Buxgalter)',
            'phone': '998901001006',
            'email': 'accountant@ilmiyfaoliyat.uz',
            'first_name': 'Buxgalter',
            'last_name': 'Bosh',
            'patronymic': 'Moliyaviy',
            'password': 'Accountant@123456',
            'role': 'accountant',
            'affiliation': 'Phoenix Scientific Platform',
            'is_staff': True,
            'is_superuser': False,
        },
    ]
    
    created = []
    existing = []
    errors = []
    
    for user_data in test_users:
        name = user_data.pop('name')
        phone = user_data.pop('phone')
        email = user_data.pop('email')
        password = user_data.pop('password')
        
        try:
            with transaction.atomic():
                # Check if user exists
                if User.objects.filter(phone=phone).exists():
                    user = User.objects.get(phone=phone)
                    existing.append({
                        'name': name,
                        'email': email,
                        'phone': phone,
                        'role': user.role,
                    })
                    print(f"⚠️  MAVJUD: {name}")
                    print(f"    Email: {email}")
                    print(f"    Phone: {phone}\n")
                else:
                    # Create user
                    user = User.objects.create_user(
                        phone=phone,
                        email=email,
                        password=password,
                        **user_data
                    )
                    
                    # Set gamification
                    if user.role == 'reviewer':
                        user.gamification_badges = ['Yangi Reviewer', 'Ulug\'bek']
                        user.gamification_points = 100
                        user.reviews_completed = 0
                    elif user.role == 'author':
                        user.gamification_badges = ['Yangi Muallif', 'Innovator']
                        user.gamification_points = 0
                    elif user.role in ['super_admin', 'journal_admin', 'accountant']:
                        user.gamification_badges = ['Administrator', 'Verifikatsiyalangan']
                        user.gamification_points = 500
                    
                    user.save()
                    
                    created.append({
                        'name': name,
                        'email': email,
                        'phone': phone,
                        'password': password,
                        'role': user.role,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    })
                    
                    print(f"✅ YARATILDI: {name}")
                    print(f"   Email: {email}")
                    print(f"   Phone: {phone}")
                    print(f"   Password: {password}")
                    print(f"   Role: {user.role}\n")
        
        except Exception as e:
            errors.append({
                'name': name,
                'email': email,
                'phone': phone,
                'error': str(e),
            })
            print(f"❌ XATOLIK: {name}")
            print(f"   Error: {str(e)}\n")
    
    # Print summary
    print("="*70)
    print("📊 HISOB-KITOB")
    print("="*70)
    print(f"✅ Yaratilgan: {len(created)} ta")
    print(f"⚠️  Mavjud: {len(existing)} ta")
    print(f"❌ Xatolik: {len(errors)} ta")
    print(f"Jami: {len(created) + len(existing) + len(errors)} ta\n")
    
    # Print login credentials
    print("="*70)
    print("🔐 LOGIN CREDENTIALS")
    print("="*70 + "\n")
    
    all_users = created + existing
    for user_info in sorted(all_users, key=lambda x: x['email']):
        print(f"Email: {user_info['email']}")
        print(f"Phone: {user_info['phone']}")
        print(f"Role:  {user_info['role']}")
        if 'password' in user_info:
            print(f"Pass:  {user_info['password']}")
        print()
    
    print("="*70 + "\n")
    
    return {
        'created': len(created),
        'existing': len(existing),
        'errors': len(errors),
    }


if __name__ == '__main__':
    try:
        result = create_users()
        print(f"✨ ADMIN VA EDITOR USERS MUVAFFAQIYATLI YARATILDI!\n")
    except Exception as e:
        print(f"❌ XATOLIK: {str(e)}")
        sys.exit(1)
