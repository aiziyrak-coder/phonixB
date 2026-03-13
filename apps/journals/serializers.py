from django.conf import settings
from rest_framework import serializers
from .models import Journal, JournalCategory, Issue


class JournalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalCategory
        fields = '__all__'


class IssueSerializer(serializers.ModelSerializer):
    journal_name = serializers.SerializerMethodField()
    articles = serializers.SerializerMethodField()
    collection_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = '__all__'
        extra_kwargs = {'collection_url': {'allow_blank': True, 'required': False}}

    def get_journal_name(self, obj):
        return obj.journal.name

    def get_articles(self, obj):
        """Article IDs in this issue (for author's To'plamlarim filter)."""
        return list(obj.articles.values_list('id', flat=True))

    def get_collection_file_url(self, obj):
        """Full URL to download the admin-uploaded collection file."""
        if not obj.collection_file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.collection_file.url)
        base = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/')
        return f"{base}{obj.collection_file.url}" if obj.collection_file.url else None


class JournalSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    admin_name = serializers.SerializerMethodField()
    issues = IssueSerializer(many=True, read_only=True)
    additional_document_config = serializers.SerializerMethodField()
    
    class Meta:
        model = Journal
        fields = '__all__'
    
    def get_category_name(self, obj):
        return obj.category.name
    
    def get_admin_name(self, obj):
        return obj.journal_admin.get_full_name()
    
    def get_additional_document_config(self, obj):
        if obj.additional_doc_required:
            return {
                'required': obj.additional_doc_required,
                'label': obj.additional_doc_label,
                'type': obj.additional_doc_type
            }
        return None
