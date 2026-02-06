import logging
import json
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .models import Order, OrderMapping, OrderLine, ProductVariant
from .services.customer_sync import ensure_customer_in_verial
from .product_mapping import ensure_product_mapping
from erp_connector.verial_client import VerialClient

logger = logging.getLogger("verial")

class OrderToVerialError(Exception):
    pass

def get_line_mapping(line: OrderLine):
    variant = None
    if line.sku:
        variant = ProductVariant.objects.filter(sku=line.sku).first()
    if not variant:
        variant = ProductVariant.objects.filter(
            product__title=line.product_title, 
            title=line.variant_title
        ).first()
    if variant:
        return ensure_product_mapping(variant)
    return None

def build_order_payload(order: Order, id_cliente: int) -> dict:
    """
    Construye el payload con la estructura validada para NuevoDocClienteWS (Tipo 5),
    imitando al máximo la forma del middleware viejo.
    """
    iva_porcentaje = float(getattr(settings, "VERIAL_DEFAULT_VAT", 21.0))

    lineas_verial = []
    base_imponible = 0.0

    for line in order.lines.all():
        mapping = get_line_mapping(line)
        if not mapping:
            raise OrderToVerialError(f"Producto sin mapear en Shopify: {line.product_title}")

        qty = float(line.quantity)
        net_unit_price_with_vat = round(float(line.price), 4)  # precio final, con descuento e IVA
        discount_amount = float(getattr(line, "discount_amount", 0) or 0)

        # Reconstruimos un precio "antes de descuento" a partir del total de la línea
        dto = 0.0
        original_unit_price_with_vat = net_unit_price_with_vat
        if qty > 0 and discount_amount > 0:
            total_net = net_unit_price_with_vat * qty
            total_before_discount = total_net + discount_amount
            if total_before_discount > 0:
                original_unit_price_with_vat = round(total_before_discount / qty, 4)
                dto = round((discount_amount / total_before_discount) * 100.0, 2)

        # Base imponible en Verial = Uds * Precio_sin_IVA * (1 - dto%)
        precio_sin_iva_original = original_unit_price_with_vat / (1 + iva_porcentaje / 100.0)
        base_linea = qty * precio_sin_iva_original * (1 - dto / 100.0)
        base_imponible += base_linea

        lineas_verial.append(
            {
                "TipoRegistro": 1,
                "ID_Articulo": int(mapping.verial_id),
                "Uds": qty,
                "Precio": round(original_unit_price_with_vat, 4),
                "Dto": dto,
                "PorcentajeIVA": float(iva_porcentaje),
            }
        )

    total = round(float(order.total_price), 2)

    # Pagos: en el viejo se construían a partir de objetos PaymentSale.
    # Aquí aproximamos: si el pedido está pagado, mandamos un solo pago
    # por el total del documento con un método genérico configurable.
    pagos = []
    estado_pago = (order.financial_status or "").lower()
    if estado_pago in ("paid", "paid_in_full", "captured", "authorized"):
        metodo_pago_id = int(getattr(settings, "VERIAL_DEFAULT_PAYMENT_METHOD_ID", 0))
        if metodo_pago_id:
            pagos.append(
                {
                    "ID_MetodoPago": metodo_pago_id,
                    "Fecha": order.created_at.isoformat(),
                    "Importe": float(total),
                }
            )

    payload = {
        "Tipo": 5,
        "ID_Cliente": int(id_cliente),
        "Fecha": datetime.now().isoformat(),
        "Referencia": f"S{order.name}"[:20], 
        "PreciosImpIncluidos": True,
        "BaseImponible": round(base_imponible, 2),
        "TotalImporte": total,
        "Comentario": "",
        "Contenido": lineas_verial,
        "Pagos": pagos,
    }
    
    logger.info(f"DEBUG PAYLOAD ENVIADO: {json.dumps(payload)}")
    return payload

def send_order_to_verial(order: Order):
    ok, id_cliente = ensure_customer_in_verial(order)
    if not ok:
        return False, f"Error Cliente: {id_cliente}"

    try:
        payload = build_order_payload(order, id_cliente)
        
        client = VerialClient()
        success, response = client.create_order(payload)

        if success:
            verial_id = response.get("Id")
            
            OrderMapping.objects.update_or_create(
                order=order,
                defaults={
                    "verial_id": verial_id,
                    "verial_referencia": payload["Referencia"],
                    "verial_numero": str(verial_id)
                }
            )

            order.sent_to_verial = True
            order.sent_to_verial_at = timezone.now()
            order.save(update_fields=['sent_to_verial', 'sent_to_verial_at'])
            
            return True, "Pedido inyectado correctamente"
        else:
            return False, str(response)

    except OrderToVerialError as e:
        return False, str(e)
    except Exception as e:
        logger.error(f"Error crítico enviando pedido {order.id}: {e}")
        return False, str(e)