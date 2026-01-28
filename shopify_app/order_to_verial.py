import logging
from decimal import Decimal
from django.conf import settings
from .models import Order, OrderLine, ProductVariant
from .services.customer_sync import ensure_customer_in_verial
from erp_connector.verial_client import VerialClient

logger = logging.getLogger("verial")


class OrderToVerialError(Exception):
    pass


def get_line_mapping(line: OrderLine):
    if line.sku:
        variant = ProductVariant.objects.filter(sku=line.sku).first()
        if variant and hasattr(variant, "verial_mapping"):
            return variant.verial_mapping

    variant = ProductVariant.objects.filter(product__title=line.product_title).first()
    if variant and hasattr(variant, "verial_mapping"):
        return variant.verial_mapping

    return None


def build_order_payload(order: Order, id_cliente: int) -> dict:
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
            "PorcentajeIVA": 21,
            "ImporteLinea": round(precio * cantidad, 2),
        })

    total = Decimal(order.total_price)
    base = (total / Decimal("1.21")).quantize(Decimal("0.01"))

    return {
        "Tipo": 5,
        "Referencia": f"SHOP-{order.shopify_id}",  # ⚠️ CLAVE
        "Fecha": order.created_at.strftime("%Y-%m-%d"),
        "ID_Cliente": id_cliente,
        "PreciosImpIncluidos": True,
        "BaseImponible": float(base),
        "TotalImporte": float(total),
        "Comentario": f"Pedido Shopify {order.name}",
        "Contenido": contenido,
        "Pagos": [],
    }


def send_order_to_verial(order: Order):
    # 1️⃣ Cliente
    ok, id_cliente = ensure_customer_in_verial(order)
    if not ok:
        return False, id_cliente

    # 2️⃣ Pedido
    try:
        payload = build_order_payload(order, id_cliente)
    except Exception as e:
        return False, str(e)

    # 3️⃣ Envío
    client = VerialClient()
    success, response = client.create_order(payload)

    if success:
        return True, "Pedido enviado"
    else:
        return False, response
import logging
from decimal import Decimal
from django.conf import settings
from .models import Order, OrderLine, ProductVariant
from .services.customer_sync import ensure_customer_in_verial
from erp_connector.verial_client import VerialClient

logger = logging.getLogger("verial")


class OrderToVerialError(Exception):
    pass


def get_line_mapping(line: OrderLine):
    if line.sku:
        variant = ProductVariant.objects.filter(sku=line.sku).first()
        if variant and hasattr(variant, "verial_mapping"):
            return variant.verial_mapping

    variant = ProductVariant.objects.filter(product__title=line.product_title).first()
    if variant and hasattr(variant, "verial_mapping"):
        return variant.verial_mapping

    return None


def build_order_payload(order: Order, id_cliente: int) -> dict:
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
            "PorcentajeIVA": 21,
            "ImporteLinea": round(precio * cantidad, 2),
        })

    total = Decimal(order.total_price)
    base = (total / Decimal("1.21")).quantize(Decimal("0.01"))

    return {
        "Tipo": 5,
        "Referencia": f"SHOP-{order.shopify_id}",  # ⚠️ CLAVE
        "Fecha": order.created_at.strftime("%Y-%m-%d"),
        "ID_Cliente": id_cliente,
        "PreciosImpIncluidos": True,
        "BaseImponible": float(base),
        "TotalImporte": float(total),
        "Comentario": f"Pedido Shopify {order.name}",
        "Contenido": contenido,
        "Pagos": [],
    }


def send_order_to_verial(order: Order):
    # 1️⃣ Cliente
    ok, id_cliente = ensure_customer_in_verial(order)
    if not ok:
        return False, id_cliente

    # 2️⃣ Pedido
    try:
        payload = build_order_payload(order, id_cliente)
    except Exception as e:
        return False, str(e)

    # 3️⃣ Envío
    client = VerialClient()
    success, response = client.create_order(payload)

    if success:
        return True, "Pedido enviado"
    else:
        return False, response
