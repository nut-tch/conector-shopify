import json
import requests

from django.conf import settings
from shopify_app.models import Order


def sync_orders_status():
    """
    Sincroniza el estado de los pedidos enviados a Verial
    consultando el endpoint EstadoPedidosWS.
    """

    try:
        orders_qs = Order.objects.filter(
            sent_to_verial=True
        ).exclude(
            status="COMPLETED"
        )

        if not orders_qs.exists():
            return True, "No hay pedidos para sincronizar"

        orders_by_id = {o.shopify_id: o for o in orders_qs}

        orders_payload = [{"Id": o.shopify_id} for o in orders_qs]

        url = f"http://{settings.VERIAL_SERVER}/WcfServiceLibraryVerial/EstadoPedidosWS"

        updated = 0
        completed = []

        i = 0
        while i < len(orders_payload):
            chunk = orders_payload[i:i + 25]

            payload = {
                "sesionwcf": int(settings.VERIAL_SESSION),
                "Pedidos": chunk
            }

            response = requests.post(
                url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if not response.ok:
                raise Exception(f"{response.status_code} {response.reason}")

            data = response.json()

            if data.get("InfoError", {}).get("Codigo") != 0:
                raise Exception(data["InfoError"].get("Descripcion"))

            for item in data.get("Pedidos", []):
                order = orders_by_id.get(item.get("Id"))
                if not order:
                    continue

                estado = item.get("Estado")

                if estado == 1:
                    order.status = "PENDING"
                elif estado in (2, 3):
                    order.status = "IN_PROGRESS"
                elif estado == 4:
                    order.status = "COMPLETED"
                    completed.append(order.shopify_id)

                order.verial_status = estado
                order.save(update_fields=["status", "verial_status"])
                updated += 1

            i += 25

        return True, (
            f"Pedidos: {orders_qs.count()} | "
            f"Actualizados: {updated} | "
            f"Completados: {completed}"
        )

    except Exception as e:
        return False, str(e)
