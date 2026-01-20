from django.contrib import admin
from django.urls import path, include
from shopify_app import views

urlpatterns = [
    path("health/", views.health_check),
    path("admin/", admin.site.urls),
    path("shopify/", include("shopify_app.urls")),
    path("erp/", include("erp_connector.urls")),
]
