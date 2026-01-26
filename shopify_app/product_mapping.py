"""
Mapeo automático de productos Shopify ↔ Verial por código de barras.
"""
import logging
from django.utils import timezone
from .models import ProductVariant, ProductMapping
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')


def get_verial_products_by_barcode():
    """
    Obtiene productos de Verial indexados por código de barras.
    """
    client = VerialClient()
    
    if not client.is_configured():
        return False, "Verial no configurado"
    
    success, result = client.get_products()
    
    if not success:
        return False, result
    
    # Indexar por código de barras
    productos = {}
    for art in result.get("Articulos", []):
        barcode = art.get("Barras", "").strip()
        if barcode:
            productos[barcode] = {
                "id": art.get("Id"),
                "nombre": art.get("Nombre", ""),
                "barcode": barcode,
            }
    
    return True, productos


def auto_map_products_by_barcode():
    """
    Mapea automáticamente variantes de Shopify con artículos de Verial
    usando el código de barras como clave.
    
    Returns:
        (success, result_dict)
    """
    # Obtener catálogo Verial
    success, verial_products = get_verial_products_by_barcode()
    
    if not success:
        return False, {"error": verial_products}
    
    if not verial_products:
        return False, {"error": "No se encontraron productos en Verial con código de barras"}
    
    # Estadísticas
    mapeados = 0
    actualizados = 0
    sin_barcode_shopify = 0
    sin_match = []
    
    # Recorrer variantes de Shopify con barcode
    variants = ProductVariant.objects.exclude(barcode="").exclude(barcode__isnull=True)
    
    for variant in variants:
        barcode = variant.barcode.strip()
        
        if not barcode:
            sin_barcode_shopify += 1
            continue
        
        # Buscar en Verial
        verial_art = verial_products.get(barcode)
        
        if verial_art:
            # Crear o actualizar mapeo
            mapping, created = ProductMapping.objects.update_or_create(
                variant=variant,
                defaults={
                    "verial_id": verial_art["id"],
                    "verial_barcode": verial_art["barcode"],
                }
            )
            
            if created:
                mapeados += 1
                logger.info(f"Mapeado: {variant} → Verial {verial_art['id']}")
            else:
                actualizados += 1
        else:
            sin_match.append({
                "variant": str(variant),
                "barcode": barcode,
                "sku": variant.sku,
            })
    
    # Variantes sin barcode
    total_sin_barcode = ProductVariant.objects.filter(
        barcode=""
    ).count() + ProductVariant.objects.filter(barcode__isnull=True).count()
    
    result = {
        "verial_productos": len(verial_products),
        "mapeados_nuevos": mapeados,
        "actualizados": actualizados,
        "sin_match": sin_match,
        "sin_barcode_shopify": total_sin_barcode,
    }
    
    logger.info(f"Mapeo completado: {mapeados} nuevos, {actualizados} actualizados, {len(sin_match)} sin match")
    
    return True, result


def get_mapping_stats():
    """
    Devuelve estadísticas del estado del mapeo.
    """
    total_variants = ProductVariant.objects.count()
    mapeados = ProductMapping.objects.count()
    sin_mapear = total_variants - mapeados
    sin_barcode = ProductVariant.objects.filter(barcode="").count()
    
    return {
        "total_variants": total_variants,
        "mapeados": mapeados,
        "sin_mapear": sin_mapear,
        "sin_barcode": sin_barcode,
        "porcentaje": round((mapeados / total_variants * 100), 1) if total_variants > 0 else 0,
    }