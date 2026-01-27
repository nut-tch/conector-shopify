from django.core.management.base import BaseCommand
from shopify_app.stock_sync import sync_stock_verial_to_shopify


class Command(BaseCommand):
    help = 'Sincroniza stock de Verial a Shopify'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando sincronización de stock...')
        
        success, result = sync_stock_verial_to_shopify()
        
        if success:
            self.stdout.write(self.style.SUCCESS(
                f"Stock sincronizado: {result['actualizados']} productos actualizados"
            ))
            if result['errores'] > 0:
                self.stdout.write(self.style.WARNING(
                    f"Errores: {result['errores']}"
                ))
        else:
            self.stdout.write(self.style.ERROR(
                f"Error: {result.get('error', 'Desconocido')}"
            ))