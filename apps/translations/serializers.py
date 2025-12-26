from rest_framework import serializers
from .models import TranslationRequest


class TranslationRequestSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TranslationRequest
        fields = '__all__'
        read_only_fields = ('id', 'submission_date', 'author')
    
    def get_author_name(self, obj):
        return obj.author.get_full_name()
    
    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name() if obj.reviewer else None
