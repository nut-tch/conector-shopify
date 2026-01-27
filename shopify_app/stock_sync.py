import logging
import requests
from .models import Shop, ProductMapping
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('stock')


def get_verial_stock():
    client = VerialClient()
    
    if not client.is_configured():
        return False, "Verial no configurado"
    
    success, result = client.get_stock()
    
    if not success:
        return False, result
    
    stock_data = {}
    for item in result.get("Stock", []):
        art_id = item.get("ID_Articulo")
        stock = item.get("Stock", 0)
        if art_id:
            stock_data[art_id] = int(stock) if stock else 0
    
    return True, stock_data


def get_shopify_location(shop):
    url = f"https://{shop.shop}/admin/api/2024-01/locations.json"
    headers = {"X-Shopify-Access-Token": shop.access_token}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return None
    
    locations = response.json().get("locations", [])
    if locations:
        return locations[0]["id"]
    return None


def get_inventory_item_id(shop, variant_shopify_id):
    url = f"https://{shop.shop}/admin/api/2024-01/variants/{variant_shopify_id}.json"
    headers = {"X-Shopify-Access-Token": shop.access_token}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return None
    
    variant_data = response.json().get("variant", {})
    return variant_data.get("inventory_item_id")


def update_shopify_stock(shop, inventory_item_id, location_id, quantity):
    url = f"https://{shop.shop}/admin/api/2024-01/inventory_levels/set.json"
    headers = {
        "X-Shopify-Access-Token": shop.access_token,
        "Content-Type": "application/json"
    }
    
    payload = {
        "location_id": location_id,
        "inventory_item_id": inventory_item_id,
        "available": quantity
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    return response.status_code == 200


def sync_stock_verial_to_shopify():
    shop = Shop.objects.first()
    if not shop:
        return False, {"error": "Tienda no configurada"}
    
    location_id = get_shopify_location(shop)
    if not location_id:
        return False, {"error": "No se pudo obtener ubicación de Shopify"}
    
    success, verial_stock = get_verial_stock()
    if not success:
        return False, {"error": verial_stock}
    
    actualizados = 0
    errores = 0
    sin_stock_verial = 0
    
    mappings = ProductMapping.objects.select_related('variant').all()
    
    for mapping in mappings:
        verial_id = mapping.verial_id
        stock = verial_stock.get(verial_id)
        
        if stock is None:
            sin_stock_verial += 1
            continue
        
        inventory_item_id = get_inventory_item_id(shop, mapping.variant.shopify_id)
        
        if not inventory_item_id:
            errores += 1
            logger.error(f"No se pudo obtener inventory_item_id para {mapping.variant}")
            continue
        
        if update_shopify_stock(shop, inventory_item_id, location_id, stock):
            actualizados += 1
            logger.info(f"Stock actualizado: {mapping.variant} → {stock}")
        else:
            errores += 1
            logger.error(f"Error actualizando stock: {mapping.variant}")
    
    return True, {
        "actualizados": actualizados,
        "errores": errores,
        "sin_stock_verial": sin_stock_verial,
        "total_mappings": mappings.count(),
        "productos_verial": len(verial_stock)
    }