import logging
from .models import Order
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')


def sync_order_status():
    """Consulta estado de pedidos en Verial y actualiza en Django"""
    
    # Solo pedidos enviados a Verial que no estén completados
    orders = Order.objects.filter(
        sent_to_verial=True,
        fulfillment_status__in=['', 'unfulfilled', 'partial']
    ).exclude(
        verial_status='4'  # 4 = Enviado (estado final)
    )
    
    if not orders.exists():
        return True, {"message": "No hay pedidos pendientes de actualizar"}
    
    client = VerialClient()
    
    if not client.is_configured():
        return False, {"error": "Verial no configurado"}
    
    # Preparar lista de pedidos a consultar
    pedidos_consulta = []
    for order in orders:
        pedidos_consulta.append({
            "Referencia": order.name[:40]
        })
    
    success, result = client.get_order_status(pedidos_consulta)
    
    if not success:
        return False, {"error": result}
    
    # Actualizar estados
    actualizados = 0
    estados = result.get("Pedidos", [])
    
    # Mapeo de estados Verial
    ESTADO_MAP = {
        0: "no_existe",
        1: "recibido",
        2: "en_preparacion",
        3: "preparado",
        4: "enviado"
    }
    
    for estado in estados:
        referencia = estado.get("Referencia", "")
        verial_estado = estado.get("Estado", 0)
        
        order = orders.filter(name=referencia).first()
        if order:
            order.verial_status = str(verial_estado)
            
            # Si está enviado, marcar como fulfilled en Django
            if verial_estado == 4:
                order.fulfillment_status = "fulfilled"
            elif verial_estado in [2, 3]:
                order.fulfillment_status = "partial"
            
            order.save()
            actualizados += 1
            logger.info(f"Pedido {referencia}: estado {ESTADO_MAP.get(verial_estado, 'desconocido')}")
    
    return True, {
        "consultados": len(pedidos_consulta),
        "actualizados": actualizados
    }