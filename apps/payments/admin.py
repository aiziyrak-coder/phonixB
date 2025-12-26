from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'currency', 'service_type', 'status', 'created_at']
    list_filter = ['status', 'service_type', 'created_at']
    search_fields = ['user__email', 'user__phone', 'click_trans_id']
    readonly_fields = ['created_at', 'completed_at']
    date_hierarchy = 'created_at'
