from decimal import Decimal

from rest_framework import serializers
from .models import TranslationRequest


class TranslationRequestSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TranslationRequest
        fields = '__all__'
        read_only_fields = ('id', 'submission_date', 'author')
    
    def validate(self, attrs):
        """Muallif yuborgan cost ni e’tiborsiz qoldirib, so‘z soni va tariff bo‘yicha server hisoblaydi."""
        from apps.udc.services import get_service_amount

        instance = getattr(self, 'instance', None)
        wc = attrs.get('word_count')
        if wc is None and instance is not None:
            wc = instance.word_count
        wc = max(0, int(wc or 0))
        rate = float(get_service_amount('translation_per_word', 100))
        if instance is None or 'word_count' in attrs:
            attrs['cost'] = Decimal(str(int(wc * rate)))
        return attrs
    
    def get_author_name(self, obj):
        return obj.author.get_full_name()
    
    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name() if obj.reviewer else None
