import os
import requests
import json
import hmac
import hashlib
import base64
from django.conf import settings
from urllib.parse import urlencode
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from .models import Shop, Order, Product, Customer
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from django.shortcuts import render


SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
SHOPIFY_SCOPES = os.getenv("SHOPIFY_SCOPES")
SHOPIFY_REDIRECT_URI = os.getenv("SHOPIFY_REDIRECT_URI")


def health_check(request):
    return JsonResponse({"status": "ok"})


def shopify_install(request):
    shop = request.GET.get("shop")
    if not shop:
        return HttpResponse("Missing shop parameter", status=400)

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
        return HttpResponse("Missing parameters", status=400)

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
            {"error": "Invalid response from Shopify", "raw": response.text},
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
        return JsonResponse({"error": "No shop found"}, status=404)

    url = f"https://{shop.shop}/admin/api/2024-01/orders.json"
    headers = {
        "X-Shopify-Access-Token": shop.access_token
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return JsonResponse({
            "error": "Shopify error",
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
        return JsonResponse({"error": "No shop found"}, status=404)

    url = f"https://{shop.shop}/admin/api/2024-01/orders.json"
    headers = {
        "X-Shopify-Access-Token": shop.access_token
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return JsonResponse({
            "error": "Shopify error",
            "status": response.status_code
        }, status=500)

    data = response.json()

    saved = 0
    for order in data["orders"]:
        Order.objects.update_or_create(
            shopify_id=order["id"],
            defaults={
                "shop": shop,
                "name": order["name"],
                "email": order.get("email", ""),
                "total_price": order["total_price"],
                "financial_status": order["financial_status"],
                "fulfillment_status": order.get("fulfillment_status", "") or "",
                "created_at": order["created_at"]
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
        return JsonResponse({"error": "No shop found"}, status=404)

    headers = {
        "X-Shopify-Access-Token": shop.access_token
    }

    all_products = []
    url = f"https://{shop.shop}/admin/api/2024-01/products.json?limit=250"

    while url:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return JsonResponse({
                "error": "Shopify error",
                "status": response.status_code
            }, status=500)

        data = response.json()
        all_products.extend(data["products"])

        # Buscar siguiente página en headers
        link_header = response.headers.get("Link", "")
        url = None
        if 'rel="next"' in link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")

    saved = 0
    for product in all_products:
        Product.objects.update_or_create(
            shopify_id=product["id"],
            defaults={
                "shop": shop,
                "title": product["title"],
                "vendor": product.get("vendor", ""),
                "product_type": product.get("product_type", ""),
                "status": product["status"],
                "created_at": product["created_at"]
            }
        )
        saved += 1

    return JsonResponse({
        "message": "Productos sincronizados",
        "count": saved
    })

    import json

@csrf_exempt
@csrf_exempt
def webhook_orders_create(request):
    if request.method != "POST":
        return HttpResponse("Método no permitido", status=405)

    # Verificar HMAC
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

    
    data = json.loads(request.body)
    
    shop = Shop.objects.first()
    
    if not shop:
        return HttpResponse("Tienda no encontrada", status=404)

    # Guardar pedido
    Order.objects.update_or_create(
        shopify_id=data["id"],
        defaults={
            "shop": shop,
            "name": data["name"],
            "email": data.get("email", ""),
            "total_price": data["total_price"],
            "financial_status": data["financial_status"],
            "fulfillment_status": data.get("fulfillment_status", "") or "",
            "created_at": data["created_at"]
        }
    )

    print("✅ PEDIDO RECIBIDO:", data["name"])

    return HttpResponse("OK", status=200)

def register_webhook(request):
    shop = Shop.objects.first()
    if not shop:
        return JsonResponse({"error": "Tienda no encontrada"}, status=404)

    webhook_url = "https://transsegmental-carmelo-uropodal.ngrok-free.dev/shopify/webhook/orders/create/"

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

def sync_customers(request):
    shop = Shop.objects.first()

    if not shop:
        return JsonResponse({"error": "Tienda no encontrada"}, status=404)

    headers = {
        "X-Shopify-Access-Token": shop.access_token
    }

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

        # Buscar siguiente página
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

def dashboard(request):
    today = datetime.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)

    # Estadísticas generales
    total_orders = Order.objects.count()
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()

    # Pedidos hoy
    orders_today = Order.objects.filter(created_at__date=today).count()
    revenue_today = Order.objects.filter(created_at__date=today).aggregate(
        total=Sum('total_price'))['total'] or 0

    # Pedidos últimos 7 días
    orders_7_days = Order.objects.filter(created_at__date__gte=last_7_days).count()
    revenue_7_days = Order.objects.filter(created_at__date__gte=last_7_days).aggregate(
        total=Sum('total_price'))['total'] or 0

    # Pedidos últimos 30 días
    orders_30_days = Order.objects.filter(created_at__date__gte=last_30_days).count()
    revenue_30_days = Order.objects.filter(created_at__date__gte=last_30_days).aggregate(
        total=Sum('total_price'))['total'] or 0

    # Pedidos por estado
    orders_by_status = Order.objects.values('financial_status').annotate(
        count=Count('id')).order_by('-count')

    # Últimos 5 pedidos
    recent_orders = Order.objects.order_by('-created_at')[:5]

    # Pedidos por día (últimos 7 días)
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