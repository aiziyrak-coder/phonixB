from rest_framework import serializers
from .models import PeerReview


class PeerReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    article_title = serializers.SerializerMethodField()
    
    class Meta:
        model = PeerReview
        fields = '__all__'
        read_only_fields = ('id', 'assigned_at', 'reviewer')
    
    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name()
    
    def get_article_title(self, obj):
        return obj.article.title
