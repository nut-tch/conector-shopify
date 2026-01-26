import logging
from decimal import Decimal
from datetime import datetime
from .models import Order, OrderLine, ProductMapping
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')


class OrderToVerialError(Exception):
    """Error al procesar pedido para Verial."""
    pass


def get_line_mapping(line: OrderLine) -> ProductMapping:
    """
    Obtiene el mapeo de Verial para una línea de pedido.
    Busca primero por SKU, luego por producto.
    """
    # Intentar por SKU si existe
    if line.sku:
        mapping = ProductMapping.objects.filter(verial_sku=line.sku).first()
        if mapping:
            return mapping
    
    # Intentar por producto asociado
    mapping = ProductMapping.objects.filter(product__title=line.product_title).first()
    if mapping:
        return mapping
    
    return None


def build_order_payload(order: Order) -> dict:
    """
    Construye el payload para enviar un pedido a Verial.
    """
    if not order.lines.exists():
        raise OrderToVerialError(f"Pedido {order.name} sin líneas")
    
    contenido = []
    productos_sin_mapear = []
    
    for line in order.lines.all():
        mapping = get_line_mapping(line)
        
        if not mapping:
            productos_sin_mapear.append(f"{line.product_title} (SKU: {line.sku or 'N/A'})")
            continue
        
        contenido.append({
            "TipoRegistro": 1,
            "ID_Articulo": mapping.verial_id,
            "Uds": line.quantity,
            "Precio": float(line.price),
            "Dto": 0,
            "PorcentajeIVA": 21.0,
        })
    
    if productos_sin_mapear:
        raise OrderToVerialError(
            f"Productos sin mapear: {', '.join(productos_sin_mapear)}"
        )
    
    if not contenido:
        raise OrderToVerialError(f"Pedido {order.name} sin productos válidos")
    
    # Calcular base imponible (total sin IVA)
    base_imponible = Decimal(str(order.total_price)) / Decimal("1.21")
    
    payload = {
        "Tipo": 5,  # Pedido
        "Referencia": order.name,
        "Fecha": order.created_at.strftime("%Y-%m-%d"),
        "ID_Cliente": None,  # TODO: Mapeo de clientes
        "PreciosImpIncluidos": True,
        "BaseImponible": float(base_imponible.quantize(Decimal("0.01"))),
        "TotalImporte": float(order.total_price),
        "Comentario": f"Pedido Shopify {order.name}",
        "Contenido": contenido,
        "Pagos": [{
            "ID_MetodoPago": 1,
            "Fecha": datetime.now().strftime("%Y-%m-%d"),
            "Importe": float(order.total_price),
        }],
    }
    
    return payload


def send_order_to_verial(order: Order) -> tuple[bool, str]:
    """
    Envía un pedido a Verial.
    
    Returns:
        (success, message)
    """
    try:
        payload = build_order_payload(order)
    except OrderToVerialError as e:
        logger.error(f"Error construyendo pedido {order.name}: {e}")
        return False, str(e)
    
    client = VerialClient()
    
    if not client.is_configured():
        return False, "Verial no configurado"
    
    success, result = client.create_order(payload)
    
    if success:
        logger.info(f"Pedido {order.name} enviado a Verial")
        return True, f"Pedido {order.name} enviado correctamente"
    else:
        logger.error(f"Error enviando {order.name} a Verial: {result}")
        return False, result


def send_order_by_id(order_id: int) -> tuple[bool, str]:
    """
    Envía un pedido a Verial por su ID de Django.
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return False, f"Pedido {order_id} no encontrado"
    
    return send_order_to_verial(order)


def send_order_by_shopify_id(shopify_id: int) -> tuple[bool, str]:
    """
    Envía un pedido a Verial por su ID de Shopify.
    """
    try:
        order = Order.objects.get(shopify_id=shopify_id)
    except Order.DoesNotExist:
        return False, f"Pedido Shopify {shopify_id} no encontrado"
    
    return send_order_to_verial(order)