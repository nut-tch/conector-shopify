import logging
from shopify_app.models import Order, OrderMapping
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')

ESTADO_MAP = {
    0: "no_existe",
    1: "recibido",
    2: "en_preparacion",
    3: "preparado",
    4: "enviado"
}

def sync_order_status():
    """
    Sincroniza los estados de los pedidos desde Verial hacia Django/Shopify.
    Este proceso lo corre el sync_runner cada 5 minutos.
    """
    mappings = OrderMapping.objects.select_related('order').exclude(
        order__status='COMPLETED'
    )
    
    if not mappings.exists():
        return True, {"actualizados": 0, "message": "No hay pedidos pendientes"}

    client = VerialClient()
    mappings_list = list(mappings)
    total_actualizados = 0
    
    batch_size = 25
    for i in range(0, len(mappings_list), batch_size):
        lote = mappings_list[i:i+batch_size]
        pedidos_consulta = [{"Id": m.verial_id} for m in lote]
        
        success, result = client.get_orders_status(pedidos_consulta)
        if not success:
            logger.error(f"Error consultando estados: {result}")
            continue

        estados_verial = result.get("Pedidos", [])
        mapping_dict = {m.verial_id: m for m in lote}
        
        for estado_data in estados_verial:
            v_id = estado_data.get("Id")
            verial_estado = estado_data.get("Estado", 0)
            
            mapping = mapping_dict.get(v_id)
            if not mapping:
                continue
                
            order = mapping.order
            new_status_str = str(verial_estado)
            
            if order.verial_status != new_status_str:
                order.verial_status = new_status_str
                
                if verial_estado == 4: 
                    order.status = "COMPLETED"
                    order.fulfillment_status = "fulfilled"
                elif verial_estado in [2, 3]:
                    order.status = "IN_PROGRESS"
                    order.fulfillment_status = "partial"
                
                order.save(update_fields=['verial_status', 'status', 'fulfillment_status'])
                total_actualizados += 1
                
                logger.info(f"ORDEN {order.name}: Estado Verial actualizado a {ESTADO_MAP.get(verial_estado)}")

    return True, {"actualizados": total_actualizados}

def sync_single_order(order: Order):
    """Permite forzar la actualización de un solo pedido (ej. desde un botón en Admin)"""
    mapping = OrderMapping.objects.filter(order=order).first()
    if not mapping:
        return False, "Pedido no vinculado a Verial"
    
    client = VerialClient()
    success, result = client.get_orders_status([{"Id": mapping.verial_id}])
    
    if success and result.get("Pedidos"):
        verial_estado = result["Pedidos"][0].get("Estado", 0)
        order.verial_status = str(verial_estado)
        
        if verial_estado == 4:
            order.status = "COMPLETED"
            order.fulfillment_status = "fulfilled"
        elif verial_estado in [2, 3]:
            order.fulfillment_status = "partial"
            
        order.save()
        return True, ESTADO_MAP.get(verial_estado, "desconocido")
    
    return False, "No se pudo obtener respuesta del ERP"