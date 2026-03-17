from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TranslationRequest
from .serializers import TranslationRequestSerializer
from apps.services import get_gemini_service


WORDS_PER_PAGE = 350


class TranslationRequestViewSet(viewsets.ModelViewSet):
    queryset = TranslationRequest.objects.all()
    serializer_class = TranslationRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['super_admin', 'reviewer']:
            return TranslationRequest.objects.all()
        return TranslationRequest.objects.filter(author=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['post'])
    def analyze_file(self, request):
        """Analyze a file to determine word count"""
        if 'file' not in request.FILES:
            return Response({'error': 'Fayl taqdim etilmadi'}, status=status.HTTP_400_BAD_REQUEST)
            
        file_obj = request.FILES['file']
        from math import ceil
        from apps.udc.services import get_service_amount

        try:
            import os
            from django.core.files.storage import default_storage
            
            # Save file temporarily
            tmp_path = default_storage.save(f'tmp/{file_obj.name}', file_obj)
            full_path = default_storage.path(tmp_path)
            
            try:
                # Use GeminiService to extract text
                gemini_service = get_gemini_service()
                text_content = gemini_service.extract_text_from_document(full_path)
                
                # Count words
                words = text_content.split()
                word_count = len(words)

                # Calculate cost based on pages using ServicePrice (translation_per_page)
                price_per_page = get_service_amount('translation_per_page', 50000)
                pages = max(1, ceil(max(word_count, 1) / float(WORDS_PER_PAGE)))
                cost = int(pages * price_per_page)

                return Response({
                    'word_count': word_count,
                    'cost': cost,
                    'text_preview': text_content[:500] if text_content else ""
                })
            finally:
                # Always clean up temp file
                if os.path.exists(full_path):
                    os.remove(full_path)
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[TRANSLATION] Error analyzing file: {str(e)}", exc_info=True)
            # Fallback to simple estimation if something fails
            file_size_kb = file_obj.size / 1024
            estimated_words = int(file_size_kb * 150)
            price_per_page = get_service_amount('translation_per_page', 50000)
            pages = max(1, ceil(max(estimated_words, 1) / float(WORDS_PER_PAGE)))
            fallback_cost = int(pages * price_per_page)
            return Response({
                'word_count': estimated_words,
                'cost': fallback_cost,
                'note': 'Taxminiy hisob-kitob qutqarildi.'
            })
