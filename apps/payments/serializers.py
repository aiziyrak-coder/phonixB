from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'completed_at', 'user')
    
    def get_user_name(self, obj):
        return obj.user.get_full_name()


class CreateTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('article', 'translation_request', 'amount', 'currency', 'service_type')
        extra_kwargs = {
            'article': {'required': False, 'allow_null': True},
            'translation_request': {'required': False, 'allow_null': True},
            'currency': {'required': False},
            'amount': {'required': True},
            'service_type': {'required': True},
        }
    
    def validate(self, attrs):
        """Set default currency if not provided"""
        if 'currency' not in attrs or not attrs['currency']:
            attrs['currency'] = 'UZS'
        return attrs
