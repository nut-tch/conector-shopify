from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health_check),
    path("install/", views.shopify_install),
    path("callback/", views.shopify_callback),
    path("orders/", views.orders_view),
    path("sync-orders/", views.sync_orders),
    path("sync-products/", views.sync_products),
    path("sync-customers/", views.sync_customers),
    path("webhook/orders/create/", views.webhook_orders_create),
    path("register-webhook/", views.register_webhook),
    path("dashboard/", views.dashboard),
    path('map-products/', views.auto_map_products_view, name='auto_map_products'),
    path("sync-stock/", views.sync_stock_view, name="sync_stock"),
    path("test-locations/", views.test_locations_view, name="test_locations"),
]
