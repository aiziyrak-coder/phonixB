"""
Demo foydalanuvchilar va Django admin hisobini yaratish/yangilash.
Ishlatish: python manage.py setup_demo_and_admin

- 5 ta demo user (Super Admin, Journal Admin, Reviewer, Author, Accountant) — parollarni Demo@admin1 va h.k. qilib yangilaydi.
- 1 ta Django admin user (998907863888, parol Admin123) — /admin/ uchun.
Hech qanday foydalanuvchini o'chirmaydi.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.users.models import User


DEMO_USERS = [
    {
        'phone': '998901001001',
        'email': 'admin@phoenix.uz',
        'first_name': 'Admin',
        'last_name': 'Boshqaruvchi',
        'patronymic': 'Super',
        'password': 'Demo@admin1',
        'role': 'super_admin',
        'affiliation': 'Phoenix Ilmiy Nashrlar Markazi',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'phone': '998901001002',
        'email': 'editor@phoenix.uz',
        'first_name': 'Tahrirchi',
        'last_name': 'Bosh',
        'patronymic': 'Admin',
        'password': 'Demo@editor1',
        'role': 'journal_admin',
        'affiliation': 'Phoenix Ilmiy Nashrlar Markazi',
        'is_staff': True,
        'is_superuser': False,
    },
    {
        'phone': '998901001003',
        'email': 'reviewer@phoenix.uz',
        'first_name': 'Taqrizchi',
        'last_name': 'Ilmiy',
        'patronymic': 'Reviewer',
        'password': 'Demo@review1',
        'role': 'reviewer',
        'affiliation': 'Toshkent Davlat Universiteti',
        'is_staff': False,
        'is_superuser': False,
    },
    {
        'phone': '998901001004',
        'email': 'author@phoenix.uz',
        'first_name': 'Muallif',
        'last_name': 'Demo',
        'patronymic': 'Author',
        'password': 'Demo@author1',
        'role': 'author',
        'affiliation': 'Toshkent Axborot Texnologiyalari Universiteti',
        'is_staff': False,
        'is_superuser': False,
    },
    {
        'phone': '998901001005',
        'email': 'accountant@phoenix.uz',
        'first_name': 'Buxgalter',
        'last_name': 'Moliyaviy',
        'patronymic': 'Hisob',
        'password': 'Demo@account1',
        'role': 'accountant',
        'affiliation': 'Phoenix Ilmiy Nashrlar Markazi',
        'is_staff': True,
        'is_superuser': False,
    },
]

DJANGO_ADMIN_PHONE = '998907863888'
DJANGO_ADMIN_PASSWORD = 'Admin123'
DJANGO_ADMIN_EMAIL = 'django_admin@phoenix.uz'


class Command(BaseCommand):
    help = "Demo foydalanuvchilar va Django admin (998907863888 / Admin123) yaratadi yoki parollarni yangilaydi. Hech kimni o'chirmaydi."

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-admin',
            action='store_true',
            help="Faqat 5 ta demo userni yangilash, Django admin userni yaratmaslik",
        )

    def handle(self, *args, **options):
        created = 0
        updated = 0
        errors = []

        with transaction.atomic():
            for data in DEMO_USERS:
                password = data.pop('password')
                phone = data['phone']
                try:
                    user, was_created = User.objects.get_or_create(
                        phone=phone,
                        defaults={k: v for k, v in data.items()}
                    )
                    if was_created:
                        user.set_password(password)
                        user.save()
                        created += 1
                        self.stdout.write(self.style.SUCCESS(f"[OK] Yaratildi: {phone} | {data['role']} | Parol: {password}"))
                    else:
                        for k, v in data.items():
                            setattr(user, k, v)
                        user.set_password(password)
                        user.save()
                        updated += 1
                        self.stdout.write(self.style.WARNING(f"[UPDATE] Yangilandi: {phone} | Parol: {password}"))
                    data['password'] = password
                except Exception as e:
                    errors.append(f"{phone}: {e}")
                    self.stdout.write(self.style.ERROR(f"[ERR] {phone}: {e}"))
                    data['password'] = password

            if not options.get('no_admin'):
                try:
                    admin_user, was_created = User.objects.get_or_create(
                        phone=DJANGO_ADMIN_PHONE,
                        defaults={
                            'email': DJANGO_ADMIN_EMAIL,
                            'first_name': 'Django',
                            'last_name': 'Admin',
                            'patronymic': 'Platform',
                            'affiliation': 'Phoenix',
                            'role': 'super_admin',
                            'is_staff': True,
                            'is_superuser': True,
                        }
                    )
                    admin_user.set_password(DJANGO_ADMIN_PASSWORD)
                    admin_user.is_staff = True
                    admin_user.is_superuser = True
                    admin_user.email = DJANGO_ADMIN_EMAIL
                    admin_user.save()
                    if was_created:
                        created += 1
                        self.stdout.write(self.style.SUCCESS(f"[OK] Django admin yaratildi: {DJANGO_ADMIN_PHONE} | Parol: {DJANGO_ADMIN_PASSWORD}"))
                    else:
                        updated += 1
                        self.stdout.write(self.style.WARNING(f"[UPDATE] Django admin yangilandi: {DJANGO_ADMIN_PHONE} | Parol: {DJANGO_ADMIN_PASSWORD}"))
                except Exception as e:
                    errors.append(f"Django admin {DJANGO_ADMIN_PHONE}: {e}")
                    self.stdout.write(self.style.ERROR(f"[ERR] Django admin: {e}"))

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS(f"Yaratilgan: {created} | Yangilangan: {updated} | Xatolik: {len(errors)}"))
        self.stdout.write('=' * 70)
        self.stdout.write('')
        self.stdout.write('DEMO LOGIN (tizimga kirish):')
        self.stdout.write('   Telefon        | Parol        | Rol')
        self.stdout.write('   ' + '-' * 50)
        for u in DEMO_USERS:
            self.stdout.write(f"   {u['phone']} | {u['password']} | {u['role']}")
        self.stdout.write('')
        self.stdout.write('DJANGO ADMIN (/admin/ panel):')
        self.stdout.write(f"   Telefon: {DJANGO_ADMIN_PHONE}  Parol: {DJANGO_ADMIN_PASSWORD}")
        self.stdout.write('')
