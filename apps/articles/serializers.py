from rest_framework import serializers
from .models import Article, ArticleVersion, ActivityLog
from apps.users.serializers import UserSerializer


class ArticleVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleVersion
        fields = '__all__'


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivityLog
        fields = '__all__'
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'


class ArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    journal_name = serializers.SerializerMethodField()
    versions = ArticleVersionSerializer(many=True, read_only=True)
    activity_logs = ActivityLogSerializer(many=True, read_only=True)
    analytics = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = '__all__'
        read_only_fields = ('id', 'submission_date', 'views_count', 'downloads_count', 'citations_count')
    
    def get_author_name(self, obj):
        return obj.author.get_full_name()
    
    def get_journal_name(self, obj):
        return obj.journal.name
    
    def get_analytics(self, obj):
        return {
            'views': obj.views_count,
            'downloads': obj.downloads_count,
            'citations': obj.citations_count
        }


class CreateArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('title', 'abstract', 'keywords', 'journal', 'final_pdf_path', 
                  'additional_document_path', 'page_count', 'fast_track')
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['status'] = 'Draft'
        return super().create(validated_data)
