from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TranslationRequest
from .serializers import TranslationRequestSerializer
from apps.services import extract_plain_text_from_file


# Agar matn chiqarib bo‘lmasa: fayl hajmi asosida taxmin (DOCX siqilgan — eski 150 so‘z/KB noto‘g‘ri edi)
FALLBACK_WORDS_PER_KB = 18
MAX_FALLBACK_WORDS = 120_000


class TranslationRequestViewSet(viewsets.ModelViewSet):
    queryset = TranslationRequest.objects.all()
    serializer_class = TranslationRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        role = getattr(self.request.user, 'role', None) if self.request.user.is_authenticated else None
        if isinstance(role, str):
            role = role.strip().lower()
        if role in ('super_admin', 'reviewer'):
            return TranslationRequest.objects.select_related('author', 'reviewer').all()
        return TranslationRequest.objects.select_related('author', 'reviewer').filter(
            author=self.request.user
        )
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['post'])
    def analyze_file(self, request):
        """Analyze a file to determine word count"""
        if 'file' not in request.FILES:
            return Response({'error': 'Fayl taqdim etilmadi'}, status=status.HTTP_400_BAD_REQUEST)
            
        file_obj = request.FILES['file']
        from apps.udc.services import get_service_amount

        try:
            import os
            from django.core.files.storage import default_storage
            
            # Save file temporarily
            tmp_path = default_storage.save(f'tmp/{file_obj.name}', file_obj)
            full_path = default_storage.path(tmp_path)
            
            try:
                # Gemini talab qilinmaydi — DOCX/PDF dan to‘g‘ridan-to‘g‘ri matn (noto‘g‘ri taxmin oldini olish uchun)
                text_content = extract_plain_text_from_file(full_path)

                # Count words (Unicode so‘zlar uchun bo‘shliq bilan ajratish)
                words = text_content.split()
                word_count = len(words)
                estimate_note = None

                # Matn bo‘sh bo‘lsa — konservativ taxmin (eski: file_kb * 150 juda yuqori chiqardi)
                if word_count == 0:
                    file_size_kb = max(file_obj.size / 1024, 0.001)
                    word_count = min(
                        max(int(file_size_kb * FALLBACK_WORDS_PER_KB), 50),
                        MAX_FALLBACK_WORDS,
                    )
                    estimate_note = (
                        'Hujjatdan matn ajratilmadi; fayl hajmi bo‘yicha taxminiy so‘zlar soni ishlatildi.'
                    )

                # Narx: har bir so‘z (ServicePrice: translation_per_word, default 100 so‘m)
                price_per_word = int(get_service_amount('translation_per_word', 100))
                cost = int(max(word_count, 0) * price_per_word)

                payload = {
                    'word_count': word_count,
                    'cost': cost,
                    'price_per_word': price_per_word,
                    'text_preview': (text_content[:500] if text_content else ''),
                }
                if estimate_note:
                    payload['note'] = estimate_note
                return Response(payload)
            finally:
                # Always clean up temp file
                if os.path.exists(full_path):
                    os.remove(full_path)
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[TRANSLATION] Error analyzing file: {str(e)}", exc_info=True)
            file_size_kb = max(file_obj.size / 1024, 0.001)
            estimated_words = min(
                max(int(file_size_kb * FALLBACK_WORDS_PER_KB), 50),
                MAX_FALLBACK_WORDS,
            )
            price_per_word = int(get_service_amount('translation_per_word', 100))
            fallback_cost = int(max(estimated_words, 0) * price_per_word)
            return Response({
                'word_count': estimated_words,
                'cost': fallback_cost,
                'price_per_word': price_per_word,
                'note': 'Taxminiy hisob-kitob (fayl vaqtincha saqlanmadi). Iltimos, qayta urinib ko‘ring.',
            })
