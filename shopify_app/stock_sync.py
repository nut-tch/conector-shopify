import logging
import requests
from .models import Shop, ProductMapping, ProductVariant
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('stock')

def get_verial_stock():
    """Obtiene el stock real desde Verial usando el nuevo cliente."""
    client = VerialClient()
    if not client.is_configured():
        return False, "Verial no configurado"
    
    # Usamos el método que ya definimos en VerialClient
    success, result = client.get_stock(id_articulo=0)
    
    if not success:
        return False, result

    stock_data = {}
    # Verial devuelve la lista en 'StockArticulos'
    for item in result.get("StockArticulos", []):
        # Campos exactos según pruebas: IdArticulo y Stock
        art_id = item.get("IdArticulo")
        stock = item.get("Stock", 0)
        if art_id is not None:
            stock_data[int(art_id)] = int(float(stock))
    
    return True, stock_data

def get_verial_products_by_barcode():
    """Obtiene el catálogo para mapear Barcode -> ID_Verial."""
    client = VerialClient()
    if not client.is_configured():
        return False, "Verial no configurado"
    
    # Usamos get_articles() que ya tenemos en el cliente
    success, result = client.get_articles()
    
    if not success:
        return False, result
    
    productos = {}
    for art in result.get("Articulos", []):
        # Usamos ReferenciaBarras como clave de unión
        barcode = str(art.get("ReferenciaBarras", "")).strip()
        if barcode:
            productos[barcode] = int(art.get("Id"))
    
    return True, productos

# --- MÉTODOS GRAPHQL (Se mantienen igual, están muy bien hechos) ---

def graphql_request(shop, query, variables=None):
    url = f"https://{shop.shop}/admin/api/2024-01/graphql.json"
    headers = {
        "X-Shopify-Access-Token": shop.access_token,
        "Content-Type": "application/json"
    }
    payload = {"query": query}
    if variables: payload["variables"] = variables
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error en GraphQL: {e}")
    return None

def get_shopify_location_id(shop):
    query = """query { locations(first: 1) { nodes { id } } }"""
    data = graphql_request(shop, query)
    if data and data.get("data", {}).get("locations", {}).get("nodes"):
        return data["data"]["locations"]["nodes"][0]["id"]
    return None

def get_shopify_inventory_items(shop):
    """Obtiene todos los items de inventario paginados (250 por vez)"""
    items = []
    has_next_page = True
    cursor = None
    
    while has_next_page:
        cursor_str = f', after: "{cursor}"' if cursor else ""
        query = """
        query {
            inventoryItems(first: 250 %s) {
                nodes {
                    id
                    sku
                    variant { barcode }
                }
                pageInfo { hasNextPage endCursor }
            }
        }
        """ % cursor_str
        
        data = graphql_request(shop, query)
        if data and data.get("data", {}).get("inventoryItems"):
            inv_data = data["data"]["inventoryItems"]
            items.extend(inv_data["nodes"])
            has_next_page = inv_data["pageInfo"]["hasNextPage"]
            cursor = inv_data["pageInfo"]["endCursor"]
        else:
            has_next_page = False
    return items

def update_stock_batch(shop, location_id, quantities):
    """Actualización masiva de stock"""
    mutation = """
    mutation InventorySet($input: InventorySetQuantitiesInput!) {
        inventorySetQuantities(input: $input) {
            userErrors { field message }
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
        errors = data.get("data", {}).get("inventorySetQuantities", {}).get("userErrors", [])
        if errors: return False, errors
        return True, "OK"
    return False, "No response"

# --- FUNCIÓN PRINCIPAL DE SINCRONIZACIÓN ---

def sync_stock_verial_to_shopify():
    shop = Shop.objects.first()
    if not shop: return False, {"error": "Tienda no configurada"}
    
    location_id = get_shopify_location_id(shop)
    if not location_id: return False, {"error": "No hay Location ID"}

    # 1. Obtener datos de Verial
    success_p, verial_products = get_verial_products_by_barcode()
    success_s, verial_stock = get_verial_stock()
    
    if not success_p or not success_s:
        return False, {"error": "Error conectando con Verial"}

    # 2. Obtener datos de Shopify
    shopify_items = get_shopify_inventory_items(shop)
    
    quantities = []
    for item in shopify_items:
        # Priorizar Barcode, luego SKU
        code = None
        if item.get("variant") and item["variant"].get("barcode"):
            code = str(item["variant"]["barcode"]).strip()
        if not code:
            code = str(item.get("sku", "")).strip()
        
        if not code: continue

        # Buscar el ID de Verial que corresponde a ese código
        verial_id = verial_products.get(code)
        if verial_id is not None:
            stock = verial_stock.get(verial_id, 0)
            quantities.append({
                "inventoryItemId": item["id"],
                "locationId": location_id,
                "quantity": int(stock)
            })
    
    if not quantities:
        return False, {"error": "Nada que actualizar"}

    # 3. Actualizar en trozos de 250 (límite API Shopify)
    actualizados = 0
    for i in range(0, len(quantities), 250):
        chunk = quantities[i:i + 250]
        success, res = update_stock_batch(shop, location_id, chunk)
        if success: actualizados += len(chunk)

    return True, {"actualizados": actualizados, "total": len(shopify_items)}