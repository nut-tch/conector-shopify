import os
import requests
from urllib.parse import urlencode
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from .models import Shop, Order, Product


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