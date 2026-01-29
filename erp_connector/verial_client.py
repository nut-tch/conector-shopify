import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger("verial")


class VerialClient:
    def __init__(self):
        self.server = settings.VERIAL_SERVER
        self.base_url = f"http://{self.server}/WcfServiceLibraryVerial"
        self.session = settings.VERIAL_SESSION
        self.online_session = getattr(settings, 'VERIAL_ONLINE_SESSION', 15)
        self.headers = {
            "Content-Type": "Application/json"
        }

    def is_configured(self):
        return bool(self.server and self.session)

    def _post(self, endpoint: str, payload: dict, use_online_session: bool = False):
        """
        Realiza petición POST a Verial.
        
        Args:
            endpoint: Nombre del endpoint (sin la URL base)
            payload: Datos a enviar
            use_online_session: Si True, usa la sesión online (para pedidos de tienda)
        """
        if not self.is_configured():
            return False, "Verial no configurado"

        url = f"{self.base_url}/{endpoint}"
        payload = payload.copy()
        payload["sesionwcf"] = self.online_session if use_online_session else self.session

        try:
            # IMPORTANTE: usar data=json.dumps(), no json=
            response = requests.post(
                url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=30
            )
            return True, response
        except requests.exceptions.RequestException as e:
            logger.error(f"Error conexión Verial [{endpoint}]: {e}")
            return False, f"Error conexión Verial: {e}"

    def _handle_response(self, response):
        """Procesa la respuesta de Verial."""
        try:
            data = response.json()
        except Exception:
            return False, f"Respuesta no JSON ({response.status_code})"

        info = data.get("InfoError")
        if info and info.get("Codigo") not in (0, None):
            return False, info.get("Descripcion", "Error Verial")

        return True, data

    def create_customer(self, customer_data: dict):
        """Crea o actualiza un cliente en Verial."""
        success, response = self._post("NuevoClienteWS", customer_data)
        if not success:
            return False, response
        return self._handle_response(response)

    def create_order(self, order_data: dict):
        """
        Crea un pedido en Verial.
        Usa la sesión online para pedidos de tienda.
        
        Returns:
            (True, data) donde data contiene 'Id', 'Numero', etc.
            (False, error_message) en caso de error
        """
        success, response = self._post(
            "NuevoDocClienteWS", 
            order_data, 
            use_online_session=True
        )
        if not success:
            return False, response
        return self._handle_response(response)

    def get_orders_status(self, pedidos: list):
        """
        Consulta el estado de pedidos en Verial.
        
        Args:
            pedidos: Lista de dicts con 'Id' (verial_id)
                    Ejemplo: [{'Id': 57654}, {'Id': 57655}]
        
        Returns:
            (True, data) donde data['Pedidos'] contiene los estados
            (False, error_message) en caso de error
        
        Estados Verial:
            0 = No existe
            1 = Recibido/Creado
            2 = En preparación
            3 = Preparado
            4 = Enviado (completado)
        """
        payload = {"Pedidos": pedidos}
        success, response = self._post(
            "EstadoPedidosWS", 
            payload,
            use_online_session=True
        )
        if not success:
            return False, response
        return self._handle_response(response)

    # === Métodos auxiliares para otros usos ===
    
    def get_articles(self):
        """Obtiene todos los artículos de Verial."""
        url = f"{self.base_url}/GetArticulosWS?x={self.session}"
        try:
            response = requests.get(url, timeout=30)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo artículos: {e}")
            return False, str(e)

    def get_stock(self, id_articulo: int = 0):
        """Obtiene el stock de artículos."""
        url = f"{self.base_url}/GetStockArticulosWS?x={self.session}&id_articulo={id_articulo}"
        try:
            response = requests.get(url, timeout=30)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo stock: {e}")
            return False, str(e)