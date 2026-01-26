import os
import json
import logging
import requests

logger = logging.getLogger('verial')


class VerialClient:
    """
    Cliente para conectar con el webservice de Verial.
    """
    
    def __init__(self):
        self.server = os.getenv("VERIAL_SERVER", "")
        self.session = os.getenv("VERIAL_SESSION", "")
        self.online_session = os.getenv("VERIAL_ONLINE_SESSION", "")
        self.base_url = f"http://{self.server}/WcfServiceLibraryVerial"
    
    def is_configured(self):
        """Verifica si las credenciales están configuradas."""
        return bool(self.server and self.session)
    
    def _get(self, endpoint, params=""):
        """Petición GET al webservice."""
        if not self.is_configured():
            return False, "Verial no configurado"
        
        url = f"{self.base_url}/{endpoint}?x={self.session}{params}"
        
        try:
            r = requests.get(url, timeout=30)
            return self._handle_response(r)
        except Exception as e:
            logger.error(f"GET {endpoint} -> Error: {e}")
            return False, str(e)
    
    def _post(self, endpoint, payload, use_online_session=False):
        """Petición POST al webservice."""
        if not self.is_configured():
            return False, "Verial no configurado"
        
        url = f"{self.base_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        # Usar sesión de tienda online para pedidos web
        session = self.online_session if use_online_session else self.session
        payload["sesionwcf"] = session
        
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            return self._handle_response(r)
        except Exception as e:
            logger.error(f"POST {endpoint} -> Error: {e}")
            return False, str(e)
    
    def _handle_response(self, response):
        """Procesa la respuesta del webservice."""
        if response.ok:
            data = response.json()
            if data.get("InfoError", {}).get("Codigo") == 0:
                return True, data
            else:
                error_msg = data.get("InfoError", {}).get("Descripcion", "Error desconocido")
                return False, error_msg
        return False, f"{response.status_code} {response.reason}"
    
    # ==================== MÉTODOS DE LECTURA ====================
    
    def get_products(self):
        """Obtener todos los productos de Verial."""
        return self._get("GetArticulosWS")
    
    def get_stock(self, product_id=0):
        """Obtener stock de productos."""
        return self._get("GetStockArticulosWS", f"&id_articulo={product_id}")
    
    def get_customers(self, customer_id=0, nif=None):
        """Obtener clientes de Verial."""
        params = f"&id_cliente={customer_id}"
        if nif:
            params += f"&nif={nif}"
        return self._get("GetClientesWS", params)
    
    def get_countries(self):
        """Obtener países."""
        return self._get("GetPaisesWS")
    
    def get_states(self):
        """Obtener provincias."""
        return self._get("GetProvinciasWS")
    
    def get_cities(self):
        """Obtener localidades."""
        return self._get("GetLocalidadesWS")
    
    # ==================== MÉTODOS DE ESCRITURA ====================
    
    def create_customer(self, customer_data):
        """
        Crear o actualizar cliente en Verial.
        
        customer_data = {
            "Tipo": 1,  # 1=Persona, 2=Empresa
            "NIF": "12345678A",
            "Nombre": "Juan",
            "Apellido1": "García",
            "Apellido2": "López",
            "RazonSocial": "",
            "ID_Pais": 1,
            "Provincia": "Madrid",
            "Localidad": "Madrid",
            "CPostal": "28001",
            "Direccion": "Calle Principal 1",
            "Telefono": "912345678",
            "Email": "email@ejemplo.com",
            "Id": None  # Si existe, actualiza; si no, crea nuevo
        }
        """
        return self._post("NuevoClienteWS", customer_data)
    
    def create_shipping_address(self, address_data):
        """
        Crear dirección de envío en Verial.
        
        address_data = {
            "ID_Cliente": 123,
            "Nombre": "Juan García",
            "Apellido1": "",
            "Apellido2": "",
            "ID_Pais": 1,
            "Provincia": "Madrid",
            "Localidad": "Madrid",
            "CPostal": "28001",
            "Direccion": "Calle Envío 2",
            "Telefono": "912345678",
            "Email": "email@ejemplo.com",
            "Comentario": "Dejar en portería"
        }
        """
        return self._post("NuevaDireccionEnvioWS", address_data)
    
    def create_order(self, order_data):
        """
        Crear pedido en Verial.
        
        order_data = {
            "Tipo": 5,  # 5 = Pedido
            "Referencia": "#3814",
            "Fecha": "2024-01-23",
            "ID_Cliente": 123,
            "ID_DireccionEnvio": 456,  # Opcional
            "PreciosImpIncluidos": True,
            "BaseImponible": 45.50,
            "TotalImporte": 55.00,
            "Comentario": "Notas del pedido",
            "Contenido": [
                {
                    "TipoRegistro": 1,
                    "ID_Articulo": 789,
                    "Uds": 2,
                    "Precio": 22.75,
                    "Dto": 0,
                    "PorcentajeIVA": 21.00
                }
            ],
            "Pagos": [
                {
                    "ID_MetodoPago": 1,
                    "Fecha": "2024-01-23",
                    "Importe": 55.00
                }
            ]
        }
        """
        return self._post("NuevoDocClienteWS", order_data, use_online_session=True)
    
    def get_order_status(self, order_ids):
        """
        Consultar estado de pedidos.
        
        order_ids = [{"Id": 123}, {"Id": 456}]
        
        Estados:
        1 = Pendiente
        2, 3 = En proceso
        4 = Completado
        """
        payload = {"Pedidos": order_ids}
        return self._post("EstadoPedidosWS", payload)
    
    # ==================== MÉTODO DE TEST ====================
    
    def test_connection(self):
        """Probar conexión con Verial."""
        if not self.is_configured():
            return False, "Credenciales no configuradas"
        
        success, result = self.get_countries()
        if success:
            return True, "Conexión exitosa"
        return False, result