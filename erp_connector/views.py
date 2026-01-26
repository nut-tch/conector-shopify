from django.http import JsonResponse
from .models import ERPSyncLog
from .verial_client import VerialClient


def test_erp_connection(request):
    """Endpoint para probar la conexión con Verial."""
    client = VerialClient()
    
    if not client.is_configured():
        return JsonResponse({
            "status": "no_configurado",
            "message": "Añade VERIAL_SERVER y VERIAL_SESSION en .env"
        })
    
    success, result = client.test_connection()
    
    return JsonResponse({
        "status": "ok" if success else "error",
        "message": result
    })


def get_verial_products(request):
    """Obtener productos de Verial."""
    client = VerialClient()
    
    if not client.is_configured():
        return JsonResponse({"error": "Verial no configurado"}, status=400)
    
    success, result = client.get_products()
    
    if success:
        products = result.get("Articulos", [])
        return JsonResponse({
            "count": len(products),
            "products": products[:50]
        })
    
    return JsonResponse({"error": result}, status=500)


def get_verial_stock(request):
    """Obtener stock de Verial."""
    client = VerialClient()
    
    if not client.is_configured():
        return JsonResponse({"error": "Verial no configurado"}, status=400)
    
    success, result = client.get_stock()
    
    if success:
        stock = result.get("Stock", [])
        return JsonResponse({
            "count": len(stock),
            "stock": stock[:50]
        })
    
    return JsonResponse({"error": result}, status=500)


def send_order_to_verial(order):
    """
    Enviar un pedido de Shopify a Verial.
    Retorna: (success, message, verial_id)
    """
    client = VerialClient()
    
    if not client.is_configured():
        ERPSyncLog.objects.create(
            action="error",
            shopify_id=order.shopify_id,
            erp_response="Verial no configurado",
            success=False
        )
        return False, "Verial no configurado", None
    
    # TODO: Implementar mapeo de datos
    ERPSyncLog.objects.create(
        action="order_sent",
        shopify_id=order.shopify_id,
        erp_response="Pendiente de mapeo de datos",
        success=False
    )
    
    return False, "Pendiente de implementar mapeo", None
