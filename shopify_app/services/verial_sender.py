from django.utils import timezone
from shopify_app.order_to_verial import send_order_to_verial

DUPLICATE_MESSAGES = [
    "ya existe un documento con la misma referencia"
]

def send_order(order):
    
    if order.sent_to_verial:
        return True

    success, message = send_order_to_verial(order)

    if success:
        order.status = "SENT"
        order.sent_to_verial = True
        order.sent_to_verial_at = timezone.now()
        order.verial_error = ""

    else:
        
        if message:
            lower_msg = message.lower()
            if any(txt in lower_msg for txt in DUPLICATE_MESSAGES):
                order.status = "SENT"
                order.sent_to_verial = True
                order.sent_to_verial_at = timezone.now()
                order.verial_error = "Duplicado en Verial (pedido ya existente)"
            else:
                order.status = "ERROR"
                order.verial_error = message
        else:
            order.status = "ERROR"
            order.verial_error = "Error desconocido"

    order.save()
    return order.sent_to_verial
