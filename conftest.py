"""
Fixtures y configuración común para todos los tests del proyecto
Conector Shopify-Verial

Este archivo debe estar en la raíz del proyecto.
"""
import pytest
from django.conf import settings
from decimal import Decimal
import json
import hashlib
import hmac
import base64
from datetime import datetime, timezone


# =============================================================================
# CONFIGURACIÓN DE PYTEST-DJANGO
# =============================================================================

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Habilita acceso a BD para todos los tests automáticamente"""
    pass


# =============================================================================
# FIXTURES DE TIENDA (SHOP)
# =============================================================================

@pytest.fixture
def shop_data():
    """Datos de prueba para una tienda Shopify"""
    return {
        'shop': 'test-shop.myshopify.com',
        'access_token': 'test_access_token_12345'
    }


@pytest.fixture
def shop(db, shop_data):
    """Fixture que crea una tienda de prueba en BD"""
    from shopify_app.models import Shop
    return Shop.objects.create(**shop_data)


# =============================================================================
# FIXTURES DE PRODUCTOS
# =============================================================================

@pytest.fixture
def product_data():
    """Datos de prueba para un producto"""
    return {
        'shopify_id': 1234567890,
        'title': 'Producto de Prueba',
        'vendor': 'Test Vendor',
        'product_type': 'Test Type',
        'status': 'active',
        'created_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def product(db, shop, product_data):
    """Fixture que crea un producto de prueba"""
    from shopify_app.models import Product
    return Product.objects.create(shop=shop, **product_data)


@pytest.fixture
def variant_data():
    """Datos de prueba para una variante"""
    return {
        'shopify_id': 9876543210,
        'title': 'Default Title',
        'sku': 'TEST-SKU-001',
        'barcode': '8412345678901',
        'price': Decimal('29.99'),
        'inventory_quantity': 100
    }


@pytest.fixture
def product_variant(db, product, variant_data):
    """Fixture que crea una variante de producto"""
    from shopify_app.models import ProductVariant
    return ProductVariant.objects.create(product=product, **variant_data)


@pytest.fixture
def product_mapping_data():
    """Datos de prueba para mapeo de productos"""
    return {
        'verial_id': 12345,
        'verial_barcode': '8412345678901',
    }


@pytest.fixture
def product_mapping(db, product_variant, product_mapping_data):
    """Fixture que crea un mapeo de producto"""
    from shopify_app.models import ProductMapping
    return ProductMapping.objects.create(
        variant=product_variant,
        **product_mapping_data
    )


# =============================================================================
# FIXTURES DE CLIENTES
# =============================================================================

@pytest.fixture
def customer_data():
    """Datos de prueba para un cliente"""
    return {
        'shopify_id': 5555555555,
        'email': 'test@example.com',
        'first_name': 'Juan',
        'last_name': 'Pérez',
        'phone': '+34666777888',
        'created_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def customer(db, shop, customer_data):
    """Fixture que crea un cliente de prueba"""
    from shopify_app.models import Customer
    return Customer.objects.create(shop=shop, **customer_data)


@pytest.fixture
def customer_mapping_data():
    """Datos de prueba para mapeo de clientes"""
    return {
        'verial_id': 54321,
        'verial_nif': '12345678A',
    }


@pytest.fixture
def customer_mapping(db, customer, customer_mapping_data):
    """Fixture que crea un mapeo de cliente"""
    from shopify_app.models import CustomerMapping
    return CustomerMapping.objects.create(
        customer=customer,
        **customer_mapping_data
    )


# =============================================================================
# FIXTURES DE PEDIDOS
# =============================================================================

@pytest.fixture
def order_data():
    """Datos de prueba para un pedido"""
    return {
        'shopify_id': 4444444444,
        'name': '#1001',
        'email': 'customer@example.com',
        'total_price': Decimal('59.98'),
        'financial_status': 'paid',
        'fulfillment_status': '',
        'created_at': datetime.now(timezone.utc),
        'status': 'RECEIVED',
        'sent_to_verial': False,
    }


@pytest.fixture
def order(db, shop, order_data):
    """Fixture que crea un pedido de prueba"""
    from shopify_app.models import Order
    return Order.objects.create(shop=shop, **order_data)


@pytest.fixture
def order_line_data():
    """Datos de prueba para una línea de pedido"""
    return {
        'shopify_id': 7777777777,
        'product_title': 'Producto Test',
        'variant_title': 'Default',
        'sku': 'TEST-SKU-001',
        'quantity': 2,
        'price': Decimal('29.99')
    }


@pytest.fixture
def order_line(db, order, order_line_data):
    """Fixture que crea una línea de pedido"""
    from shopify_app.models import OrderLine
    return OrderLine.objects.create(order=order, **order_line_data)


@pytest.fixture
def order_with_lines(db, order, order_line_data):
    """Fixture que crea un pedido completo con líneas"""
    from shopify_app.models import OrderLine
    
    # Crear 2 líneas de pedido
    line1 = OrderLine.objects.create(
        order=order,
        shopify_id=7777777777,
        product_title='Producto Test 1',
        variant_title='Default',
        sku='TEST-SKU-001',
        quantity=2,
        price=Decimal('29.99')
    )
    
    line2 = OrderLine.objects.create(
        order=order,
        shopify_id=8888888888,
        product_title='Producto Test 2',
        variant_title='Large',
        sku='TEST-SKU-002',
        quantity=1,
        price=Decimal('49.99')
    )
    
    order.refresh_from_db()
    return order


@pytest.fixture
def order_mapping_data():
    """Datos de prueba para mapeo de pedidos"""
    return {
        'verial_id': 99999,
        'verial_referencia': 'REF-2024-001',
        'verial_numero': 'NUM-001',
    }


@pytest.fixture
def order_mapping(db, order, order_mapping_data):
    """Fixture que crea un mapeo de pedido"""
    from shopify_app.models import OrderMapping
    return OrderMapping.objects.create(
        order=order,
        **order_mapping_data
    )


# =============================================================================
# FIXTURES DE WEBHOOKS DE SHOPIFY
# =============================================================================

@pytest.fixture
def shopify_webhook_data():
    """Datos de prueba para un webhook de Shopify (Order Create)"""
    return {
        "id": 4444444444,
        "admin_graphql_api_id": "gid://shopify/Order/4444444444",
        "app_id": 580111,
        "browser_ip": "192.168.1.1",
        "buyer_accepts_marketing": False,
        "cancel_reason": None,
        "cancelled_at": None,
        "cart_token": "cart_token_123",
        "checkout_id": 33333333,
        "checkout_token": "checkout_token_456",
        "client_details": {
            "accept_language": "es-ES",
            "browser_height": 1080,
            "browser_ip": "192.168.1.1",
            "browser_width": 1920,
            "session_hash": None,
            "user_agent": "Mozilla/5.0..."
        },
        "closed_at": None,
        "confirmed": True,
        "contact_email": "customer@example.com",
        "created_at": "2024-01-15T10:30:00+00:00",
        "currency": "EUR",
        "current_subtotal_price": "59.98",
        "current_total_discounts": "0.00",
        "current_total_price": "59.98",
        "current_total_tax": "0.00",
        "customer": {
            "id": 5555555555,
            "email": "customer@example.com",
            "first_name": "Juan",
            "last_name": "Pérez",
            "phone": "+34666777888",
            "created_at": "2024-01-01T00:00:00+00:00"
        },
        "customer_locale": "es",
        "email": "customer@example.com",
        "financial_status": "paid",
        "fulfillment_status": None,
        "line_items": [
            {
                "id": 7777777777,
                "admin_graphql_api_id": "gid://shopify/LineItem/7777777777",
                "fulfillable_quantity": 2,
                "fulfillment_service": "manual",
                "fulfillment_status": None,
                "name": "Producto Test 1",
                "price": "29.99",
                "product_id": 1234567890,
                "quantity": 2,
                "sku": "TEST-SKU-001",
                "title": "Producto Test 1",
                "variant_id": 9876543210,
                "variant_title": "Default",
                "vendor": "Test Vendor"
            },
            {
                "id": 8888888888,
                "admin_graphql_api_id": "gid://shopify/LineItem/8888888888",
                "fulfillable_quantity": 1,
                "fulfillment_service": "manual",
                "fulfillment_status": None,
                "name": "Producto Test 2",
                "price": "49.99",
                "product_id": 1234567891,
                "quantity": 1,
                "sku": "TEST-SKU-002",
                "title": "Producto Test 2",
                "variant_id": 9876543211,
                "variant_title": "Large",
                "vendor": "Test Vendor"
            }
        ],
        "name": "#1001",
        "note": None,
        "number": 1,
        "order_number": 1001,
        "phone": "+34666777888",
        "total_price": "59.98",
        "total_tax": "0.00",
        "updated_at": "2024-01-15T10:30:00+00:00"
    }


@pytest.fixture
def shopify_hmac_signature():
    """
    Genera un HMAC válido para validar webhooks de Shopify
    """
    def _generate_hmac(data, secret=None):
        """
        Genera un HMAC SHA256 para los datos del webhook
        
        Args:
            data: dict o str - Datos del webhook
            secret: str - Secreto de Shopify (usa el de settings por defecto)
        
        Returns:
            str: HMAC en base64
        """
        if secret is None:
            secret = settings.SHOPIFY_API_SECRET
        
        # Si data es dict, convertir a JSON string
        if isinstance(data, dict):
            data = json.dumps(data, separators=(',', ':'))
        
        # Generar HMAC
        hmac_obj = hmac.new(
            secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        )
        
        return base64.b64encode(hmac_obj.digest()).decode('utf-8')
    
    return _generate_hmac


# =============================================================================
# FIXTURES DE VERIAL (MOCKS)
# =============================================================================

@pytest.fixture
def mock_verial_response():
    """Respuestas mock para el API de Verial"""
    return {
        'success': {
            'InfoError': {
                'Codigo': 0,
                'Descripcion': None
            },
            'Data': {
                'ID': 12345,
                'Resultado': 'OK'
            }
        },
        'error': {
            'InfoError': {
                'Codigo': 1,
                'Descripcion': 'Error de prueba'
            }
        },
        'articulos': {
            'InfoError': {
                'Codigo': 0,
                'Descripcion': None
            },
            'Articulos': [
                {
                    'ID': 12345,
                    'Codigo': '8412345678901',
                    'Descripcion': 'Producto Test',
                    'PVP': 29.99,
                    'Stock': 100
                },
                {
                    'ID': 12346,
                    'Codigo': '8412345678902',
                    'Descripcion': 'Producto Test 2',
                    'PVP': 49.99,
                    'Stock': 50
                }
            ]
        },
        'clientes': {
            'InfoError': {
                'Codigo': 0,
                'Descripcion': None
            },
            'Clientes': [
                {
                    'ID': 54321,
                    'NIF': '12345678A',
                    'Nombre': 'Juan Pérez',
                    'Email': 'test@example.com'
                }
            ]
        },
        'nuevo_documento': {
            'InfoError': {
                'Codigo': 0,
                'Descripcion': None
            },
            'ID': 99999,
            'Referencia': 'REF-2024-001',
            'Numero': 'NUM-001'
        }
    }


# =============================================================================
# FIXTURES DE CLIENTES HTTP
# =============================================================================

@pytest.fixture
def api_client():
    """Cliente para hacer requests a la API"""
    from django.test import Client
    return Client()


@pytest.fixture
def authenticated_client(api_client, shop):
    """Cliente autenticado con una tienda"""
    # Si necesitas autenticación específica, añádela aquí
    return api_client