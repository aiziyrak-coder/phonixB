from django.core.management.base import BaseCommand, CommandError
from apps.users.models import User


class Command(BaseCommand):
    help = 'Barcha userlarni o\'chirib, har bir rol uchun 1ta demo user yaratish'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Barcha userlarni o\'chirib, qayta yaratish (default behavior)',
        )

    def handle(self, *args, **options):
        # 1. BARCHA userlarni o'chirish
        total_deleted = User.objects.count()
        User.objects.all().delete()
        self.stdout.write(
            self.style.WARNING(f'🗑️  {total_deleted} ta user o\'chirildi.')
        )

        # 2. Har bir rol uchun 1ta demo user
        demo_users = [
            {
                'phone': '998901001001',
                'email': 'admin@phoenix.uz',
                'first_name': 'Adminjon',
                'last_name': 'Boshqaruvov',
                'patronymic': 'Superovich',
                'role': 'super_admin',
                'affiliation': 'Phoenix Scientific Platform',
                'password': 'Demo@admin1',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'phone': '998901001002',
                'email': 'editor@phoenix.uz',
                'first_name': 'Tahrirjon',
                'last_name': 'Jurnalbekov',
                'patronymic': 'Adminovich',
                'role': 'journal_admin',
                'affiliation': 'Phoenix Scientific Platform',
                'password': 'Demo@editor1',
                'is_staff': True,
                'is_superuser': False,
            },
            {
                'phone': '998901001003',
                'email': 'reviewer@phoenix.uz',
                'first_name': 'Taqrizjon',
                'last_name': 'Ilmiyev',
                'patronymic': 'Reviewerovich',
                'role': 'reviewer',
                'affiliation': 'Toshkent Davlat Universiteti',
                'password': 'Demo@review1',
                'is_staff': False,
                'is_superuser': False,
                'specializations': ['Computer Science', 'Mathematics'],
            },
            {
                'phone': '998901001004',
                'email': 'author@phoenix.uz',
                'first_name': 'Muallifjon',
                'last_name': 'Yozuvchiev',
                'patronymic': 'Ilmiyovich',
                'role': 'author',
                'affiliation': 'Toshkent Axborot Texnologiyalari Universiteti',
                'password': 'Demo@author1',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'phone': '998901001005',
                'email': 'accountant@phoenix.uz',
                'first_name': 'Buxgalterjon',
                'last_name': 'Moliyaev',
                'patronymic': 'Hisobovich',
                'role': 'accountant',
                'affiliation': 'Phoenix Scientific Platform',
                'password': 'Demo@account1',
                'is_staff': True,
                'is_superuser': False,
            },
        ]

        created_count = 0

        for user_data in demo_users:
            password = user_data.pop('password')
            phone = user_data['phone']
            email = user_data['email']

            try:
                user = User.objects.create_user(
                    phone=phone,
                    password=password,
                    **{k: v for k, v in user_data.items() if k != 'phone'}
                )

                # Gamification
                if user.role == 'author':
                    user.gamification_badges = ['Yangi Muallif']
                elif user.role == 'reviewer':
                    user.gamification_badges = ['Yangi Reviewer']
                    user.reviews_completed = 5
                else:
                    user.gamification_badges = ['Administrator']
                    user.gamification_points = 1000

                user.save()
                created_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ {user.role:15s} | {phone} | {password} | {email}'
                    )
                )
                # Put password back for summary
                user_data['password'] = password

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Xatolik: {email} - {str(e)}')
                )
                user_data['password'] = password

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS(f'✅ Jami {created_count} ta demo user yaratildi.'))
        self.stdout.write('=' * 70)

        self.stdout.write('\n🔐 DEMO LOGIN MA\'LUMOTLARI:\n')
        self.stdout.write(f'{"Rol":<17} {"Telefon":<15} {"Parol":<17} {"Email"}')
        self.stdout.write('-' * 70)
        for u in demo_users:
            self.stdout.write(
                f'{u["role"]:<17} {u["phone"]:<15} {u["password"]:<17} {u["email"]}'
            )
