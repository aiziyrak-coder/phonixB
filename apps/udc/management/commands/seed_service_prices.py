"""
Barcha xizmatlar uchun boshlang'ich narxlarni yaratish.
python manage.py seed_service_prices
"""
from django.core.management.base import BaseCommand
from apps.udc.models import ServicePrice


class Command(BaseCommand):
    help = 'Barcha xizmatlar uchun boshlang\'ich narxlarni yaratish'

    def handle(self, *args, **kwargs):
        self.stdout.write('Xizmat narxlarini yaratish boshlandi...')
        
        # Barcha xizmatlar ro'yxati
        services = [
            # UDK xizmatlari
            {
                'service_key': 'udk_request',
                'label': 'UDK tasdiqlangan ma\'lumotnoma',
                'amount': 50000,
            },
            # Antiplagiat tekshiruv
            {
                'service_key': 'plagiarism_check',
                'label': 'Antiplagiat tekshiruv (to\'liq hisobot)',
                'amount': 30000,
            },
            # DOI raqami olish
            {
                'service_key': 'doi_request',
                'label': 'DOI raqami olish',
                'amount': 100000,
            },
            # Maqola namuna olish
            {
                'service_key': 'article_sample_quyi',
                'label': 'Maqola namuna olish (Quyi sifat)',
                'amount': 150000,
            },
            {
                'service_key': 'article_sample_orta',
                'label': 'Maqola namuna olish (O\'rta sifat)',
                'amount': 250000,
            },
            {
                'service_key': 'article_sample_yuqori',
                'label': 'Maqola namuna olish (Yuqori sifat)',
                'amount': 400000,
            },
            # Tarjima xizmatlari
            {
                'service_key': 'translation_per_page',
                'label': 'Tarjima xizmati (1 bet uchun)',
                'amount': 50000,
            },
            # Kitob nashr
            {
                'service_key': 'book_publication_base',
                'label': 'Kitob nashr qilish (Bazaviy narx)',
                'amount': 500000,
            },
            # Fast track
            {
                'service_key': 'fast_track',
                'label': 'Fast track (tezlashtirilgan ko\'rib chiqish)',
                'amount': 200000,
            },
            # Language editing
            {
                'service_key': 'language_editing',
                'label': 'Tahrir qilish xizmati',
                'amount': 100000,
            },
            # Publication fee
            {
                'service_key': 'publication_fee',
                'label': 'Nashr qilish to\'lovi',
                'amount': 150000,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for service_data in services:
            service_key = service_data['service_key']
            obj, created = ServicePrice.objects.update_or_create(
                service_key=service_key,
                defaults={
                    'label': service_data['label'],
                    'amount': service_data['amount'],
                    'currency': 'UZS',
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Yaratildi: {service_key} - {service_data["amount"]:,.0f} so\'m'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ Yangilandi: {service_key} - {service_data["amount"]:,.0f} so\'m'))
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Jami: {created_count} ta yaratildi, {updated_count} ta yangilandi'))
        self.stdout.write(self.style.SUCCESS('Xizmat narxlari muvaffaqiyatli yuklandi!'))
