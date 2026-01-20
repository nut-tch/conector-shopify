from django.urls import path
from . import views

urlpatterns = [
    path("test-connection/", views.test_erp_connection),
]