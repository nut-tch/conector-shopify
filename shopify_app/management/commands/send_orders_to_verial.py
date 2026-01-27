from django.core.management.base import BaseCommand
from shopify_app.models import Order
from shopify_app.services.verial_sender import send_order

class Command(BaseCommand):
    help = "Envía pedidos pendientes a Verial"

    def handle(self, *args, **options):
        orders = Order.objects.filter(
            status="RECEIVED",
            sent_to_verial=False
        )

        if not orders.exists():
            self.stdout.write("No hay pedidos pendientes.")
            return

        for order in orders:
            self.stdout.write(f"Enviando pedido {order.name}...")
            success = send_order(order)

            if success:
                self.stdout.write(self.style.SUCCESS(
                    f"✔ Pedido {order.name} enviado"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"✖ Error enviando pedido {order.name}"
                ))
