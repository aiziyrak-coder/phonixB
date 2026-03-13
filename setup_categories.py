#!/usr/bin/env python
import os
import sys
import django

# Django sozlamalari
sys.path.append('/phonix/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.journals.models import ScientificField, JournalCategory

# Ilmiy sohalarni yaratish
scientific_fields = [
    "Pedagogika va ta'lim",
    "Psixologiya", 
    "Filologiya va tilshunoslik",
    "Tarix",
    "Falsafa",
    "Iqtisodiyot",
    "Menejment va biznes",
    "Huquq",
    "Siyosatshunoslik",
    "Sotsiologiya",
    "Axborot texnologiyalari (IT)",
    "Matematika",
    "Fizika",
    "Kimyo",
    "Bilogiya",
    "Tibbiyot",
    "Qishloq xo'jaligi",
    "Arxitektura va qurilish",
    "Transport va logistika",
    "San'at va madaniyat",
    "Jurnalistika va ommaviy kommunikatsiya",
    "Turizm va mehmondo'stlik",
    "Sport va jismoniy tarbiya",
    "Ekologiya va atrof-muhit muhofazasi",
    "Texnika fanlari",
    "Energetika",
    "Harbiy fanlar va xavfsizlik",
    "Dinshunoslik",
    "Gender tadqiqotlari",
    "Multidissiplinar (fanlararo) yo'nalishlar"
]

print("Ilmiy sohalarni yaratish...")
for field_name in scientific_fields:
    field, created = ScientificField.objects.get_or_create(
        name=field_name,
        defaults={'description': f'{field_name} sohasi'}
    )
    if created:
        print(f"  ✅ {field_name} yaratildi")
    else:
        print(f"  ℹ️ {field_name} allaqachon mavjud")

# Kategoriyalarni yaratish
categories = [
    "Mahalliy OAK jurnallari",
    "Xalqaro OAK jurnallari", 
    "Mahalliy jurnallar",
    "Xalqaro jurnallar",
    "Mahalliy konferensiyalar",
    "Xalqaro konferensiyalar",
    "Scopus jurnallari",
    "Scopus konferensiyalari"
]

print("\nKategoriyalarni yaratish...")
for cat_name in categories:
    category, created = JournalCategory.objects.get_or_create(
        name=cat_name,
        defaults={'description': f'{cat_name} kategoriyasi'}
    )
    if created:
        print(f"  ✅ {cat_name} yaratildi")
    else:
        print(f"  ℹ️ {cat_name} allaqachon mavjud")

print(f"\n🎉 Jami {ScientificField.objects.count()} ta ilmiy soha va {JournalCategory.objects.count()} ta kategoriya yaratildi!")
