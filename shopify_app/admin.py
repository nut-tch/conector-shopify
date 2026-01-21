from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from .models import Shop, Order, Product, Customer
from .views import sync_orders, sync_products, sync_customers

admin.site.register(Shop)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "total_price", "financial_status", "created_at")
    change_list_template = "admin/order_change_list.html"
    ordering = ("-created_at",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("sync/", self.admin_site.admin_view(self.sync_view), name="sync_orders"),
        ]
        return custom_urls + urls

    def sync_view(self, request):
        sync_orders(request)
        self.message_user(request, "Pedidos sincronizados correctamente")
        return redirect("..")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "vendor", "product_type", "status", "created_at")
    change_list_template = "admin/product_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("sync/", self.admin_site.admin_view(self.sync_view), name="sync_products"),
        ]
        return custom_urls + urls

    def sync_view(self, request):
        sync_products(request)
        self.message_user(request, "Productos sincronizados correctamente")
        return redirect("..")

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone", "created_at")
    ordering = ("-created_at",)
    change_list_template = "admin/customer_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("sync/", self.admin_site.admin_view(self.sync_view), name="sync_customers"),
        ]
        return custom_urls + urls

    def sync_view(self, request):
        sync_customers(request)
        self.message_user(request, "Clientes sincronizados correctamente")
        return redirect("..")
