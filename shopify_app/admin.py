from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from .models import Shop, Order, OrderLine, Product, ProductVariant, Customer, ProductMapping
from .views import sync_orders, sync_products, sync_customers

admin.site.site_header = "Nutricione"
admin.site.site_title = "Nutricione"
admin.site.index_title = "Panel de administración"

admin.site.register(Shop)


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    readonly_fields = ("shopify_id", "product_title", "variant_title", "sku", "quantity", "price", "line_total")
    can_delete = False

    def line_total(self, obj):
        return f"{obj.total} €"
    line_total.short_description = "Total"


class FinancialStatusFilter(admin.SimpleListFilter):
    title = 'Estado de pago'
    parameter_name = 'financial_status'

    def lookups(self, request, model_admin):
        return (
            ('paid', 'Pagado'),
            ('pending', 'Pendiente'),
            ('refunded', 'Reembolsado'),
            ('partially_refunded', 'Reembolso parcial'),
            ('voided', 'Anulado'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(financial_status=self.value())
        return queryset


class FulfillmentStatusFilter(admin.SimpleListFilter):
    title = 'Estado de envío'
    parameter_name = 'fulfillment_status'

    def lookups(self, request, model_admin):
        return (
            ('fulfilled', 'Enviado'),
            ('unfulfilled', 'No enviado'),
            ('partial', 'Parcialmente enviado'),
            ('', 'Sin estado'),
        )

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(fulfillment_status=self.value())
        return queryset


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "total_price", "financial_status", "fulfillment_status", "created_at")
    list_filter = (FinancialStatusFilter, FulfillmentStatusFilter, "created_at")
    search_fields = ("name", "email", "shopify_id")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    change_list_template = "admin/order_change_list.html"
    inlines = [OrderLineInline]

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
    list_filter = ("status", "vendor", "product_type")
    search_fields = ("title", "vendor", "shopify_id")
    ordering = ("-created_at",)
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
    list_display = ("full_name", "email", "phone", "orders_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("first_name", "last_name", "email", "phone", "shopify_id")
    ordering = ("-created_at",)
    change_list_template = "admin/customer_change_list.html"

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "Nombre completo"

    def orders_count(self, obj):
        return Order.objects.filter(email=obj.email).count()
    orders_count.short_description = "Nº Pedidos"

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

@admin.register(ProductMapping)
class ProductMappingAdmin(admin.ModelAdmin):
    list_display = ("variant", "verial_id", "verial_barcode", "last_sync")
    search_fields = ("variant__product__title", "variant__sku", "verial_id", "verial_barcode")
    autocomplete_fields = ["variant"]

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "title", "sku", "barcode", "price", "inventory_quantity")
    search_fields = ("product__title", "title", "sku", "barcode")
    list_filter = ("product__vendor",)