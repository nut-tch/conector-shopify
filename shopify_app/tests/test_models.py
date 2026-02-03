"""
Tests para los modelos de shopify_app

Estos tests están adaptados específicamente para los modelos del proyecto
Conector Shopify-Verial.
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from django.db import IntegrityError


@pytest.mark.unit
class TestShopModel:
    """Tests para el modelo Shop"""
    
    def test_create_shop(self, shop_data):
        """Test de creación básica de una tienda"""
        from shopify_app.models import Shop
        
        shop = Shop.objects.create(**shop_data)
        
        assert shop.shop == shop_data['shop']
        assert shop.access_token == shop_data['access_token']
        assert shop.id is not None
    
    def test_shop_str_representation(self, shop):
        """Test del método __str__ de Shop"""
        assert str(shop) == shop.shop
    
    def test_shop_unique_constraint(self, shop):
        """Test que el campo shop es único"""
        from shopify_app.models import Shop
        
        with pytest.raises(IntegrityError):
            Shop.objects.create(
                shop=shop.shop,
                access_token='otro_token'
            )
    
    def test_shop_verbose_names(self):
        """Test de verbose names en español"""
        from shopify_app.models import Shop
        
        assert Shop._meta.verbose_name == "Tienda"
        assert Shop._meta.verbose_name_plural == "Tiendas"


@pytest.mark.unit
class TestProductModel:
    """Tests para el modelo Product"""
    
    def test_create_product(self, shop, product_data):
        """Test de creación de producto"""
        from shopify_app.models import Product
        
        product = Product.objects.create(shop=shop, **product_data)
        
        assert product.shop == shop
        assert product.shopify_id == product_data['shopify_id']
        assert product.title == product_data['title']
        assert product.status == 'active'
    
    def test_product_shop_relationship(self, product, shop):
        """Test de la relación Product -> Shop"""
        assert product.shop == shop
        assert product in shop.product_set.all()
    
    def test_product_str_representation(self, product):
        """Test del método __str__ de Product"""
        assert str(product) == product.title
    
    def test_product_shopify_id_unique(self, shop, product):
        """Test que shopify_id es único"""
        from shopify_app.models import Product
        
        with pytest.raises(IntegrityError):
            Product.objects.create(
                shop=shop,
                shopify_id=product.shopify_id,  # Mismo ID
                title='Otro producto',
                vendor='Vendor',
                product_type='Type',
                status='active',
                created_at=timezone.now()
            )
    
    def test_product_verbose_names(self):
        """Test de verbose names"""
        from shopify_app.models import Product
        
        assert Product._meta.verbose_name == "Producto"
        assert Product._meta.verbose_name_plural == "Productos"


@pytest.mark.unit
class TestProductVariantModel:
    """Tests para el modelo ProductVariant"""
    
    def test_create_variant(self, product, variant_data):
        """Test de creación de variante"""
        from shopify_app.models import ProductVariant
        
        variant = ProductVariant.objects.create(
            product=product,
            **variant_data
        )
        
        assert variant.product == product
        assert variant.sku == variant_data['sku']
        assert variant.barcode == variant_data['barcode']
        assert variant.price == variant_data['price']
        assert variant.inventory_quantity == variant_data['inventory_quantity']
    
    def test_variant_product_relationship(self, product_variant, product):
        """Test de la relación ProductVariant -> Product"""
        assert product_variant.product == product
        assert product_variant in product.variants.all()
    
    def test_variant_str_representation(self, product_variant, product):
        """Test del método __str__ de ProductVariant"""
        expected = f"{product.title} - {product_variant.title}"
        assert str(product_variant) == expected
    
    def test_variant_with_no_barcode(self, product):
        """Test de variante sin código de barras"""
        from shopify_app.models import ProductVariant
        
        variant = ProductVariant.objects.create(
            product=product,
            shopify_id=9999999999,
            title='Sin Barcode',
            sku='NO-BARCODE',
            barcode='',  # Sin barcode
            price=Decimal('10.00'),
            inventory_quantity=0
        )
        
        assert variant.barcode == ''
        assert variant.sku == 'NO-BARCODE'
    
    def test_variant_shopify_id_unique(self, product, product_variant):
        """Test que shopify_id es único en variantes"""
        from shopify_app.models import ProductVariant
        
        with pytest.raises(IntegrityError):
            ProductVariant.objects.create(
                product=product,
                shopify_id=product_variant.shopify_id,  # Mismo ID
                title='Otra variante',
                sku='SKU-2',
                barcode='',
                price=Decimal('20.00')
            )


@pytest.mark.unit
class TestCustomerModel:
    """Tests para el modelo Customer"""
    
    def test_create_customer(self, shop, customer_data):
        """Test de creación de cliente"""
        from shopify_app.models import Customer
        
        customer = Customer.objects.create(shop=shop, **customer_data)
        
        assert customer.shop == shop
        assert customer.email == customer_data['email']
        assert customer.first_name == customer_data['first_name']
        assert customer.last_name == customer_data['last_name']
    
    def test_customer_full_name(self, customer):
        """Test para obtener nombre completo del cliente"""
        full_name = f"{customer.first_name} {customer.last_name}"
        assert full_name == "Juan Pérez"
    
    def test_customer_shop_relationship(self, customer, shop):
        """Test de la relación Customer -> Shop"""
        assert customer.shop == shop
        assert customer in shop.customer_set.all()
    
    def test_customer_str_representation(self, customer):
        """Test del método __str__ de Customer"""
        expected = f"{customer.first_name} {customer.last_name} ({customer.email})"
        assert str(customer) == expected
    
    def test_customer_shopify_id_unique(self, shop, customer):
        """Test que shopify_id es único"""
        from shopify_app.models import Customer
        
        with pytest.raises(IntegrityError):
            Customer.objects.create(
                shop=shop,
                shopify_id=customer.shopify_id,  # Mismo ID
                email='otro@example.com',
                first_name='María',
                last_name='García',
                created_at=timezone.now()
            )


@pytest.mark.unit
class TestOrderModel:
    """Tests para el modelo Order"""
    
    def test_create_order(self, shop, order_data):
        """Test de creación de pedido"""
        from shopify_app.models import Order
        
        order = Order.objects.create(shop=shop, **order_data)
        
        assert order.shop == shop
        assert order.name == order_data['name']
        assert order.total_price == order_data['total_price']
        assert order.financial_status == 'paid'
        assert order.status == 'RECEIVED'
        assert order.sent_to_verial is False
    
    def test_order_without_fulfillment(self, order):
        """Test de pedido sin estado de envío"""
        assert order.fulfillment_status == ''
    
    def test_order_str_representation(self, order):
        """Test del método __str__ de Order"""
        assert str(order) == order.name
    
    def test_order_status_choices(self):
        """Test de las opciones de estado"""
        from shopify_app.models import Order
        
        status_values = [choice[0] for choice in Order.STATUS_CHOICES]
        assert 'RECEIVED' in status_values
        assert 'READY' in status_values
        assert 'SENT' in status_values
        assert 'ERROR' in status_values
    
    def test_order_shopify_id_unique(self, shop, order):
        """Test que shopify_id es único"""
        from shopify_app.models import Order
        
        with pytest.raises(IntegrityError):
            Order.objects.create(
                shop=shop,
                shopify_id=order.shopify_id,  # Mismo ID
                name='#1002',
                email='otro@example.com',
                total_price=Decimal('100.00'),
                financial_status='pending',
                created_at=timezone.now()
            )
    
    def test_order_default_values(self, shop):
        """Test de valores por defecto"""
        from shopify_app.models import Order
        
        order = Order.objects.create(
            shop=shop,
            shopify_id=9999999999,
            name='#1999',
            email='test@example.com',
            total_price=Decimal('50.00'),
            financial_status='paid',
            created_at=timezone.now()
        )
        
        assert order.status == 'RECEIVED'
        assert order.sent_to_verial is False
        assert order.verial_status == ''
        assert order.fulfillment_status == ''
        assert order.received_at is not None


@pytest.mark.unit
class TestOrderLineModel:
    """Tests para el modelo OrderLine"""
    
    def test_create_order_line(self, order, order_line_data):
        """Test de creación de línea de pedido"""
        from shopify_app.models import OrderLine
        
        line = OrderLine.objects.create(order=order, **order_line_data)
        
        assert line.order == order
        assert line.sku == order_line_data['sku']
        assert line.quantity == order_line_data['quantity']
        assert line.price == order_line_data['price']
    
    def test_order_line_total_property(self, order_line):
        """Test del cálculo de total de línea"""
        expected_total = order_line.quantity * order_line.price
        assert order_line.total == expected_total
        assert order_line.total == Decimal('59.98')
    
    def test_order_line_total_with_zero_quantity(self, order):
        """Test de total con cantidad cero"""
        from shopify_app.models import OrderLine
        
        line = OrderLine.objects.create(
            order=order,
            shopify_id=1111111111,
            product_title='Producto',
            quantity=0,
            price=Decimal('10.00')
        )
        
        assert line.total == 0
    
    def test_order_line_str_representation(self, order_line):
        """Test del método __str__ de OrderLine"""
        expected = f"{order_line.quantity}x {order_line.product_title}"
        assert str(order_line) == expected
    
    def test_order_lines_relationship(self, order_with_lines):
        """Test de la relación Order -> OrderLines"""
        assert order_with_lines.lines.count() == 2
        
        total_items = sum(line.quantity for line in order_with_lines.lines.all())
        assert total_items == 3  # 2 + 1
    
    def test_order_line_cascade_delete(self, order_with_lines):
        """Test que al borrar un pedido se borran sus líneas"""
        from shopify_app.models import OrderLine
        
        order_id = order_with_lines.id
        lines_count = order_with_lines.lines.count()
        
        assert lines_count == 2
        
        # Borrar el pedido
        order_with_lines.delete()
        
        # Verificar que las líneas también se borraron
        remaining_lines = OrderLine.objects.filter(order_id=order_id).count()
        assert remaining_lines == 0


@pytest.mark.unit
class TestProductMappingModel:
    """Tests para el modelo ProductMapping"""
    
    def test_create_product_mapping(self, product_variant, product_mapping_data):
        """Test de creación de mapeo de producto"""
        from shopify_app.models import ProductMapping
        
        mapping = ProductMapping.objects.create(
            variant=product_variant,
            **product_mapping_data
        )
        
        assert mapping.variant == product_variant
        assert mapping.verial_id == product_mapping_data['verial_id']
        assert mapping.verial_barcode == product_mapping_data['verial_barcode']
        assert mapping.last_sync is not None
    
    def test_product_mapping_one_to_one(self, product_mapping, product_variant):
        """Test que el mapeo es OneToOne con ProductVariant"""
        from shopify_app.models import ProductMapping
        
        # Intentar crear otro mapeo para la misma variante debe fallar
        with pytest.raises(IntegrityError):
            ProductMapping.objects.create(
                variant=product_variant,
                verial_id=99999,
                verial_barcode='9999999999999'
            )
    
    def test_access_mapping_from_variant(self, product_variant, product_mapping):
        """Test de acceso al mapeo desde la variante"""
        assert hasattr(product_variant, 'verial_mapping')
        assert product_variant.verial_mapping == product_mapping
    
    def test_product_mapping_str_representation(self, product_mapping):
        """Test del método __str__"""
        expected = f"{product_mapping.variant} → Verial ID: {product_mapping.verial_id}"
        assert str(product_mapping) == expected
    
    def test_product_mapping_auto_update_last_sync(self, product_mapping):
        """Test que last_sync se actualiza automáticamente"""
        old_sync = product_mapping.last_sync
        
        # Esperar un momento y actualizar
        import time
        time.sleep(0.1)
        
        product_mapping.verial_barcode = '9999999999999'
        product_mapping.save()
        
        assert product_mapping.last_sync > old_sync


@pytest.mark.unit
class TestCustomerMappingModel:
    """Tests para el modelo CustomerMapping"""
    
    def test_create_customer_mapping(self, customer, customer_mapping_data):
        """Test de creación de mapeo de cliente"""
        from shopify_app.models import CustomerMapping
        
        mapping = CustomerMapping.objects.create(
            customer=customer,
            **customer_mapping_data
        )
        
        assert mapping.customer == customer
        assert mapping.verial_id == customer_mapping_data['verial_id']
        assert mapping.verial_nif == customer_mapping_data['verial_nif']
    
    def test_customer_mapping_one_to_one(self, customer_mapping, customer):
        """Test que el mapeo es OneToOne con Customer"""
        from shopify_app.models import CustomerMapping
        
        # Intentar crear otro mapeo para el mismo cliente debe fallar
        with pytest.raises(IntegrityError):
            CustomerMapping.objects.create(
                customer=customer,
                verial_id=99999,
                verial_nif='99999999Z'
            )
    
    def test_access_mapping_from_customer(self, customer, customer_mapping):
        """Test de acceso al mapeo desde el cliente"""
        assert hasattr(customer, 'verial_mapping')
        assert customer.verial_mapping == customer_mapping
    
    def test_customer_mapping_str_representation(self, customer_mapping):
        """Test del método __str__"""
        expected = f"{customer_mapping.customer} → Verial ID: {customer_mapping.verial_id}"
        assert str(customer_mapping) == expected


@pytest.mark.unit
class TestOrderMappingModel:
    """Tests para el modelo OrderMapping"""
    
    def test_create_order_mapping(self, order, order_mapping_data):
        """Test de creación de mapeo de pedido"""
        from shopify_app.models import OrderMapping
        
        mapping = OrderMapping.objects.create(
            order=order,
            **order_mapping_data
        )
        
        assert mapping.order == order
        assert mapping.verial_id == order_mapping_data['verial_id']
        assert mapping.verial_referencia == order_mapping_data['verial_referencia']
        assert mapping.verial_numero == order_mapping_data['verial_numero']
        assert mapping.created_at is not None
    
    def test_order_mapping_one_to_one(self, order_mapping, order):
        """Test que el mapeo es OneToOne con Order"""
        from shopify_app.models import OrderMapping
        
        # Intentar crear otro mapeo para el mismo pedido debe fallar
        with pytest.raises(IntegrityError):
            OrderMapping.objects.create(
                order=order,
                verial_id=88888,
                verial_referencia='REF-2',
                verial_numero='NUM-2'
            )
    
    def test_access_mapping_from_order(self, order, order_mapping):
        """Test de acceso al mapeo desde el pedido"""
        assert hasattr(order, 'verial_mapping')
        assert order.verial_mapping == order_mapping
    
    def test_order_mapping_str_representation(self, order_mapping):
        """Test del método __str__"""
        expected = f"{order_mapping.order.name} → Verial ID: {order_mapping.verial_id}"
        assert str(order_mapping) == expected


@pytest.mark.unit
class TestModelQuerySets:
    """Tests para QuerySets y filtros comunes"""
    
    def test_filter_orders_by_status(self, shop):
        """Test de filtrado de pedidos por estado"""
        from shopify_app.models import Order
        
        # Crear pedidos con diferentes estados
        Order.objects.create(
            shop=shop,
            shopify_id=1111,
            name='#1001',
            email='test1@example.com',
            total_price=Decimal('10.00'),
            financial_status='paid',
            status='RECEIVED',
            created_at=timezone.now()
        )
        
        Order.objects.create(
            shop=shop,
            shopify_id=2222,
            name='#1002',
            email='test2@example.com',
            total_price=Decimal('20.00'),
            financial_status='paid',
            status='SENT',
            created_at=timezone.now()
        )
        
        received_orders = Order.objects.filter(status='RECEIVED')
        sent_orders = Order.objects.filter(status='SENT')
        
        assert received_orders.count() == 1
        assert sent_orders.count() == 1
        assert received_orders.first().name == '#1001'
    
    def test_filter_orders_sent_to_verial(self, shop):
        """Test de filtrado de pedidos enviados a Verial"""
        from shopify_app.models import Order
        
        # Crear pedidos
        Order.objects.create(
            shop=shop,
            shopify_id=3333,
            name='#1003',
            email='test3@example.com',
            total_price=Decimal('30.00'),
            financial_status='paid',
            sent_to_verial=True,
            created_at=timezone.now()
        )
        
        Order.objects.create(
            shop=shop,
            shopify_id=4444,
            name='#1004',
            email='test4@example.com',
            total_price=Decimal('40.00'),
            financial_status='paid',
            sent_to_verial=False,
            created_at=timezone.now()
        )
        
        sent = Order.objects.filter(sent_to_verial=True)
        not_sent = Order.objects.filter(sent_to_verial=False)
        
        assert sent.count() == 1
        assert not_sent.count() == 1
    
    def test_filter_products_by_barcode(self, product, product_variant):
        """Test de búsqueda de variantes por código de barras"""
        from shopify_app.models import ProductVariant
        
        variants = ProductVariant.objects.filter(
            barcode=product_variant.barcode
        )
        
        assert variants.count() == 1
        assert variants.first() == product_variant
    
    def test_get_unmapped_products(self, product, product_variant):
        """Test para obtener productos sin mapeo a Verial"""
        from shopify_app.models import ProductVariant, ProductMapping
        
        # Sin mapeo
        unmapped = ProductVariant.objects.filter(verial_mapping__isnull=True)
        assert unmapped.count() == 1
        
        # Crear mapeo
        ProductMapping.objects.create(
            variant=product_variant,
            verial_id=12345,
            verial_barcode=product_variant.barcode
        )
        
        # Ahora no debe aparecer en sin mapear
        unmapped = ProductVariant.objects.filter(verial_mapping__isnull=True)
        assert unmapped.count() == 0
    
    def test_get_orders_with_lines(self, order_with_lines):
        """Test para obtener pedidos con sus líneas"""
        from shopify_app.models import Order
        
        # Obtener pedido con prefetch de líneas (optimización)
        orders = Order.objects.prefetch_related('lines').filter(
            id=order_with_lines.id
        )
        
        order = orders.first()
        assert order.lines.count() == 2
        
        # Calcular total desde líneas
        total_from_lines = sum(line.total for line in order.lines.all())
        assert total_from_lines == Decimal('109.97')  # 2*29.99 + 1*49.99