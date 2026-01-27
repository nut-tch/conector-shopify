import logging
from decimal import Decimal
from datetime import datetime
from .models import Order, OrderLine, ProductMapping, ProductVariant, Customer
from .services.customer_sync import ensure_customer_in_verial
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')


class OrderToVerialError(Exception):
    pass


def get_line_mapping(line: OrderLine) -> ProductMapping:
    if line.sku:
        variant = ProductVariant.objects.filter(barcode=line.sku).first()
        if variant and hasattr(variant, 'verial_mapping'):
            return variant.verial_mapping
    
    variant = ProductVariant.objects.filter(product__title=line.product_title).first()
    if variant and hasattr(variant, 'verial_mapping'):
        return variant.verial_mapping
    
    return None


def build_order_payload(order: Order, id_cliente: int) -> dict:
    if not order.lines.exists():
        raise OrderToVerialError(f"Pedido {order.name} sin líneas")
    
    # Construir líneas
    contenido = []
    productos_sin_mapear = []
    
    for line in order.lines.all():
        mapping = get_line_mapping(line)
        
        if not mapping:
            productos_sin_mapear.append(f"{line.product_title} (SKU: {line.sku or 'N/A'})")
            continue
        
        precio = float(line.price)
        cantidad = line.quantity
        importe_linea = round(precio * cantidad, 2)
        
        contenido.append({
            "TipoRegistro": 1,
            "ID_Articulo": mapping.verial_id,
            "Uds": cantidad,
            "Precio": precio,
            "Dto": 0,
            "PorcentajeIVA": 21.0,
            "ImporteLinea": importe_linea,
        })
    
    if productos_sin_mapear:
        raise OrderToVerialError(
            f"Productos sin mapear: {', '.join(productos_sin_mapear)}"
        )
    
    if not contenido:
        raise OrderToVerialError(f"Pedido {order.name} sin productos válidos")
    
    # Calcular base imponible (total sin IVA)
    total = Decimal(str(order.total_price))
    base_imponible = total / Decimal("1.21")
    
    payload = {
        "Tipo": 5,
        "Referencia": order.name[:40],
        "Fecha": order.created_at.strftime("%Y-%m-%d"),
        "ID_Cliente": id_cliente,
        "PreciosImpIncluidos": True,
        "BaseImponible": float(base_imponible.quantize(Decimal("0.01"))),
        "TotalImporte": float(total),
        "Comentario": f"Pedido Shopify {order.name}",
        "Contenido": contenido,
        "Pagos": [],
    }
    
    return payload


def send_order_to_verial(order: Order) -> tuple[bool, str]:
    # Paso 1: Asegurar que el cliente existe en Verial
    success, id_cliente = ensure_customer_in_verial(order)
    
    if not success or not id_cliente:
        return False, f"No se pudo obtener/crear cliente en Verial para {order.email}"
    
    # Paso 2: Construir payload del pedido
    try:
        payload = build_order_payload(order, id_cliente)
    except OrderToVerialError as e:
        logger.error(f"Error construyendo pedido {order.name}: {e}")
        return False, str(e)
    
    # Paso 3: Enviar pedido
    client = VerialClient()
    
    if not client.is_configured():
        return False, "Verial no configurado"
    
    success, result = client.create_order(payload)
    
    if success:
        logger.info(f"Pedido {order.name} enviado a Verial con cliente {id_cliente}")
        return True, f"Pedido {order.name} enviado correctamente"
    else:
        logger.error(f"Error enviando {order.name} a Verial: {result}")
        return False, result


def send_order_by_id(order_id: int) -> tuple[bool, str]:
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return False, f"Pedido {order_id} no encontrado"
    
    return send_order_to_verial(order)


def send_order_by_shopify_id(shopify_id: int) -> tuple[bool, str]:
    try:
        order = Order.objects.get(shopify_id=shopify_id)
    except Order.DoesNotExist:
        return False, f"Pedido Shopify {shopify_id} no encontrado"
    
    return send_order_to_verial(order)