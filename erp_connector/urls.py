from django.urls import path
from . import views

urlpatterns = [
    path("test-connection/", views.test_erp_connection),
    path("products/", views.get_verial_products),
    path("stock/", views.get_verial_stock),
]