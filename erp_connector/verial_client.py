import requests
import logging
from django.conf import settings

logger = logging.getLogger("verial")


class VerialClient:
    def __init__(self):
        self.base_url = settings.VERIAL_BASE_URL
        self.session = settings.VERIAL_SESSION
        self.headers = {
            "Content-Type": "application/json"
        }

    def is_configured(self):
        return bool(self.base_url and self.session)

    def _post(self, endpoint: str, payload: dict):
        if not self.is_configured():
            return False, "Verial no configurado"

        url = f"{self.base_url}/{endpoint}"

        payload = payload.copy()
        payload["sesionwcf"] = self.session

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            return True, response

        except requests.exceptions.RequestException as e:
            logger.error(f"Error conexión Verial [{endpoint}]: {e}")
            return False, f"Error conexión Verial: {e}"


    def create_customer(self, customer_data: dict):
        success, response = self._post("Clientes.svc/Alta", customer_data)
        if not success:
            return False, response

        return self._handle_response(response)

    def create_order(self, order_data: dict):
        success, response = self._post("Documentos.svc/Alta", order_data)
        if not success:
            return False, response

        return self._handle_response(response)

    def _handle_response(self, response):
        try:
            data = response.json()
        except Exception:
            return False, f"Respuesta no JSON ({response.status_code})"

        info = data.get("InfoError")
        if info and info.get("Codigo") not in (0, None):
            return False, info.get("Descripcion", "Error Verial")

        return True, data
