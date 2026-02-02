from django.core.management.base import BaseCommand
from shopify_app.models import Order
from shopify_app.order_to_verial import send_order_to_verial

class Command(BaseCommand):
    help = "Envía pedidos pendientes de Shopify a Verial"

    def handle(self, *args, **options):
        orders = Order.objects.filter(
            status="RECEIVED",
            sent_to_verial=False
        )

        if not orders.exists():
            self.stdout.write(self.style.SUCCESS("✨ No hay pedidos pendientes de envío."))
            return

        self.stdout.write(f"📦 Se han encontrado {orders.count()} pedidos para procesar.")

        for order in orders:
            self.stdout.write(f"🚀 Procesando pedido {order.name}...")
            
            success, message = send_order_to_verial(order)

            if success:
                self.stdout.write(self.style.SUCCESS(
                    f"  ✔ Pedido {order.name} inyectado correctamente en Verial."
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"  ✖ Error en pedido {order.name}: {message}"
                ))