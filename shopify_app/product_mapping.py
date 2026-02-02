import logging
from django.db import transaction
from .models import ProductVariant, ProductMapping
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')

def get_verial_products_by_barcode():
    """
    Obtiene el catálogo completo de Verial indexado por código de barras.
    """
    client = VerialClient()
    if not client.is_configured():
        return False, "Verial no configurado en settings"
    
    success, result = client.get_articles() 
    
    if not success:
        return False, result
    
    productos_indexados = {}
    for art in result.get("Articulos", []):
        barcode = str(art.get("ReferenciaBarras") or "").strip()
        if barcode:
            productos_indexados[barcode] = {
                "id": art.get("Id"),
                "nombre": art.get("Nombre", ""),
                "barcode": barcode,
            }
    
    return True, productos_indexados

def ensure_product_mapping(variant: ProductVariant):
    """
    Busca o crea el mapeo para una variante específica.
    MEJORA: Si no existe, usa get_stock(id_articulo) si tuviéramos el ID, 
    pero como buscamos por Barcode, usamos la caché de búsqueda.
    """
    mapping = ProductMapping.objects.filter(variant=variant).first()
    if mapping:
        return mapping

    barcode_limpio = str(variant.barcode or "").strip()
    if not barcode_limpio:
        logger.warning(f"Variante {variant.sku} no tiene barcode. Imposible mapear.")
        return None

    logger.info(f"Buscando mapeo en Verial para Barcode: {barcode_limpio}...")
    
    success, verial_products = get_verial_products_by_barcode()
    
    if success and isinstance(verial_products, dict):
        verial_art = verial_products.get(barcode_limpio)
        if verial_art:
            with transaction.atomic():
                mapping, created = ProductMapping.objects.update_or_create(
                    variant=variant,
                    defaults={
                        "verial_id": verial_art["id"],
                        "verial_barcode": verial_art["barcode"],
                    }
                )
            logger.info(f"✅ Mapeo creado: {variant.sku} -> Verial ID {verial_art['id']}")
            return mapping
            
    logger.error(f"❌ No se encontró el barcode {barcode_limpio} en el catálogo de Verial.")
    return None

def auto_map_products_by_barcode():
    """
    Sincronización masiva de catálogo.
    """
    success, verial_products = get_verial_products_by_barcode()
    if not success:
        return False, {"error": verial_products}
    
    stats = {"nuevos": 0, "actualizados": 0, "sin_match": []}
    
    variants = ProductVariant.objects.exclude(barcode="").exclude(barcode__isnull=True)
    
    for variant in variants:
        barcode = str(variant.barcode).strip()
        verial_art = verial_products.get(barcode)
        
        if verial_art:
            mapping, created = ProductMapping.objects.update_or_create(
                variant=variant,
                defaults={
                    "verial_id": verial_art["id"],
                    "verial_barcode": verial_art["barcode"],
                }
            )
            if created: stats["nuevos"] += 1
            else: stats["actualizados"] += 1
        else:
            stats["sin_match"].append(barcode)
            
    return True, stats