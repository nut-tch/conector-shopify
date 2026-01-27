import logging
from shopify_app.models import Customer, CustomerMapping, Order
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')


def build_customer_payload(customer: Customer) -> dict:
    apellidos = (customer.last_name or "").split(" ", 1)
    apellido1 = apellidos[0] if apellidos else ""
    apellido2 = apellidos[1] if len(apellidos) > 1 else ""
    
    return {
        "Tipo": 1,  # Particular
        "NIF": "",
        "Nombre": (customer.first_name or "")[:50],
        "Apellido1": apellido1[:50],
        "Apellido2": apellido2[:50],
        "RazonSocial": "",
        "ID_Pais": 1,  # España
        "Provincia": "",
        "Localidad": "",
        "CPostal": "",
        "Direccion": "",
        "Telefono": (customer.phone or "")[:20],
        "Email": (customer.email or "")[:100],
        "WebUser": (customer.email or "")[:100],
    }

def create_customer_in_verial(customer: Customer) -> tuple[bool, dict]:
    client = VerialClient()
    
    if not client.is_configured():
        return False, {"error": "Verial no configurado"}
    
    payload = build_customer_payload(customer)
    success, result = client.create_customer(payload)
    
    if not success:
        logger.error(f"Error creando cliente {customer.email}: {result}")
        return False, {"error": result}

    clientes = result.get("Clientes", [])
    if not clientes:
        return False, {"error": "Verial no devolvió ID de cliente"}
    
    verial_id = clientes[0].get("Id")
    if not verial_id:
        return False, {"error": "Verial no devolvió ID de cliente"}

    mapping = CustomerMapping.objects.create(
        customer=customer,
        verial_id=verial_id,
    )
    
    logger.info(f"Cliente {customer.email} creado en Verial: {verial_id}")
    
    return True, {"verial_id": verial_id, "mapping": mapping}

def get_or_create_verial_customer(customer: Customer) -> tuple[bool, int]:
    # Si ya tiene mapeo, devolver ID
    if hasattr(customer, 'verial_mapping'):
        return True, customer.verial_mapping.verial_id
    
    # Crear en Verial
    success, result = create_customer_in_verial(customer)
    
    if success:
        return True, result["verial_id"]
    
    return False, None

def get_customer_for_order(order: Order) -> Customer:
    if order.email:
        return Customer.objects.filter(email=order.email).first()
    return None


def ensure_customer_in_verial(order: Order) -> tuple[bool, int]:
    customer = get_customer_for_order(order)
    
    if not customer:
        logger.warning(f"Pedido {order.name}: no hay cliente con email {order.email}")
        return False, None
    
    return get_or_create_verial_customer(customer)