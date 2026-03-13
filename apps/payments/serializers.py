from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    udk_certificate_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'completed_at', 'user')
    
    def get_user_name(self, obj):
        return obj.user.get_full_name()
    
    def get_udk_certificate_url(self, obj):
        if getattr(obj, 'service_type', None) != 'udk_request' or not obj.article_id:
            return None
        article = getattr(obj, 'article', None)
        if not article or not article.udk_certificate_path:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(article.udk_certificate_path.url)
        from django.conf import settings
        base = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/')
        path = str(article.udk_certificate_path).lstrip('/')
        return f"{base}/{path}" if path else None


class CreateTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('article', 'translation_request', 'amount', 'currency', 'service_type', 'extra_data')
        extra_kwargs = {
            'article': {'required': False, 'allow_null': True},
            'translation_request': {'required': False, 'allow_null': True},
            'currency': {'required': False},
            'amount': {'required': True},
            'service_type': {'required': True},
            'extra_data': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        """Set default currency if not provided"""
        if 'currency' not in attrs or not attrs['currency']:
            attrs['currency'] = 'UZS'
        if 'extra_data' not in attrs:
            attrs['extra_data'] = {}
        return attrs
