import logging
from ..models import Order, OrderMapping
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')

# Mapeo de estados Verial
ESTADO_MAP = {
    0: "no_existe",
    1: "recibido",
    2: "en_preparacion",
    3: "preparado",
    4: "enviado"
}


def sync_order_status():
    """
    Consulta estado de pedidos en Verial y actualiza en Django.
    
    Solo consulta pedidos que:
    - Tienen mapeo con Verial (OrderMapping)
    - No están completados (verial_status != '4')
    
    Returns:
        (True, dict) con estadísticas
        (False, dict) con error
    """
    # 1️⃣ Obtener pedidos con mapeo que no estén completados
    mappings = OrderMapping.objects.select_related('order').exclude(
        order__verial_status='4'
    )
    
    if not mappings.exists():
        return True, {"message": "No hay pedidos pendientes de actualizar"}

    client = VerialClient()
    if not client.is_configured():
        return False, {"error": "Verial no configurado"}

    # 2️⃣ Preparar lista de IDs para consultar (máx 25 por petición)
    mappings_list = list(mappings)
    total_actualizados = 0
    total_consultados = 0
    errores = []

    # Procesar en lotes de 25
    for i in range(0, len(mappings_list), 25):
        lote = mappings_list[i:i+25]
        pedidos_consulta = [{"Id": m.verial_id} for m in lote]
        
        success, result = client.get_orders_status(pedidos_consulta)
        
        if not success:
            errores.append(f"Lote {i//25 + 1}: {result}")
            continue

        total_consultados += len(pedidos_consulta)
        
        # 3️⃣ Procesar respuesta
        estados = result.get("Pedidos", [])
        
        # Crear dict de mapping por verial_id para búsqueda rápida
        mapping_dict = {m.verial_id: m for m in lote}
        
        for estado in estados:
            verial_id = estado.get("Id")
            verial_estado = estado.get("Estado", 0)
            
            mapping = mapping_dict.get(verial_id)
            if not mapping:
                continue
                
            order = mapping.order
            old_status = order.verial_status
            
            # Actualizar estado
            order.verial_status = str(verial_estado)
            
            # Actualizar fulfillment_status según estado Verial
            if verial_estado == 4:
                order.fulfillment_status = "fulfilled"
            elif verial_estado in [2, 3]:
                order.fulfillment_status = "partial"
            
            order.save()
            
            # Log si cambió el estado
            if old_status != str(verial_estado):
                logger.info(
                    f"Pedido {order.name} (Verial ID: {verial_id}): "
                    f"{ESTADO_MAP.get(int(old_status) if old_status else 0, 'desconocido')} → "
                    f"{ESTADO_MAP.get(verial_estado, 'desconocido')}"
                )
            
            total_actualizados += 1

    return True, {
        "total_pedidos": len(mappings_list),
        "consultados": total_consultados,
        "actualizados": total_actualizados,
        "errores": errores if errores else None
    }


def sync_single_order(order: Order):
    """
    Sincroniza el estado de un pedido específico.
    
    Args:
        order: Instancia de Order
        
    Returns:
        (True, estado) o (False, error)
    """
    if not hasattr(order, 'verial_mapping'):
        return False, "Pedido no tiene mapeo con Verial"
    
    mapping = order.verial_mapping
    
    client = VerialClient()
    if not client.is_configured():
        return False, "Verial no configurado"
    
    success, result = client.get_orders_status([{"Id": mapping.verial_id}])
    
    if not success:
        return False, result
    
    estados = result.get("Pedidos", [])
    if not estados:
        return False, "No se encontró el pedido en Verial"
    
    estado = estados[0]
    verial_estado = estado.get("Estado", 0)
    
    order.verial_status = str(verial_estado)
    if verial_estado == 4:
        order.fulfillment_status = "fulfilled"
    elif verial_estado in [2, 3]:
        order.fulfillment_status = "partial"
    order.save()
    
    return True, ESTADO_MAP.get(verial_estado, "desconocido")