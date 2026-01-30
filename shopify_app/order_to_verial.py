import logging
import json
from datetime import datetime
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
    Construye el payload con la estructura validada para NuevoDocClienteWS (Tipo 5).
    """
    lineas_verial = []
    for line in order.lines.all():
        mapping = get_line_mapping(line)
        if not mapping:
            raise OrderToVerialError(f"Producto sin mapear en Shopify: {line.product_title}")

        # Estructura VALIDADA: Usamos ID_Articulo, Uds y TipoRegistro
        lineas_verial.append({
            "TipoRegistro": 1,          # Fijo para artículos
            "ID_Articulo": int(mapping.verial_id),
            "Uds": float(line.quantity),
            "Precio": round(float(line.price), 2),
            "PorcentajeIVA": 21.0,      # Verial espera este nombre de campo
            "Dto": 0.0
        })

    total = round(float(order.total_price), 2)
    
    # Estructura VALIDADA para NuevoDocClienteWS
    payload = {
        "Tipo": 5,                      # 5 = Presupuesto/Pedido (Evita Veri*Factu)
        "ID_Cliente": int(id_cliente),
        "Fecha": datetime.now().isoformat(),
        "Referencia": f"S{order.name}"[:20], # Usamos order.name (ej: #1001)
        "TotalImporte": total,           # Importante: Nombre exacto
        "PreciosImpIncluidos": True,     # Importante: Nombre exacto
        "Contenido": lineas_verial,      # Importante: En lugar de "Lineas"
        "Pagos": []
    }
    
    logger.info(f"DEBUG PAYLOAD ENVIADO: {json.dumps(payload)}")
    return payload

def send_order_to_verial(order: Order):
    # 1. Asegurar que el cliente existe o crearlo
    ok, id_cliente = ensure_customer_in_verial(order)
    if not ok:
        return False, f"Error Cliente: {id_cliente}"

    try:
        # 2. Construir el payload con los campos que funcionan
        payload = build_order_payload(order, id_cliente)
        
        # 3. Usar el cliente corregido
        client = VerialClient()
        success, response = client.create_order(payload)

        if success:
            # Verial devuelve el ID del documento creado
            verial_id = response.get("Id")
            
            # Guardamos el mapeo para evitar duplicados futuros
            OrderMapping.objects.update_or_create(
                order=order,
                defaults={
                    "verial_id": verial_id,
                    "verial_referencia": payload["Referencia"],
                    "verial_numero": str(verial_id) # O el campo Numero si viniera
                }
            )
            
            return True, "Pedido inyectado correctamente"
        else:
            # Aquí 'response' contiene la descripción del error de Verial
            return False, str(response)

    except OrderToVerialError as e:
        return False, str(e)
    except Exception as e:
        logger.error(f"Error crítico enviando pedido {order.id}: {e}")
        return False, str(e)