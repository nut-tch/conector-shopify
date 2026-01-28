import logging
import requests
from .models import Shop, ProductMapping, ProductVariant
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


def get_verial_products_by_barcode():
    client = VerialClient()
    
    if not client.is_configured():
        return False, "Verial no configurado"
    
    success, result = client.get_products()
    
    if not success:
        return False, result
    
    productos = {}
    for art in result.get("Articulos", []):
        barcode = art.get("ReferenciaBarras", "").strip()
        if barcode:
            productos[barcode] = art.get("Id")
    
    return True, productos


def graphql_request(shop, query, variables=None):
    url = f"https://{shop.shop}/admin/api/2024-01/graphql.json"
    headers = {
        "X-Shopify-Access-Token": shop.access_token,
        "Content-Type": "application/json"
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    return None


def get_shopify_location_id(shop):
    query = """
    query {
        locations(first: 1) {
            nodes {
                id
            }
        }
    }
    """
    
    data = graphql_request(shop, query)
    
    if data and data.get("data", {}).get("locations", {}).get("nodes"):
        return data["data"]["locations"]["nodes"][0]["id"]
    return None


def get_shopify_inventory_items(shop):
    """Obtener todos los inventory items con su barcode/sku"""
    items = []
    has_next_page = True
    cursor = None
    
    while has_next_page:
        if cursor:
            query = """
            query {
                inventoryItems(first: 250, after: "%s") {
                    nodes {
                        id
                        tracked
                        sku
                        variant {
                            barcode
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
            """ % cursor
        else:
            query = """
            query {
                inventoryItems(first: 250) {
                    nodes {
                        id
                        tracked
                        sku
                        variant {
                            barcode
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
            """
        
        data = graphql_request(shop, query)
        
        if data and data.get("data", {}).get("inventoryItems"):
            inventory_data = data["data"]["inventoryItems"]
            items.extend(inventory_data["nodes"])
            has_next_page = inventory_data["pageInfo"]["hasNextPage"]
            cursor = inventory_data["pageInfo"]["endCursor"]
        else:
            has_next_page = False
    
    return items


def update_stock_batch(shop, location_id, quantities):
    """Actualizar stock en lote con una sola llamada"""
    mutation = """
    mutation InventorySet($input: InventorySetQuantitiesInput!) {
        inventorySetQuantities(input: $input) {
            inventoryAdjustmentGroup {
                createdAt
                reason
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {
        "input": {
            "ignoreCompareQuantity": True,
            "name": "available",
            "reason": "correction",
            "quantities": quantities
        }
    }
    
    data = graphql_request(shop, mutation, variables)
    
    if data:
        result = data.get("data", {}).get("inventorySetQuantities", {})
        errors = result.get("userErrors", [])
        if errors:
            logger.error(f"Errores actualizando stock: {errors}")
            return False, errors
        return True, result
    
    return False, "No response"


def sync_stock_verial_to_shopify():
    shop = Shop.objects.first()
    if not shop:
        return False, {"error": "Tienda no configurada"}
    
    location_id = get_shopify_location_id(shop)
    if not location_id:
        return False, {"error": "No se pudo obtener ubicación de Shopify"}

    success, verial_products = get_verial_products_by_barcode()
    if not success:
        return False, {"error": f"Error obteniendo productos Verial: {verial_products}"}
    
    success, verial_stock = get_verial_stock()
    if not success:
        return False, {"error": f"Error obteniendo stock Verial: {verial_stock}"}

    shopify_items = get_shopify_inventory_items(shop)
    if not shopify_items:
        return False, {"error": "No se pudieron obtener productos de Shopify"}

    quantities = []
    mapeados = 0
    sin_match = 0
    
    for item in shopify_items:
        code = item.get("sku") or ""
        if item.get("variant") and item["variant"].get("barcode"):
            code = item["variant"]["barcode"]
        
        if not code:
            sin_match += 1
            continue

        verial_id = verial_products.get(code)
        if not verial_id:
            sin_match += 1
            continue

        stock = verial_stock.get(verial_id, 0)
        
        quantities.append({
            "inventoryItemId": item["id"],
            "locationId": location_id,
            "quantity": stock
        })
        mapeados += 1
    
    if not quantities:
        return False, {"error": "No hay productos para actualizar"}

    actualizados = 0
    errores = 0
    
    chunk_size = 250
    for i in range(0, len(quantities), chunk_size):
        chunk = quantities[i:i + chunk_size]
        success, result = update_stock_batch(shop, location_id, chunk)
        
        if success:
            actualizados += len(chunk)
            logger.info(f"Stock actualizado: {len(chunk)} productos")
        else:
            errores += len(chunk)
            logger.error(f"Error actualizando chunk: {result}")
    
    return True, {
        "actualizados": actualizados,
        "errores": errores,
        "sin_match": sin_match,
        "total_shopify": len(shopify_items),
        "productos_verial": len(verial_products)
    }