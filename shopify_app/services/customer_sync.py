import logging
from shopify_app.models import Customer, CustomerMapping, Order
from erp_connector.verial_client import VerialClient

logger = logging.getLogger('verial')

def build_customer_payload(customer: Customer, order: Order = None) -> dict:
    """
    Construye el payload para NuevoClienteWS imitando la estructura del conector viejo.
    """
    apellidos_raw = (customer.last_name or "").strip().split(" ", 1)
    apellido1 = apellidos_raw[0] if apellidos_raw else ""
    apellido2 = apellidos_raw[1] if len(apellidos_raw) > 1 else ""
    direccion = ""
    localidad = ""
    cp = ""
    provincia = ""

    es_empresa = bool(getattr(customer, 'company', ""))
    tipo_cliente = 2 if es_empresa else 1

    return {
        "Tipo": tipo_cliente,
        "NIF": getattr(customer, 'nif', "")[:20],
        "Nombre": (customer.first_name or "")[:50].strip(),
        "Apellido1": apellido1[:50].strip(),
        "Apellido2": apellido2[:50].strip(),
        "RazonSocial": (getattr(customer, 'company', "") or customer.first_name)[:100],
        "ID_Pais": 1,
        "Provincia": provincia[:50],
        "Localidad": localidad[:50],
        "LocalidadAux": "",
        "CPostal": cp[:10],
        "Direccion": direccion[:100],
        "Telefono": (customer.phone or "")[:50],
        "Email": (customer.email or "")[:100],
    }

def get_or_create_verial_customer(customer: Customer, order: Order = None) -> tuple[bool, int]:
    """
    Lógica de sincronización: Local -> NIF -> Creación.
    """
    mapping = CustomerMapping.objects.filter(customer=customer).first()
    if mapping:
        return True, mapping.verial_id
    
    client = VerialClient()
    nif = getattr(customer, 'nif', None)
    
    if nif:
        logger.info(f"Buscando cliente preventivamente por NIF: {nif}")
        success, v_customer = client.find_customer_by_nif(nif)
        
        if success and v_customer:
            verial_id = v_customer.get("Id")
            logger.info(f"Cliente localizado por NIF (ID: {verial_id}).")
            CustomerMapping.objects.get_or_create(customer=customer, defaults={'verial_id': verial_id})
            return True, verial_id

    logger.info(f"Creando nueva ficha de cliente para: {customer.email}")
    payload = build_customer_payload(customer, order)
    success, result = client.create_customer(payload)
    
    if success:
        clientes_list = result.get("Clientes", [])
        if clientes_list:
            verial_id = clientes_list[0].get("Id")
            CustomerMapping.objects.update_or_create(customer=customer, defaults={"verial_id": verial_id})
            return True, verial_id
    
    error_msg = result if not success else "Verial no devolvió ID"
    logger.error(f"Error creando cliente: {error_msg}")
    return False, 0

def ensure_customer_in_verial(order: Order) -> tuple[bool, int]:
    """Punto de entrada para el envío de pedidos."""
    customer = Customer.objects.filter(email=order.email, shop=order.shop).first()
    if not customer:
        return False, "Cliente no encontrado en base de datos local"
    
    return get_or_create_verial_customer(customer, order)