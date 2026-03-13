#!/usr/bin/env python
"""
PHONIX Platform - Demo foydalanuvchilar va Django admin (mijoz uchun).
Ishlatish: python create_admin_editor_users.py
Yoki: python manage.py setup_demo_and_admin  (afzallik beriladi)

- 5 ta demo user: 998901001001–005, parollar Demo@admin1, Demo@editor1, ...
- Django admin: 998907863888, parol Admin123 (/admin/ uchun)
Hech qanday foydalanuvchini o'chirmaydi.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    call_command('setup_demo_and_admin')
    print('\n✨ Tugadi. Tizimga kirish: 998901001001 / Demo@admin1')
    print('   Django admin: 998907863888 / Admin123\n')
