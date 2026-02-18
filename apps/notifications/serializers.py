from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'user')

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else ''
