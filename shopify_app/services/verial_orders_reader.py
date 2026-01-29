import json
import requests
from datetime import date, timedelta
from django.conf import settings


def get_verial_orders_last_days(days=7):
    """
    Lee pedidos (documentos tipo 5) desde Verial
    NO toca base de datos
    NO toca Shopify
    """

    today = date.today()
    from_date = today - timedelta(days=days)

    payload = {
        "FechaDesde": from_date.strftime("%Y-%m-%d"),
        "FechaHasta": today.strftime("%Y-%m-%d"),
        "Tipo": 5,
        "sesionwcf": int(settings.VERIAL_SESSION),
    }

    url = f"http://{settings.VERIAL_SERVER}/WcfServiceLibraryVerial/BuscarDocClienteWS"

    try:
        r = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=30
        )
    except Exception as e:
        return False, f"Error conexión Verial: {e}"

    if not r.ok:
        return False, f"HTTP {r.status_code} leyendo documentos"

    try:
        data = r.json()
    except ValueError:
        return False, "Respuesta no JSON desde Verial"

    documentos = data.get("Documentos")
    if documentos is None:
        return False, "Respuesta Verial sin 'Documentos'"

    return True, documentos
