from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health_check),
    path("install/", views.shopify_install),
    path("callback/", views.shopify_callback),
    path("orders/", views.orders_view),
]
