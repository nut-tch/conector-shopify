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
        self.online_session = getattr(settings, 'VERIAL_ONLINE_SESSION', "15") # Token 15 para pedidos
        self.headers = {
            "Content-Type": "application/json"
        }

    def is_configured(self):
        return bool(self.server and self.session)

    def _post(self, endpoint: str, payload: dict, use_online_session: bool = False):
        """Realiza petición POST inyectando la sesión dentro del JSON."""
        if not self.is_configured():
            return False, "Verial no configurado"

        url = f"{self.base_url}/{endpoint}"
        payload = payload.copy()
        # Inyectamos la sesión dentro del payload (Requisito Verial)
        payload["sesionwcf"] = self.online_session if use_online_session else self.session

        try:
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
        if response.status_code == 200:
            try:
                data = response.json()
                # Éxito si Codigo es 0
                if data.get("InfoError", {}).get("Codigo") != 0:
                    return False, data.get("InfoError", {}).get("Descripcion", "Error desconocido")
                return True, data
            except Exception:
                return False, f"Respuesta no JSON: {response.text}"
        return False, f"Error servidor Verial (HTTP {response.status_code})"

    # --- CLIENTES ---

    def find_customer_by_nif(self, nif: str):
        """Busca cliente por NIF usando GET."""
        url = f"{self.base_url}/GetClientesWS?x={self.session}&nif={nif}"
        try:
            response = requests.get(url, timeout=20)
            ok, data = self._handle_response(response)
            if ok:
                clientes = data.get("Clientes", [])
                return True, (clientes[0] if clientes else None)
            return False, data
        except Exception as e:
            return False, str(e)

    def create_customer(self, customer_data: dict):
        """Crea o actualiza un cliente (si incluye 'Id')."""
        # customer_data debe contener: Nombre, NIF, Tipo, etc.
        success, response = self._post("NuevoClienteWS", customer_data)
        if not success:
            return False, response
        return self._handle_response(response)

    # --- PEDIDOS / DOCUMENTOS ---

    def create_order(self, order_payload: dict):
        """
        Crea un pedido/presupuesto usando el Tipo 5 (No fiscal).
        Evita errores de VeriFactu y Object Reference.
        """
        # order_payload debe incluir: Tipo: 5, ID_Cliente, Contenido, etc.
        success, response = self._post("NuevoDocClienteWS", order_payload, use_online_session=True)
        if not success:
            return False, response
        return self._handle_response(response)

    # --- ARTÍCULOS Y STOCK ---

    def get_articles(self):
        """Obtiene catálogo completo."""
        url = f"{self.base_url}/GetArticulosWS?x={self.session}"
        try:
            response = requests.get(url, timeout=30)
            return self._handle_response(response)
        except Exception as e:
            return False, str(e)

    def get_stock(self, id_articulo: int = 0):
        """Obtiene stock filtrado o total."""
        url = f"{self.base_url}/GetStockArticulosWS?x={self.session}&id_articulo={id_articulo}"
        try:
            response = requests.get(url, timeout=30)
            return self._handle_response(response)
        except Exception as e:
            return False, str(e)