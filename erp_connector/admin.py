from django.contrib import admin
from .models import ERPSyncLog

@admin.register(ERPSyncLog)
class ERPSyncLogAdmin(admin.ModelAdmin):
    list_display = ("action", "shopify_id", "success", "created_at")
    list_filter = ("action", "success")