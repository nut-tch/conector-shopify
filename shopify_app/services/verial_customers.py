import json
import requests
from django.conf import settings
from shopify_app.models import Customer, CustomerMapping


def _s(value):
    """Nunca mandar None a Verial"""
    return value if value is not None else ""


def get_or_create_verial_customer(customer: Customer):
    """
    Devuelve (success, verial_customer_id | error_msg)
    """

    # 1️⃣ Reutilizar mapping si existe
    try:
        mapping = customer.verial_mapping
        return True, mapping.verial_id
    except CustomerMapping.DoesNotExist:
        pass

    # 2️⃣ Crear cliente directamente (como el middleware viejo)
    payload = {
        "sesionwcf": int(settings.VERIAL_SESSION),
        "Tipo": 1,

        "Nombre": _s(customer.first_name),
        "Apellido1": _s(customer.last_name),
        "Apellido2": "",
        "RazonSocial": "",
        "NIF": "",
        "Email": _s(customer.email),
        "Telefono": _s(customer.phone),
        "ID_Pais": 1,
        "Provincia": 0,
        "Localidad": _s(customer.city if hasattr(customer, "city") else "Madrid"),
        "CPostal": _s(customer.zipcode if hasattr(customer, "zipcode") else ""),
        "Direccion": _s(customer.address if hasattr(customer, "address") else ""),
        "TipoVia": 0,
        "Numero": "",
    }

    try:
        r = requests.post(
            settings.VERIAL_CREATE_CLIENT_URL,
            headers=settings.VERIAL_HEADERS,
            json=payload,
            timeout=20
        )
    except Exception as e:
        return False, f"Error conexión Verial (crear cliente): {e}"

    if not r.ok:
        return False, f"HTTP {r.status_code} creando cliente"

    try:
        data = r.json()
    except ValueError:
        return False, "Respuesta no JSON creando cliente"

    info = data.get("InfoError")
    if info and info.get("Codigo") not in (0, None):
        return False, info.get("Descripcion", "Error Verial creando cliente")

    clientes = data.get("Clientes") or []
    if not clientes:
        return False, "Verial no devolvió cliente creado"

    verial_id = clientes[0].get("Id")
    if not verial_id:
        return False, "Verial no devolvió ID de cliente"

    CustomerMapping.objects.create(
        customer=customer,
        verial_id=verial_id
    )

    return True, verial_id
