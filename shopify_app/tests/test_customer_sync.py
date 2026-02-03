"""
Tests para sincronización de clientes con Verial
"""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal


@pytest.mark.unit
class TestBuildCustomerPayload:
    """Tests para construcción de payload de cliente"""
    
    def test_build_customer_payload_basic(self, customer):
        """Test de construcción básica de payload"""
        from shopify_app.services.customer_sync import build_customer_payload
        
        payload = build_customer_payload(customer)
        
        assert payload['Tipo'] == 1  # Persona física
        assert payload['Nombre'] == customer.first_name
        assert payload['Apellido1'] == 'Pérez'
        assert payload['Email'] == customer.email
        assert payload['Activo'] is True
    
    def test_build_customer_payload_with_two_surnames(self, shop):
        """Test con dos apellidos"""
        from shopify_app.models import Customer
        from shopify_app.services.customer_sync import build_customer_payload
        
        customer = Customer.objects.create(
            shop=shop,
            shopify_id=6666666666,
            email='test2@example.com',
            first_name='María',
            last_name='García López',
            created_at='2024-01-01T00:00:00Z'
        )
        
        payload = build_customer_payload(customer)
        
        assert payload['Nombre'] == 'María'
        assert payload['Apellido1'] == 'García'
        assert payload['Apellido2'] == 'López'
    
    def test_build_customer_payload_empresa(self, shop):
        """Test para cliente empresa"""
        from shopify_app.models import Customer
        from shopify_app.services.customer_sync import build_customer_payload
        
        customer = Customer.objects.create(
            shop=shop,
            shopify_id=7777777777,
            email='empresa@example.com',
            first_name='Acme',
            last_name='Corporation',
            created_at='2024-01-01T00:00:00Z'
        )
        
        # Simular que es empresa (normalmente vendría de otro campo)
        customer.company = 'Acme Corp'
        
        payload = build_customer_payload(customer)
        
        assert payload['Tipo'] == 2  # Empresa
        assert 'RazonSocial' in payload


@pytest.mark.integration
class TestGetOrCreateVerialCustomer:
    """Tests para obtener o crear cliente en Verial"""
    
    def test_get_customer_from_existing_mapping(self, customer, customer_mapping):
        """Test cuando ya existe mapping local"""
        from shopify_app.services.customer_sync import get_or_create_verial_customer
        
        success, verial_id = get_or_create_verial_customer(customer)
        
        assert success is True
        assert verial_id == customer_mapping.verial_id
    
    @patch('shopify_app.services.customer_sync.VerialClient')
    def test_find_customer_by_nif(self, mock_client_class, shop):
        """Test de búsqueda por NIF en Verial"""
        from shopify_app.models import Customer, CustomerMapping
        from shopify_app.services.customer_sync import get_or_create_verial_customer
        
        # Cliente sin mapping
        customer = Customer.objects.create(
            shop=shop,
            shopify_id=8888888888,
            email='nif@example.com',
            first_name='Test',
            last_name='NIF',
            created_at='2024-01-01T00:00:00Z'
        )
        customer.nif = '12345678A'
        
        # Mock Verial client
        mock_client = MagicMock()
        mock_client.find_customer_by_nif.return_value = (True, {
            'Id': 54321,
            'NIF': '12345678A'
        })
        mock_client_class.return_value = mock_client
        
        success, verial_id = get_or_create_verial_customer(customer)
        
        assert success is True
        assert verial_id == 54321
        
        # Verificar que se creó el mapping
        mapping = CustomerMapping.objects.filter(customer=customer).first()
        assert mapping is not None
        assert mapping.verial_id == 54321
    
    @patch('shopify_app.services.customer_sync.VerialClient')
    def test_create_new_customer(self, mock_client_class, customer):
        """Test de creación de nuevo cliente"""
        from shopify_app.models import CustomerMapping
        from shopify_app.services.customer_sync import get_or_create_verial_customer
        
        # Mock Verial client
        mock_client = MagicMock()
        mock_client.find_customer_by_nif.return_value = (False, None)
        mock_client.create_customer.return_value = (True, {
            'Clientes': [{'Id': 99999}]
        })
        mock_client_class.return_value = mock_client
        
        success, verial_id = get_or_create_verial_customer(customer)
        
        assert success is True
        assert verial_id == 99999
        
        # Verificar mapping
        mapping = CustomerMapping.objects.filter(customer=customer).first()
        assert mapping is not None
    
    @patch('shopify_app.services.customer_sync.VerialClient')
    def test_create_customer_error(self, mock_client_class, customer):
        """Test cuando falla creación en Verial"""
        from shopify_app.services.customer_sync import get_or_create_verial_customer
        
        mock_client = MagicMock()
        mock_client.find_customer_by_nif.return_value = (False, None)
        mock_client.create_customer.return_value = (False, "Error de Verial")
        mock_client_class.return_value = mock_client
        
        success, verial_id = get_or_create_verial_customer(customer)
        
        assert success is False
        assert verial_id == 0


@pytest.mark.integration
class TestEnsureCustomerInVerial:
    """Tests para ensure_customer_in_verial"""
    
    @patch('shopify_app.services.customer_sync.get_or_create_verial_customer')
    def test_ensure_customer_success(self, mock_get_or_create, order, customer):
        """Test exitoso de ensure_customer_in_verial"""
        from shopify_app.services.customer_sync import ensure_customer_in_verial
        
        # Configurar order con email del customer
        order.email = customer.email
        order.save()
        
        mock_get_or_create.return_value = (True, 12345)
        
        success, verial_id = ensure_customer_in_verial(order)
        
        assert success is True
        assert verial_id == 12345
    
    def test_ensure_customer_not_found(self, order):
        """Test cuando no se encuentra el customer"""
        from shopify_app.services.customer_sync import ensure_customer_in_verial
        
        # Order con email que no existe
        order.email = 'noexiste@example.com'
        order.save()
        
        success, error = ensure_customer_in_verial(order)
        
        assert success is False
        assert 'no encontrado' in error


@pytest.mark.integration
class TestCustomerSyncIntegration:
    """Tests de integración completa"""
    
    @patch('shopify_app.services.customer_sync.VerialClient')
    def test_complete_customer_flow(self, mock_client_class, shop, order):
        """Test de flujo completo: buscar -> no encontrar -> crear"""
        from shopify_app.models import Customer, CustomerMapping
        from shopify_app.services.customer_sync import ensure_customer_in_verial
        
        # Crear customer
        customer = Customer.objects.create(
            shop=shop,
            shopify_id=9999999999,
            email='flujo@example.com',
            first_name='Flujo',
            last_name='Test',
            created_at='2024-01-01T00:00:00Z'
        )
        
        order.email = customer.email
        order.save()
        
        # Mock client
        mock_client = MagicMock()
        mock_client.find_customer_by_nif.return_value = (False, None)
        mock_client.create_customer.return_value = (True, {
            'Clientes': [{'Id': 88888}]
        })
        mock_client_class.return_value = mock_client
        
        success, verial_id = ensure_customer_in_verial(order)
        
        assert success is True
        assert verial_id == 88888
        
        # Verificar que se creó mapping
        mapping = CustomerMapping.objects.filter(customer=customer).first()
        assert mapping is not None
        assert mapping.verial_id == 88888


@pytest.mark.unit
class TestCustomerPayloadValidation:
    """Tests de validación de payload"""
    
    def test_payload_field_lengths(self, customer):
        """Test que los campos respetan longitudes máximas"""
        from shopify_app.services.customer_sync import build_customer_payload
        
        # Customer con datos muy largos
        customer.first_name = 'A' * 100
        customer.last_name = 'B' * 100
        customer.email = 'test@' + 'x' * 200 + '.com'
        
        payload = build_customer_payload(customer)
        
        assert len(payload['Nombre']) <= 50
        assert len(payload['Apellido1']) <= 50
        assert len(payload['Email']) <= 100
    
    def test_payload_required_fields(self, customer):
        """Test que el payload tiene todos los campos requeridos"""
        from shopify_app.services.customer_sync import build_customer_payload
        
        payload = build_customer_payload(customer)
        
        required_fields = [
            'Tipo', 'NIF', 'Nombre', 'Apellido1', 'Apellido2',
            'RazonSocial', 'Email', 'ID_Pais', 'ID_Tarifa',
            'ID_FormaPago', 'Activo', 'Direccion', 'Localidad',
            'Provincia', 'CPostal'
        ]
        
        for field in required_fields:
            assert field in payload
    
    def test_payload_with_empty_customer(self, shop):
        """Test con customer con campos vacíos"""
        from shopify_app.models import Customer
        from shopify_app.services.customer_sync import build_customer_payload
        
        customer = Customer.objects.create(
            shop=shop,
            shopify_id=1010101010,
            email='',
            first_name='',
            last_name='',
            created_at='2024-01-01T00:00:00Z'
        )
        
        payload = build_customer_payload(customer)
        
        # No debería fallar con campos vacíos
        assert payload['Nombre'] == ''
        assert payload['Email'] == ''


@pytest.mark.integration
class TestCustomerMappingPersistence:
    """Tests de persistencia de mappings"""
    
    @patch('shopify_app.services.customer_sync.VerialClient')
    def test_mapping_persists_across_calls(self, mock_client_class, customer):
        """Test que el mapping persiste entre llamadas"""
        from shopify_app.models import CustomerMapping
        from shopify_app.services.customer_sync import get_or_create_verial_customer
        
        mock_client = MagicMock()
        mock_client.find_customer_by_nif.return_value = (False, None)
        mock_client.create_customer.return_value = (True, {
            'Clientes': [{'Id': 77777}]
        })
        mock_client_class.return_value = mock_client
        
        # Primera llamada - crea mapping
        success1, verial_id1 = get_or_create_verial_customer(customer)
        
        # Segunda llamada - debe usar mapping existente
        success2, verial_id2 = get_or_create_verial_customer(customer)
        
        assert success1 is True
        assert success2 is True
        assert verial_id1 == verial_id2 == 77777
        
        # Solo debe haber un mapping
        mappings = CustomerMapping.objects.filter(customer=customer)
        assert mappings.count() == 1