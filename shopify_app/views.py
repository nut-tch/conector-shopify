import os
import json
import hmac
import hashlib
import base64
import requests
from datetime import datetime, timedelta
from shopify_app.product_mapping import auto_map_products_by_barcode
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from urllib.parse import urlencode
from django.utils.dateparse import parse_datetime

from .models import Shop, Order, OrderLine, Product, ProductVariant, Customer


SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
SHOPIFY_SCOPES = os.getenv("SHOPIFY_SCOPES")
SHOPIFY_REDIRECT_URI = os.getenv("SHOPIFY_REDIRECT_URI")


def health_check(request):
    return JsonResponse({"status": "ok"})


def shopify_install(request):
    shop = request.GET.get("shop")
    if not shop:
        return HttpResponse("Falta parámetro shop", status=400)

    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": SHOPIFY_SCOPES,
        "redirect_uri": SHOPIFY_REDIRECT_URI,
        "state": "random_string",
    }

    install_url = f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
    return redirect(install_url)


@csrf_exempt
def shopify_callback(request):
    code = request.GET.get("code")
    shop = request.GET.get("shop")

    if not code or not shop:
        return HttpResponse("Faltan parámetros", status=400)

    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code,
    }

    response = requests.post(token_url, json=payload)

    try:
        data = response.json()
    except Exception:
        return JsonResponse(
            {"error": "Respuesta inválida de Shopify", "raw": response.text},
            status=400,
        )

    access_token = data.get("access_token")

    if not access_token:
        return JsonResponse(data, status=400)

    Shop.objects.update_or_create(
        shop=shop,
        defaults={"access_token": access_token}
    )

    return JsonResponse({
        "shop": shop,
        "access_token": access_token,
        "saved": True,
    })


def orders_view(request):
    shop = Shop.objects.first()

    if not shop:
        return JsonResponse({"error": "Tienda no encontrada"}, status=404)

    url = f"https://{shop.shop}/admin/api/2024-01/orders.json"
    headers = {"X-Shopify-Access-Token": shop.access_token}

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return JsonResponse({
            "error": "Error de Shopify",
            "status": response.status_code
        }, status=500)

    data = response.json()

    orders_clean = []
    for order in data["orders"]:
        orders_clean.append({
            "id": order["id"],
            "name": order["name"],
            "email": order.get("email", ""),
            "total_price": order["total_price"],
            "financial_status": order["financial_status"],
            "fulfillment_status": order.get("fulfillment_status", "unfulfilled"),
            "created_at": order["created_at"]
        })

    return JsonResponse({
        "count": len(orders_clean),
        "orders": orders_clean
    })


def sync_orders(request):
    shop = Shop.objects.first()

    if not shop:
        return JsonResponse({"error": "Tienda no encontrada"}, status=404)

    url = f"https://{shop.shop}/admin/api/2024-01/orders.json"
    headers = {"X-Shopify-Access-Token": shop.access_token}

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return JsonResponse({
            "error": "Error de Shopify",
            "status": response.status_code
        }, status=500)

    data = response.json()

    saved = 0
    for order_data in data["orders"]:
        order, created = Order.objects.update_or_create(
            shopify_id=order_data["id"],
            defaults={
                "shop": shop,
                "name": order_data["name"],
                "email": order_data.get("email", ""),
                "total_price": order_data["total_price"],
                "financial_status": order_data["financial_status"],
                "fulfillment_status": order_data.get("fulfillment_status", "") or "",
                "created_at": order_data["created_at"]
            }
        )

        # Guardar líneas de pedido
        for item in order_data.get("line_items", []):
            OrderLine.objects.update_or_create(
                order=order,
                shopify_id=item["id"],
                defaults={
                    "product_title": item.get("title", ""),
                    "variant_title": item.get("variant_title", "") or "",
                    "sku": item.get("sku", "") or "",
                    "quantity": item.get("quantity", 1),
                    "price": item.get("price", 0)
                }
            )

        saved += 1

    return JsonResponse({
        "message": "Pedidos sincronizados",
        "count": saved
    })


def sync_products(request):
    shop = Shop.objects.first()

    if not shop:
        return JsonResponse({"error": "Tienda no encontrada"}, status=404)

    headers = {"X-Shopify-Access-Token": shop.access_token}

    all_products = []
    url = f"https://{shop.shop}/admin/api/2024-01/products.json?limit=250"

    while url:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return JsonResponse({
                "error": "Error de Shopify",
                "status": response.status_code
            }, status=500)

        data = response.json()
        all_products.extend(data["products"])

        link_header = response.headers.get("Link", "")
        url = None
        if 'rel="next"' in link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")

    saved_products = 0
    saved_variants = 0
    
    for product_data in all_products:
        product, created = Product.objects.update_or_create(
            shopify_id=product_data["id"],
            defaults={
                "shop": shop,
                "title": product_data["title"],
                "vendor": product_data.get("vendor", ""),
                "product_type": product_data.get("product_type", ""),
                "status": product_data["status"],
                "created_at": product_data["created_at"]
            }
        )
        saved_products += 1
        
        # Guardar variantes con barcode
        for variant_data in product_data.get("variants", []):
            ProductVariant.objects.update_or_create(
                shopify_id=variant_data["id"],
                defaults={
                    "product": product,
                    "title": variant_data.get("title", "Default"),
                    "sku": variant_data.get("sku", "") or "",
                    "barcode": variant_data.get("barcode", "") or "",
                    "price": variant_data.get("price", 0),
                    "inventory_quantity": variant_data.get("inventory_quantity", 0),
                }
            )
            saved_variants += 1

    return JsonResponse({
        "message": "Productos sincronizados",
        "products": saved_products,
        "variants": saved_variants
    })


def sync_customers(request):
    shop = Shop.objects.first()

    if not shop:
        return JsonResponse({"error": "Tienda no encontrada"}, status=404)

    headers = {"X-Shopify-Access-Token": shop.access_token}

    all_customers = []
    url = f"https://{shop.shop}/admin/api/2024-01/customers.json?limit=250"

    while url:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return JsonResponse({
                "error": "Error de Shopify",
                "status": response.status_code
            }, status=500)

        data = response.json()
        all_customers.extend(data["customers"])

        link_header = response.headers.get("Link", "")
        url = None
        if 'rel="next"' in link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")

    saved = 0
    for customer in all_customers:
        Customer.objects.update_or_create(
            shopify_id=customer["id"],
            defaults={
                "shop": shop,
                "email": customer.get("email", "") or "",
                "first_name": customer.get("first_name", "") or "",
                "last_name": customer.get("last_name", "") or "",
                "phone": customer.get("phone", "") or "",
                "created_at": customer["created_at"]
            }
        )
        saved += 1

    return JsonResponse({
        "message": "Clientes sincronizados",
        "count": saved
    })


@csrf_exempt
def webhook_orders_create(request):
    if request.method != "POST":
        return HttpResponse("Método no permitido", status=405)

    shopify_hmac = request.headers.get("X-Shopify-Hmac-Sha256")
    if not shopify_hmac:
        return HttpResponse("Falta HMAC", status=400)

    digest = hmac.new(
        settings.SHOPIFY_API_SECRET.encode("utf-8"),
        request.body,
        hashlib.sha256
    ).digest()

    calculated_hmac = base64.b64encode(digest).decode()

    if not hmac.compare_digest(calculated_hmac, shopify_hmac):
        return HttpResponse("HMAC inválido", status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("JSON inválido", status=400)

    shop = Shop.objects.first()
    if not shop:
        return HttpResponse("Tienda no encontrada", status=404)

    order, created = Order.objects.update_or_create(
        shopify_id=data["id"],
        defaults={
            "shop": shop,
            "name": data["name"],
            "email": data.get("email", ""),
            "total_price": data["total_price"],
            "financial_status": data["financial_status"],
            "fulfillment_status": data.get("fulfillment_status", "") or "",
            "created_at": parse_datetime(data["created_at"]),
            "status": "RECEIVED",
        }
    )

    for item in data.get("line_items", []):
        OrderLine.objects.update_or_create(
            order=order,
            shopify_id=item["id"],
            defaults={
                "product_title": item.get("title", ""),
                "variant_title": item.get("variant_title", "") or "",
                "sku": item.get("sku", "") or "",
                "quantity": item.get("quantity", 1),
                "price": item.get("price", 0),
            }
        )

    print(f"✅ PEDIDO RECIBIDO: {order.name}")
    return HttpResponse("OK", status=200)

def register_webhook(request):
    shop = Shop.objects.first()
    if not shop:
        return JsonResponse({"error": "Tienda no encontrada"}, status=404)

    webhook_url = os.getenv("WEBHOOK_URL", "https://tu-dominio.com/shopify/webhook/orders/create/")

    payload = {
        "webhook": {
            "topic": "orders/create",
            "address": webhook_url,
            "format": "json"
        }
    }

    url = f"https://{shop.shop}/admin/api/2024-01/webhooks.json"
    headers = {
        "X-Shopify-Access-Token": shop.access_token,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code not in [200, 201]:
        return JsonResponse({
            "error": "Error al registrar el webhook",
            "status": response.status_code,
            "body": response.text
        }, status=500)

    return JsonResponse({
        "message": "Webhook registrado correctamente",
        "response": response.json()
    })


def dashboard(request):
    today = datetime.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)

    total_orders = Order.objects.count()
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()

    orders_today = Order.objects.filter(created_at__date=today).count()
    revenue_today = Order.objects.filter(created_at__date=today).aggregate(
        total=Sum('total_price'))['total'] or 0

    orders_7_days = Order.objects.filter(created_at__date__gte=last_7_days).count()
    revenue_7_days = Order.objects.filter(created_at__date__gte=last_7_days).aggregate(
        total=Sum('total_price'))['total'] or 0

    orders_30_days = Order.objects.filter(created_at__date__gte=last_30_days).count()
    revenue_30_days = Order.objects.filter(created_at__date__gte=last_30_days).aggregate(
        total=Sum('total_price'))['total'] or 0

    orders_by_status = Order.objects.values('financial_status').annotate(
        count=Count('id')).order_by('-count')

    recent_orders = Order.objects.order_by('-created_at')[:5]

    orders_per_day = Order.objects.filter(
        created_at__date__gte=last_7_days
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id'),
        revenue=Sum('total_price')
    ).order_by('date')

    context = {
        'total_orders': total_orders,
        'total_customers': total_customers,
        'total_products': total_products,
        'orders_today': orders_today,
        'revenue_today': revenue_today,
        'orders_7_days': orders_7_days,
        'revenue_7_days': revenue_7_days,
        'orders_30_days': orders_30_days,
        'revenue_30_days': revenue_30_days,
        'orders_by_status': orders_by_status,
        'recent_orders': recent_orders,
        'orders_per_day': list(orders_per_day),
    }

    return render(request, 'dashboard.html', context)

def auto_map_products_view(request):   
    from .product_mapping import auto_map_products_by_barcode, get_mapping_stats
    
    success, result = auto_map_products_by_barcode()
    stats = get_mapping_stats()

    return JsonResponse({
        "success": success,
        "result": result,
        "stats": stats
    })

def sync_stock_view(request):
    from .stock_sync import sync_stock_verial_to_shopify
    
    success, result = sync_stock_verial_to_shopify()
    
    return JsonResponse({
        "success": success,
        "result": result
    })

def test_locations_view(request):
    shop = Shop.objects.first()
    if not shop:
        return JsonResponse({"error": "No hay tienda"})
    
    url = f"https://{shop.shop}/admin/api/2024-01/locations.json"
    headers = {"X-Shopify-Access-Token": shop.access_token}
    
    response = requests.get(url, headers=headers)
    
    return JsonResponse({
        "status_code": response.status_code,
        "response": response.json() if response.ok else response.text
    })