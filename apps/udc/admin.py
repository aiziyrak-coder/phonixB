from django.contrib import admin
from .models import ServicePrice, UDKCertificate


@admin.register(ServicePrice)
class ServicePriceAdmin(admin.ModelAdmin):
    list_display = ('service_key', 'amount', 'currency', 'label', 'updated_at')
    search_fields = ('service_key', 'label')


@admin.register(UDKCertificate)
class UDKCertificateAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'udk_code', 'created_at')
    list_filter = ('udk_code',)
    search_fields = ('title', 'udk_code')
    raw_id_fields = ('user', 'transaction')
