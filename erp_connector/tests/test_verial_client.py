"""
Tests para el cliente de Verial
"""
import pytest
import responses
from unittest.mock import patch, MagicMock
from decimal import Decimal


@pytest.mark.unit
class TestVerialClientInit:
    """Tests para inicialización del cliente"""
    
    def test_verial_client_initialization(self):
        """Test de inicialización del cliente"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        assert client.server is not None
        assert client.base_url is not None
        assert client.session is not None
        assert client.headers['Content-Type'] == 'application/json'
    
    def test_verial_client_is_configured(self):
        """Test de verificación de configuración"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        # Con settings de test debería estar configurado
        assert client.is_configured() is True


@pytest.mark.integration
class TestVerialClientCustomers:
    """Tests para operaciones de clientes"""
    
    @responses.activate
    def test_find_customer_by_nif_success(self):
        """Test de búsqueda exitosa de cliente por NIF"""
        from erp_connector.verial_client import VerialClient
        from django.conf import settings
        
        client = VerialClient()
        
        # Mock de respuesta
        responses.add(
            responses.GET,
            f'{client.base_url}/GetClientesWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'Clientes': [
                    {
                        'Id': 12345,
                        'NIF': '12345678A',
                        'Nombre': 'Juan Pérez',
                        'Email': 'test@example.com'
                    }
                ]
            },
            status=200
        )
        
        success, customer = client.find_customer_by_nif('12345678A')
        
        assert success is True
        assert customer is not None
        assert customer['NIF'] == '12345678A'
        assert customer['Id'] == 12345
    
    @responses.activate
    def test_find_customer_by_nif_not_found(self):
        """Test de búsqueda de cliente no encontrado"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.GET,
            f'{client.base_url}/GetClientesWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'Clientes': []
            },
            status=200
        )
        
        success, customer = client.find_customer_by_nif('99999999Z')
        
        assert success is True
        assert customer is None
    
    @responses.activate
    def test_create_customer_success(self):
        """Test de creación exitosa de cliente"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.POST,
            f'{client.base_url}/NuevoClienteWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'Id': 12345
            },
            status=200
        )
        
        customer_data = {
            'Nombre': 'Juan Pérez',
            'NIF': '12345678A',
            'Tipo': 1
        }
        
        success, result = client.create_customer(customer_data)
        
        assert success is True
        assert result['Id'] == 12345
    
    @responses.activate
    def test_create_customer_error(self):
        """Test de error al crear cliente"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.POST,
            f'{client.base_url}/NuevoClienteWS',
            json={
                'InfoError': {
                    'Codigo': 1,
                    'Descripcion': 'NIF duplicado'
                }
            },
            status=200
        )
        
        customer_data = {
            'Nombre': 'Juan Pérez',
            'NIF': '12345678A',
            'Tipo': 1
        }
        
        success, error = client.create_customer(customer_data)
        
        assert success is False
        assert 'NIF duplicado' in error


@pytest.mark.integration
class TestVerialClientOrders:
    """Tests para operaciones de pedidos"""
    
    @responses.activate
    def test_create_order_success(self):
        """Test de creación exitosa de pedido"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.POST,
            f'{client.base_url}/NuevoDocClienteWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'Id': 99999,
                'Referencia': 'REF-2024-001',
                'Numero': 'NUM-001'
            },
            status=200
        )
        
        order_data = {
            'Tipo': 5,
            'ID_Cliente': 12345,
            'Contenido': [
                {
                    'IdArticulo': 1001,
                    'Cantidad': 2,
                    'Precio': 29.99
                }
            ]
        }
        
        success, result = client.create_order(order_data)
        
        assert success is True
        assert result['Id'] == 99999
        assert 'Referencia' in result
    
    @responses.activate
    def test_create_order_error(self):
        """Test de error al crear pedido"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.POST,
            f'{client.base_url}/NuevoDocClienteWS',
            json={
                'InfoError': {
                    'Codigo': 1,
                    'Descripcion': 'Cliente no encontrado'
                }
            },
            status=200
        )
        
        order_data = {
            'Tipo': 5,
            'ID_Cliente': 99999,
            'Contenido': []
        }
        
        success, error = client.create_order(order_data)
        
        assert success is False
        assert 'Cliente no encontrado' in error


@pytest.mark.integration
class TestVerialClientArticles:
    """Tests para operaciones de artículos"""
    
    @responses.activate
    def test_get_articles_success(self):
        """Test de obtención exitosa de artículos"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.GET,
            f'{client.base_url}/GetArticulosWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'Articulos': [
                    {
                        'Id': 1001,
                        'ReferenciaBarras': '8412345678901',
                        'Nombre': 'Producto Test',
                        'PVP': 29.99
                    },
                    {
                        'Id': 1002,
                        'ReferenciaBarras': '8412345678902',
                        'Nombre': 'Producto Test 2',
                        'PVP': 49.99
                    }
                ]
            },
            status=200
        )
        
        success, result = client.get_articles()
        
        assert success is True
        assert 'Articulos' in result
        assert len(result['Articulos']) == 2
        assert result['Articulos'][0]['Id'] == 1001
    
    @responses.activate
    def test_get_articles_empty(self):
        """Test de obtención de artículos vacía"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.GET,
            f'{client.base_url}/GetArticulosWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'Articulos': []
            },
            status=200
        )
        
        success, result = client.get_articles()
        
        assert success is True
        assert result['Articulos'] == []


@pytest.mark.integration
class TestVerialClientStock:
    """Tests para operaciones de stock"""
    
    @responses.activate
    def test_get_stock_all(self):
        """Test de obtención de todo el stock"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.GET,
            f'{client.base_url}/GetStockArticulosWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'StockArticulos': [
                    {
                        'IdArticulo': 1001,
                        'Stock': 100
                    },
                    {
                        'IdArticulo': 1002,
                        'Stock': 50
                    }
                ]
            },
            status=200
        )
        
        success, result = client.get_stock(id_articulo=0)
        
        assert success is True
        assert 'StockArticulos' in result
        assert len(result['StockArticulos']) == 2
    
    @responses.activate
    def test_get_stock_specific_article(self):
        """Test de obtención de stock de artículo específico"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.GET,
            f'{client.base_url}/GetStockArticulosWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'StockArticulos': [
                    {
                        'IdArticulo': 1001,
                        'Stock': 100
                    }
                ]
            },
            status=200
        )
        
        success, result = client.get_stock(id_articulo=1001)
        
        assert success is True
        assert len(result['StockArticulos']) == 1
        assert result['StockArticulos'][0]['IdArticulo'] == 1001


@pytest.mark.integration
class TestVerialClientErrorHandling:
    """Tests para manejo de errores"""
    
    @responses.activate
    def test_connection_error(self):
        """Test de error de conexión"""
        from erp_connector.verial_client import VerialClient
        import requests
        
        client = VerialClient()
        
        responses.add(
            responses.GET,
            f'{client.base_url}/GetArticulosWS',
            body=requests.exceptions.ConnectionError('Connection failed')
        )
        
        success, error = client.get_articles()
        
        assert success is False
        assert 'Connection failed' in str(error) or 'Error conexión' in str(error)
    
    @responses.activate
    def test_server_error_500(self):
        """Test de error 500 del servidor"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.GET,
            f'{client.base_url}/GetArticulosWS',
            json={'error': 'Internal Server Error'},
            status=500
        )
        
        success, error = client.get_articles()
        
        assert success is False
        assert '500' in str(error)
    
    @responses.activate
    def test_invalid_json_response(self):
        """Test de respuesta con JSON inválido"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.GET,
            f'{client.base_url}/GetArticulosWS',
            body='invalid json {[',
            status=200
        )
        
        success, error = client.get_articles()
        
        assert success is False
        assert 'no JSON' in error or 'JSON' in error
    
    @responses.activate
    def test_verial_api_error_code(self):
        """Test de código de error de Verial"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        responses.add(
            responses.GET,
            f'{client.base_url}/GetArticulosWS',
            json={
                'InfoError': {
                    'Codigo': 1,
                    'Descripcion': 'Sesión inválida'
                }
            },
            status=200
        )
        
        success, error = client.get_articles()
        
        assert success is False
        assert 'Sesión inválida' in error


@pytest.mark.unit
class TestVerialClientPrivateMethods:
    """Tests para métodos privados"""
    
    @responses.activate
    def test_post_method_injects_session(self):
        """Test que _post inyecta la sesión correctamente"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        def request_callback(request):
            # Verificar que el payload tiene sesionwcf
            import json
            payload = json.loads(request.body)
            assert 'sesionwcf' in payload
            assert payload['sesionwcf'] == client.session
            
            return (200, {}, json.dumps({
                'InfoError': {'Codigo': 0, 'Descripcion': None}
            }))
        
        responses.add_callback(
            responses.POST,
            f'{client.base_url}/TestEndpoint',
            callback=request_callback
        )
        
        success, response = client._post('TestEndpoint', {'test': 'data'})
        
        assert success is True
    
    @responses.activate
    def test_post_method_uses_online_session(self):
        """Test que _post usa online_session cuando se indica"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        def request_callback(request):
            import json
            payload = json.loads(request.body)
            assert 'sesionwcf' in payload
            assert payload['sesionwcf'] == client.online_session
            
            return (200, {}, json.dumps({
                'InfoError': {'Codigo': 0, 'Descripcion': None}
            }))
        
        responses.add_callback(
            responses.POST,
            f'{client.base_url}/TestEndpoint',
            callback=request_callback
        )
        
        success, response = client._post('TestEndpoint', {'test': 'data'}, use_online_session=True)
        
        assert success is True


@pytest.mark.integration
class TestVerialClientRealWorldScenarios:
    """Tests de escenarios del mundo real"""
    
    @responses.activate
    def test_complete_order_flow(self):
        """Test de flujo completo: buscar cliente -> crear pedido"""
        from erp_connector.verial_client import VerialClient
        
        client = VerialClient()
        
        # 1. Buscar cliente
        responses.add(
            responses.GET,
            f'{client.base_url}/GetClientesWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'Clientes': [
                    {
                        'Id': 12345,
                        'NIF': '12345678A',
                        'Nombre': 'Juan Pérez'
                    }
                ]
            },
            status=200
        )
        
        # 2. Crear pedido
        responses.add(
            responses.POST,
            f'{client.base_url}/NuevoDocClienteWS',
            json={
                'InfoError': {'Codigo': 0, 'Descripcion': None},
                'Id': 99999,
                'Referencia': 'REF-001'
            },
            status=200
        )
        
        # Ejecutar flujo
        success, customer = client.find_customer_by_nif('12345678A')
        assert success is True
        
        order_data = {
            'Tipo': 5,
            'ID_Cliente': customer['Id'],
            'Contenido': []
        }
        
        success, order = client.create_order(order_data)
        assert success is True
        assert order['Id'] == 99999