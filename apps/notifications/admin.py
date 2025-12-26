from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'read', 'created_at']
    list_filter = ['read', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'message']
