import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import Order, OrderLine, ProductVariant, OrderMapping
from .services.customer_sync import ensure_customer_in_verial
from erp_connector.verial_client import VerialClient

logger = logging.getLogger("verial")


class OrderToVerialError(Exception):
    pass


def get_line_mapping(line: OrderLine):
    """Obtiene el mapeo de Verial para una línea de pedido."""
    if line.sku:
        variant = ProductVariant.objects.filter(sku=line.sku).first()
        if variant and hasattr(variant, "verial_mapping"):
            return variant.verial_mapping

    variant = ProductVariant.objects.filter(product__title=line.product_title).first()
    if variant and hasattr(variant, "verial_mapping"):
        return variant.verial_mapping

    return None


def build_order_payload(order: Order, id_cliente: int) -> dict:
    """
    Construye el payload para enviar a Verial.
    
    IMPORTANTE: No incluir 'ImporteLinea' en las líneas.
    """
    if not order.lines.exists():
        raise OrderToVerialError("Pedido sin líneas")

    contenido = []
    for line in order.lines.all():
        mapping = get_line_mapping(line)
        if not mapping:
            raise OrderToVerialError(
                f"Producto sin mapear: {line.product_title}"
            )

        precio = float(line.price)
        cantidad = line.quantity

        contenido.append({
            "TipoRegistro": 1,
            "ID_Articulo": mapping.verial_id,
            "Uds": cantidad,
            "Precio": precio,
            "Dto": 0,
            "PorcentajeIVA": 21
            # NO incluir ImporteLinea - Verial lo calcula
        })

    total = Decimal(order.total_price)
    base = (total / Decimal("1.21")).quantize(Decimal("0.01"))
    
    # Referencia única para identificar el pedido
    referencia = f"SHOP-{order.shopify_id}"

    return {
        "Tipo": 5,
        "Referencia": referencia,
        "Fecha": order.created_at.strftime("%Y-%m-%d"),
        "ID_Cliente": id_cliente,
        "PreciosImpIncluidos": True,
        "BaseImponible": float(base),
        "TotalImporte": float(total),
        "Comentario": f"Pedido Shopify {order.name}",
        "Contenido": contenido,
        "Pagos": []
    }


def send_order_to_verial(order: Order):
    """
    Envía un pedido a Verial y guarda el mapeo.
    
    Returns:
        (True, "Pedido enviado") en caso de éxito
        (False, "mensaje de error") en caso de error
    """
    # 1️⃣ Asegurar cliente en Verial
    ok, id_cliente = ensure_customer_in_verial(order)
    if not ok:
        return False, id_cliente

    # 2️⃣ Construir payload
    try:
        payload = build_order_payload(order, id_cliente)
    except OrderToVerialError as e:
        return False, str(e)
    except Exception as e:
        logger.error(f"Error construyendo payload: {e}")
        return False, str(e)

    # 3️⃣ Enviar a Verial
    client = VerialClient()
    success, response = client.create_order(payload)

    if success:
        # 4️⃣ GUARDAR MAPEO
        verial_id = response.get("Id")
        verial_numero = str(response.get("Numero", ""))
        
        if verial_id:
            OrderMapping.objects.update_or_create(
                order=order,
                defaults={
                    "verial_id": verial_id,
                    "verial_referencia": payload["Referencia"],
                    "verial_numero": verial_numero
                }
            )
            logger.info(
                f"Pedido {order.name} enviado a Verial: "
                f"ID={verial_id}, Numero={verial_numero}"
            )
        else:
            logger.warning(
                f"Pedido {order.name} enviado pero sin ID en respuesta: {response}"
            )
        
        # 5️⃣ Actualizar estado del pedido
        order.sent_to_verial = True
        order.sent_to_verial_at = timezone.now()
        order.verial_error = ""
        order.save()
        
        return True, "Pedido enviado"
    else:
        # Error al enviar
        order.verial_error = str(response)[:500]
        order.save()
        logger.error(f"Error enviando pedido {order.name}: {response}")
        return False, response