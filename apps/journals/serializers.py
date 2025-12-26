from rest_framework import serializers
from .models import Journal, JournalCategory, Issue


class JournalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalCategory
        fields = '__all__'


class IssueSerializer(serializers.ModelSerializer):
    journal_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Issue
        fields = '__all__'
    
    def get_journal_name(self, obj):
        return obj.journal.name


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
