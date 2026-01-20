import os
from django.http import JsonResponse
from .models import ERPSyncLog

# Credenciales ERP (se llenarán cuando las tengas)
ERP_URL = os.getenv("ERP_URL", "")
ERP_USER = os.getenv("ERP_USER", "")
ERP_PASSWORD = os.getenv("ERP_PASSWORD", "")


def send_order_to_erp(order):
    """
    Envía un pedido al ERP Verial.
    Por implementar cuando tengamos credenciales.
    """
    if not ERP_URL:
        return {"error": "ERP no configurado", "success": False}
    
    # TODO: Implementar llamada SOAP/REST al ERP
    # payload = {...}
    # response = requests.post(ERP_URL, ...)
    
    # Log temporal
    ERPSyncLog.objects.create(
        action="order_sent",
        shopify_id=order.get("id"),
        erp_response="Pendiente de implementar",
        success=False
    )
    
    return {"message": "Pendiente de implementar", "success": False}


def send_customer_to_erp(customer):
    """
    Envía un cliente al ERP Verial.
    Por implementar cuando tengamos credenciales.
    """
    if not ERP_URL:
        return {"error": "ERP no configurado", "success": False}
    
    # TODO: Implementar llamada SOAP/REST al ERP
    
    ERPSyncLog.objects.create(
        action="customer_sent",
        shopify_id=customer.get("id"),
        erp_response="Pendiente de implementar",
        success=False
    )
    
    return {"message": "Pendiente de implementar", "success": False}


def test_erp_connection(request):
    """
    Endpoint para probar la conexión con el ERP.
    """
    if not ERP_URL:
        return JsonResponse({
            "status": "no_configurado",
            "message": "Credenciales ERP pendientes"
        })
    
    # TODO: Implementar test de conexión
    
    return JsonResponse({
        "status": "pendiente",
        "message": "Test de conexión pendiente de implementar"
    })