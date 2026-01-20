from django.contrib import admin
from .models import Shop, Order, Product

admin.site.register(Shop)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "total_price", "financial_status", "created_at")
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "vendor", "product_type", "status", "created_at")