from django.core.management.base import BaseCommand, CommandError
from apps.users.models import User


class Command(BaseCommand):
    help = 'Test userlarni yaratish - Admin, Editor, Reviewer, Author, Accountant'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Barcha test userlarni o\'chirib, qayta yaratish',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        
        test_users = [
            {
                'phone': '998901001001',
                'email': 'admin@ilmiyfaoliyat.uz',
                'first_name': 'Admin',
                'last_name': 'Bosh',
                'patronymic': 'Superuser',
                'role': 'super_admin',
                'affiliation': 'Phoenix Scientific Platform',
                'password': 'Admin@123456',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'phone': '998901001002',
                'email': 'editor@ilmiyfaoliyat.uz',
                'first_name': 'Tahrirchi',
                'last_name': 'Bosh',
                'patronymic': 'Admin',
                'role': 'journal_admin',
                'affiliation': 'Phoenix Scientific Platform',
                'password': 'Editor@123456',
                'is_staff': True,
                'is_superuser': False,
            },
            {
                'phone': '998901001003',
                'email': 'reviewer1@ilmiyfaoliyat.uz',
                'first_name': 'Reviewer',
                'last_name': 'Birinchi',
                'patronymic': 'Ilmiy',
                'role': 'reviewer',
                'affiliation': 'Tashkent State University',
                'password': 'Reviewer@123456',
                'is_staff': False,
                'is_superuser': False,
                'specializations': ['Computer Science', 'Information Technology'],
            },
            {
                'phone': '998901001004',
                'email': 'reviewer2@ilmiyfaoliyat.uz',
                'first_name': 'Reviewer',
                'last_name': 'Ikkinchi',
                'patronymic': 'Ilmiy',
                'role': 'reviewer',
                'affiliation': 'National University of Uzbekistan',
                'password': 'Reviewer@123456',
                'is_staff': False,
                'is_superuser': False,
                'specializations': ['Mathematics', 'Physics'],
            },
            {
                'phone': '998901001005',
                'email': 'author1@ilmiyfaoliyat.uz',
                'first_name': 'Muallif',
                'last_name': 'Birinchi',
                'patronymic': 'Ilmiy',
                'role': 'author',
                'affiliation': 'Tashkent Institute of Technology',
                'password': 'Author@123456',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'phone': '998901001006',
                'email': 'accountant@ilmiyfaoliyat.uz',
                'first_name': 'Buxgalter',
                'last_name': 'Bosh',
                'patronymic': 'Moliyaviy',
                'role': 'accountant',
                'affiliation': 'Phoenix Scientific Platform',
                'password': 'Accountant@123456',
                'is_staff': True,
                'is_superuser': False,
            },
        ]

        created_count = 0
        existing_count = 0
        
        for user_data in test_users:
            phone = user_data['phone']
            email = user_data['email']
            password = user_data.pop('password')
            
            try:
                if User.objects.filter(phone=phone).exists():
                    if reset:
                        # Delete and recreate
                        user = User.objects.get(phone=phone)
                        user.delete()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'♻️  Qayta yaratildi: {email} ({user_data["role"]})'
                            )
                        )
                        user = User.objects.create_user(
                            phone=phone,
                            email=email,
                            password=password,
                            **user_data
                        )
                        user.save()
                        created_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'⚠️  Mavjud: {email} ({user_data["role"]})'
                            )
                        )
                        existing_count += 1
                else:
                    # Create new user
                    user = User.objects.create_user(
                        phone=phone,
                        email=email,
                        password=password,
                        **user_data
                    )
                    
                    # Set gamification
                    if user.role == 'author':
                        user.gamification_badges = ['Yangi Muallif']
                    elif user.role == 'reviewer':
                        user.gamification_badges = ['Yangi Reviewer']
                    else:
                        user.gamification_badges = ['Administrator']
                        user.gamification_points = 1000
                    
                    user.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Yaratildi: {email} ({user.role})\n'
                            f'   Password: {password}\n'
                            f'   Phone: {phone}'
                        )
                    )
                    created_count += 1
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Xatolik: {email} - {str(e)}')
                )
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Mustavoyd yaratilngani:\n'
                f'   Yangi userlar: {created_count}\n'
                f'   Mavjud userlar: {existing_count}'
            )
        )
        self.stdout.write('='*60)
        
        # Print login info
        self.stdout.write('\n🔐 LOGIN CREDENTIALS:\n')
        for user_data in test_users:
            self.stdout.write(
                f"{user_data['email']}\n"
                f"  Role: {user_data['role']}\n"
            )
