import logging
from decimal import Decimal
from datetime import datetime
from .models import Order, OrderLine, ProductMapping, ProductVariant, Customer, CustomerMapping
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


def build_customer_payload(order: Order) -> dict:
    # Obtener datos del cliente desde Customer si existe
    customer = Customer.objects.filter(email=order.email).first()
    
    if customer:
        nombre = customer.first_name or ""
        apellidos = (customer.last_name or "").split(" ", 1)
        apellido1 = apellidos[0] if apellidos else ""
        apellido2 = apellidos[1] if len(apellidos) > 1 else ""
        telefono = customer.phone or ""
    else:
        # Usar datos básicos del pedido
        nombre = order.email.split("@")[0] if order.email else "Cliente Web"
        apellido1 = ""
        apellido2 = ""
        telefono = ""
    
    return {
        "Tipo": 1,  # 1=Particular
        "NIF": "",
        "Nombre": nombre[:50],
        "Apellido1": apellido1[:50],
        "Apellido2": apellido2[:50],
        "RazonSocial": "",
        "ID_Pais": 1,  # España
        "Provincia": "",
        "Localidad": "",
        "CPostal": "",
        "Direccion": "",
        "Telefono": telefono[:20],
        "Email": order.email[:100] if order.email else "",
        "WebUser": order.email[:100] if order.email else "",
    }


def build_order_payload(order: Order) -> dict:
    if not order.lines.exists():
        raise OrderToVerialError(f"Pedido {order.name} sin líneas")
    
    # Verificar si el cliente ya tiene mapeo
    customer = Customer.objects.filter(email=order.email).first()
    id_cliente = None
    cliente_payload = None
    
    if customer and hasattr(customer, 'verial_mapping'):
        id_cliente = customer.verial_mapping.verial_id
    else:
        # Enviar cliente embebido para que Verial lo cree
        cliente_payload = build_customer_payload(order)
    
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
        "Tipo": 5,  # Pedido
        "Referencia": order.name[:40],
        "Fecha": order.created_at.strftime("%Y-%m-%d"),
        "PreciosImpIncluidos": True,
        "BaseImponible": float(base_imponible.quantize(Decimal("0.01"))),
        "TotalImporte": float(total),
        "Comentario": f"Pedido Shopify {order.name}",
        "Contenido": contenido,
        "Pagos": [],
    }
    
    # Cliente ya existe en Verial
    if id_cliente:
        payload["ID_Cliente"] = id_cliente
    # Cliente nuevo, enviar embebido
    elif cliente_payload:
        payload["Cliente"] = cliente_payload
    
    return payload


def save_customer_mapping(order: Order, verial_response: dict):
    # Guardar el mapeo del cliente si Verial devolvió ID
    customer = Customer.objects.filter(email=order.email).first()
    if not customer:
        return
    
    if hasattr(customer, 'verial_mapping'):
        return
    
    # Buscar ID del cliente en la respuesta
    cliente_data = verial_response.get("Cliente", {})
    verial_id = cliente_data.get("Id")
    
    if verial_id:
        CustomerMapping.objects.create(
            customer=customer,
            verial_id=verial_id,
        )
        logger.info(f"Cliente {customer.email} mapeado a Verial ID: {verial_id}")


def send_order_to_verial(order: Order) -> tuple[bool, str]:
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
        # Guardar mapeo del cliente si es nuevo
        save_customer_mapping(order, result)
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