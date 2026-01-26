import logging
from .models import Customer, CustomerMapping
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')


def build_verial_customer_payload(customer: Customer, address: dict = None) -> dict:
    # Separar nombre y apellidos
    first_name = customer.first_name or ""
    last_name = customer.last_name or ""
    apellidos = last_name.split(" ", 1)
    apellido1 = apellidos[0] if apellidos else ""
    apellido2 = apellidos[1] if len(apellidos) > 1 else ""
    
    payload = {
        "Tipo": 1,  # 1=Persona
        "NIF": "",
        "Nombre": first_name,
        "Apellido1": apellido1,
        "Apellido2": apellido2,
        "RazonSocial": "",
        "ID_Pais": 1,  # España por defecto
        "Provincia": address.get("province", "") if address else "",
        "Localidad": address.get("city", "") if address else "",
        "CPostal": address.get("zip", "") if address else "",
        "Direccion": address.get("address1", "") if address else "",
        "Telefono": customer.phone or "",
        "Email": customer.email or "",
        "Id": None,
    }
    
    return payload


def create_customer_in_verial(customer: Customer, address: dict = None) -> tuple[bool, str]:
    # Si ya tiene mapeo, devolver el ID existente
    if hasattr(customer, 'verial_mapping'):
        return True, f"Cliente ya mapeado: {customer.verial_mapping.verial_id}"
    
    client = VerialClient()
    
    if not client.is_configured():
        return False, "Verial no configurado"
    
    payload = build_verial_customer_payload(customer, address)
    success, result = client.create_customer(payload)
    
    if success:
        verial_id = result.get("Id") or result.get("ID_Cliente")
        if verial_id:
            CustomerMapping.objects.create(
                customer=customer,
                verial_id=verial_id,
            )
            logger.info(f"Cliente {customer.email} creado en Verial: {verial_id}")
            return True, f"Cliente creado: {verial_id}"
        else:
            return False, "Verial no devolvió ID de cliente"
    else:
        logger.error(f"Error creando cliente {customer.email}: {result}")
        return False, result


def get_or_create_verial_customer(customer: Customer, address: dict = None) -> tuple[bool, int]:
    # Si ya existe mapeo, devolver ID
    if hasattr(customer, 'verial_mapping'):
        return True, customer.verial_mapping.verial_id
    
    # Crear en Verial
    success, result = create_customer_in_verial(customer, address)
    
    if success and hasattr(customer, 'verial_mapping'):
        return True, customer.verial_mapping.verial_id
    
    return False, None