"""
Tests para envío de pedidos a Verial
"""
import pytest
import responses
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock
from django.utils import timezone


@pytest.mark.unit
class TestGetLineMapping:
    """Tests para mapeo de líneas de pedido"""
    
    def test_get_line_mapping_by_sku(self, product_variant, product_mapping, order_line):
        """Test de mapeo de línea por SKU"""
        from shopify_app.order_to_verial import get_line_mapping
        
        # Actualizar SKU de la línea para que coincida
        order_line.sku = product_variant.sku
        order_line.save()
        
        mapping = get_line_mapping(order_line)
        
        assert mapping is not None
        assert mapping.variant == product_variant
        assert mapping.verial_id == product_mapping.verial_id
    
    def test_get_line_mapping_by_product_and_variant_title(self, product, product_variant, product_mapping, order):
        """Test de mapeo por título de producto y variante"""
        from shopify_app.models import OrderLine
        from shopify_app.order_to_verial import get_line_mapping
        
        line = OrderLine.objects.create(
            order=order,
            shopify_id=9999999999,
            product_title=product.title,
            variant_title=product_variant.title,
            sku='',  # Sin SKU
            quantity=1,
            price=Decimal('10.00')
        )
        
        mapping = get_line_mapping(line)
        
        assert mapping is not None
        assert mapping.variant == product_variant
    
    def test_get_line_mapping_not_found(self, order_line):
        """Test cuando no se encuentra mapeo"""
        from shopify_app.order_to_verial import get_line_mapping
        
        # Línea sin SKU válido ni título que coincida
        order_line.sku = 'INEXISTENTE'
        order_line.product_title = 'Producto Inexistente'
        order_line.save()
        
        mapping = get_line_mapping(order_line)
        
        assert mapping is None


@pytest.mark.unit
class TestBuildOrderPayload:
    """Tests para construcción de payload de pedido"""
    
    def test_build_order_payload_success(self, order_with_lines, product_variant, product_mapping):
        """Test de construcción exitosa de payload"""
        from shopify_app.order_to_verial import build_order_payload
        
        # Asegurar que las líneas tengan SKU válido
        for line in order_with_lines.lines.all():
            line.sku = product_variant.sku
            line.save()
        
        payload = build_order_payload(order_with_lines, id_cliente=12345)
        
        assert payload['Tipo'] == 5
        assert payload['ID_Cliente'] == 12345
        assert 'Fecha' in payload
        assert payload['Referencia'].startswith('S')
        assert 'Contenido' in payload
        assert len(payload['Contenido']) == 2
        assert payload['Contenido'][0]['ID_Articulo'] == product_mapping.verial_id
    
    def test_build_order_payload_without_mapping(self, order_with_lines):
        """Test que falla cuando falta mapeo de producto"""
        from shopify_app.order_to_verial import build_order_payload, OrderToVerialError
        
        # Las líneas no tienen mapeo
        with pytest.raises(OrderToVerialError) as exc_info:
            build_order_payload(order_with_lines, id_cliente=12345)
        
        assert 'sin mapear' in str(exc_info.value)
    
    def test_build_order_payload_structure(self, order, product_variant, product_mapping, order_line):
        """Test de estructura correcta del payload"""
        from shopify_app.order_to_verial import build_order_payload
        
        # Configurar línea con mapping
        order_line.sku = product_variant.sku
        order_line.save()
        
        payload = build_order_payload(order, id_cliente=12345)
        
        # Verificar estructura
        assert 'Tipo' in payload
        assert 'ID_Cliente' in payload
        assert 'Fecha' in payload
        assert 'Referencia' in payload
        assert 'TotalImporte' in payload
        assert 'PreciosImpIncluidos' in payload
        assert 'Contenido' in payload
        assert 'Pagos' in payload
        
        # Verificar línea
        linea = payload['Contenido'][0]
        assert linea['TipoRegistro'] == 1
        assert 'ID_Articulo' in linea
        assert 'Uds' in linea
        assert 'Precio' in linea
        assert 'PorcentajeIVA' in linea


@pytest.mark.integration
class TestSendOrderToVerial:
    """Tests para envío de pedidos a Verial"""
    
    @patch('shopify_app.order_to_verial.ensure_customer_in_verial')
    @patch('shopify_app.order_to_verial.VerialClient')
    def test_send_order_success(self, mock_client_class, mock_ensure_customer, 
                                order, product_variant, product_mapping, order_line):
        """Test de envío exitoso de pedido"""
        from shopify_app.order_to_verial import send_order_to_verial
        from shopify_app.models import OrderMapping
        
        # Mock customer
        mock_ensure_customer.return_value = (True, 12345)
        
        # Mock Verial client
        mock_client = MagicMock()
        mock_client.create_order.return_value = (True, {
            'Id': 99999,
            'Referencia': f'S{order.name}'
        })
        mock_client_class.return_value = mock_client
        
        # Configurar línea con mapping
        order_line.sku = product_variant.sku
        order_line.save()
        
        success, message = send_order_to_verial(order)
        
        assert success is True
        assert 'correctamente' in message
        
        # Verificar que se creó el mapping
        mapping = OrderMapping.objects.filter(order=order).first()
        assert mapping is not None
        assert mapping.verial_id == 99999
        
        # Verificar que se actualizó el pedido
        order.refresh_from_db()
        assert order.sent_to_verial is True
        assert order.sent_to_verial_at is not None
    
    @patch('shopify_app.order_to_verial.ensure_customer_in_verial')
    def test_send_order_customer_error(self, mock_ensure_customer, order):
        """Test cuando falla obtención de cliente"""
        from shopify_app.order_to_verial import send_order_to_verial
        
        mock_ensure_customer.return_value = (False, "Cliente no encontrado")
        
        success, error = send_order_to_verial(order)
        
        assert success is False
        assert 'Cliente' in error
    
    @patch('shopify_app.order_to_verial.ensure_customer_in_verial')
    def test_send_order_product_not_mapped(self, mock_ensure_customer, order_with_lines):
        """Test cuando productos no están mapeados"""
        from shopify_app.order_to_verial import send_order_to_verial
        
        mock_ensure_customer.return_value = (True, 12345)
        
        success, error = send_order_to_verial(order_with_lines)
        
        assert success is False
        assert 'sin mapear' in error
    
    @patch('shopify_app.order_to_verial.ensure_customer_in_verial')
    @patch('shopify_app.order_to_verial.VerialClient')
    def test_send_order_verial_error(self, mock_client_class, mock_ensure_customer,
                                     order, product_variant, product_mapping, order_line):
        """Test cuando Verial retorna error"""
        from shopify_app.order_to_verial import send_order_to_verial
        
        mock_ensure_customer.return_value = (True, 12345)
        
        mock_client = MagicMock()
        mock_client.create_order.return_value = (False, "Error en Verial")
        mock_client_class.return_value = mock_client
        
        order_line.sku = product_variant.sku
        order_line.save()
        
        success, error = send_order_to_verial(order)
        
        assert success is False
        assert 'Error en Verial' in error


@pytest.mark.integration
class TestOrderToVerialIntegration:
    """Tests de integración completa"""
    
    @patch('shopify_app.services.customer_sync.VerialClient')
    @patch('shopify_app.order_to_verial.VerialClient')
    def test_complete_order_flow(self, mock_order_client_class, mock_customer_client_class,
                                 shop, customer, order, product_variant, product_mapping, order_line):
        """Test de flujo completo: cliente + pedido"""
        from shopify_app.order_to_verial import send_order_to_verial
        from shopify_app.models import CustomerMapping, OrderMapping
        
        # Mock customer client
        mock_customer_client = MagicMock()
        mock_customer_client.find_customer_by_nif.return_value = (False, None)
        mock_customer_client.create_customer.return_value = (True, {
            'Clientes': [{'Id': 12345}]
        })
        mock_customer_client_class.return_value = mock_customer_client
        
        # Mock order client
        mock_order_client = MagicMock()
        mock_order_client.create_order.return_value = (True, {
            'Id': 99999,
            'Referencia': f'S{order.name}'
        })
        mock_order_client_class.return_value = mock_order_client
        
        # Configurar datos
        order.email = customer.email
        order.save()
        
        order_line.sku = product_variant.sku
        order_line.save()
        
        # Ejecutar
        success, message = send_order_to_verial(order)
        
        assert success is True
        
        # Verificar mappings
        customer_mapping = CustomerMapping.objects.filter(customer=customer).first()
        assert customer_mapping is not None
        assert customer_mapping.verial_id == 12345
        
        order_mapping = OrderMapping.objects.filter(order=order).first()
        assert order_mapping is not None
        assert order_mapping.verial_id == 99999


@pytest.mark.unit
class TestOrderToVerialError:
    """Tests para excepciones personalizadas"""
    
    def test_order_to_verial_error_raised(self):
        """Test que se puede lanzar OrderToVerialError"""
        from shopify_app.order_to_verial import OrderToVerialError
        
        with pytest.raises(OrderToVerialError) as exc_info:
            raise OrderToVerialError("Test error")
        
        assert "Test error" in str(exc_info.value)


@pytest.mark.integration
class TestOrderValidation:
    """Tests de validación de pedidos antes de enviar"""
    
    def test_order_without_lines(self, order):
        """Test de pedido sin líneas"""
        from shopify_app.order_to_verial import build_order_payload
        
        # Pedido sin líneas debería tener Contenido vacío
        payload = build_order_payload(order, id_cliente=12345)
        
        assert payload['Contenido'] == []
    
    @patch('shopify_app.order_to_verial.ensure_customer_in_verial')
    @patch('shopify_app.order_to_verial.VerialClient')
    def test_order_creates_mapping_only_once(self, mock_client_class, mock_ensure_customer,
                                             order, product_variant, product_mapping, order_line):
        """Test que no se duplica el mapping al enviar varias veces"""
        from shopify_app.order_to_verial import send_order_to_verial
        from shopify_app.models import OrderMapping
        
        mock_ensure_customer.return_value = (True, 12345)
        
        mock_client = MagicMock()
        mock_client.create_order.return_value = (True, {
            'Id': 99999,
            'Referencia': f'S{order.name}'
        })
        mock_client_class.return_value = mock_client
        
        order_line.sku = product_variant.sku
        order_line.save()
        
        # Enviar dos veces
        send_order_to_verial(order)
        send_order_to_verial(order)
        
        # Solo debe haber un mapping
        mappings = OrderMapping.objects.filter(order=order)
        assert mappings.count() == 1


@pytest.mark.integration
class TestOrderLineMapping:
    """Tests específicos para mapeo de líneas"""
    
    def test_multiple_lines_with_different_mappings(self, order, product, shop):
        """Test de pedido con múltiples líneas con diferentes productos"""
        from shopify_app.models import ProductVariant, ProductMapping, OrderLine
        from shopify_app.order_to_verial import build_order_payload
        
        # Crear dos variantes con mappings
        variant1 = ProductVariant.objects.create(
            product=product,
            shopify_id=1111111111,
            title='Variant 1',
            sku='SKU-1',
            barcode='111111',
            price=Decimal('10.00')
        )
        
        variant2 = ProductVariant.objects.create(
            product=product,
            shopify_id=2222222222,
            title='Variant 2',
            sku='SKU-2',
            barcode='222222',
            price=Decimal('20.00')
        )
        
        mapping1 = ProductMapping.objects.create(
            variant=variant1,
            verial_id=1001,
            verial_barcode='111111'
        )
        
        mapping2 = ProductMapping.objects.create(
            variant=variant2,
            verial_id=1002,
            verial_barcode='222222'
        )
        
        # Crear líneas
        OrderLine.objects.create(
            order=order,
            shopify_id=7777,
            product_title='Product 1',
            sku='SKU-1',
            quantity=2,
            price=Decimal('10.00')
        )
        
        OrderLine.objects.create(
            order=order,
            shopify_id=8888,
            product_title='Product 2',
            sku='SKU-2',
            quantity=1,
            price=Decimal('20.00')
        )
        
        payload = build_order_payload(order, id_cliente=12345)
        
        assert len(payload['Contenido']) == 2
        assert payload['Contenido'][0]['ID_Articulo'] == 1001
        assert payload['Contenido'][1]['ID_Articulo'] == 1002