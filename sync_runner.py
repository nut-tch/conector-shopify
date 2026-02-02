#!/usr/bin/env python
"""
Script de sincronización automática profesional.
Ejecuta los procesos mediante los Management Commands oficiales de Django.
"""
import os
import sys
import django
import logging
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conector_shopify.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sync_runner')


def job_sync_stock():
    """Ejecuta: python manage.py sync_stock"""
    logger.info("⏳ [STOCK] Iniciando sincronización...")
    try:
        call_command('sync_stock')
    except Exception as e:
        logger.error(f"❌ [STOCK] Error crítico: {e}")

def job_sync_products():
    """Ejecuta la sincronización masiva de mapeos"""
    logger.info("⏳ [PRODUCTOS] Mapeando catálogo...")
    try:
        from shopify_app.product_mapping import auto_map_products_by_barcode
        success, result = auto_map_products_by_barcode()
        if success:
            logger.info(f"✅ [PRODUCTOS] Mapeo completado: {result.get('mapeados_nuevos', 0)} nuevos.")
        else:
            logger.error(f"❌ [PRODUCTOS] Error: {result}")
    except Exception as e:
        logger.error(f"❌ [PRODUCTOS] Error crítico: {e}")

def job_sync_order_status():
    """Sincroniza el estado de pedidos (Enviado, Preparado, etc)"""
    logger.info("⏳ [PEDIDOS] Consultando estados en Verial...")
    try:
        from shopify_app.order_status_sync import sync_order_status
        success, result = sync_order_status()
        if success:
            logger.info(f"✅ [PEDIDOS] Actualizados: {result.get('actualizados', 0)}")
        else:
            logger.error(f"❌ [PEDIDOS] Error: {result}")
    except Exception as e:
        logger.error(f"❌ [PEDIDOS] Error crítico: {e}")


def main():
    scheduler = BlockingScheduler()
    
    scheduler.add_job(
        job_sync_stock,
        IntervalTrigger(minutes=2),
        id='sync_stock',
        replace_existing=True
    )
    
    scheduler.add_job(
        job_sync_order_status,
        IntervalTrigger(minutes=5),
        id='sync_order_status',
        replace_existing=True
    )
    
    scheduler.add_job(
        job_sync_products,
        IntervalTrigger(minutes=30),
        id='sync_products',
        replace_existing=True
    )
    
    logger.info("🚀 Sync Runner activo y escuchando...")
    logger.info("   - Stock: 2m | Pedidos: 5m | Productos: 30m")
    
    logger.info("🔄 Ejecutando carga inicial de validación...")
    job_sync_stock()
    job_sync_order_status()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Sync Runner detenido manualmente.")

if __name__ == '__main__':
    main()