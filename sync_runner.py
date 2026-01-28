#!/usr/bin/env python
"""
Script de sincronización automática.
Ejecuta: python sync_runner.py
"""
import os
import sys
import django
import logging
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conector_shopify.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sync_runner')


def job_sync_stock():
    """Sincronizar stock Verial → Shopify"""
    from shopify_app.stock_sync import sync_stock_verial_to_shopify
    
    logger.info("⏳ Iniciando sync stock...")
    success, result = sync_stock_verial_to_shopify()
    
    if success:
        logger.info(f"✅ Stock: {result.get('actualizados', 0)} productos actualizados")
    else:
        logger.error(f"❌ Stock: {result.get('error', 'Error desconocido')}")


def job_sync_products():
    """Sincronizar productos nuevos Verial → Shopify"""
    from shopify_app.product_mapping import auto_map_products_by_barcode
    
    logger.info("⏳ Iniciando sync productos...")
    success, result = auto_map_products_by_barcode()
    
    if success:
        logger.info(f"✅ Productos: {result.get('mapeados_nuevos', 0)} nuevos")
    else:
        logger.error(f"❌ Productos: {result.get('error', 'Error desconocido')}")


def job_sync_order_status():
    """Sincronizar estado pedidos Verial → Django"""
    from shopify_app.order_status_sync import sync_order_status
    
    logger.info("⏳ Iniciando sync estado pedidos...")
    success, result = sync_order_status()
    
    if success:
        logger.info(f"✅ Estados: {result.get('actualizados', 0)} actualizados")
    else:
        logger.error(f"❌ Estados: {result.get('error', 'Error desconocido')}")


def main():
    scheduler = BlockingScheduler()
    
    # Stock cada 2 minutos
    scheduler.add_job(
        job_sync_stock,
        IntervalTrigger(minutes=2),
        id='sync_stock',
        name='Sincronizar stock',
        replace_existing=True
    )
    
    # Productos cada 30 minutos
    scheduler.add_job(
        job_sync_products,
        IntervalTrigger(minutes=30),
        id='sync_products',
        name='Sincronizar productos',
        replace_existing=True
    )
    
    # Estado pedidos cada 5 minutos
    scheduler.add_job(
        job_sync_order_status,
        IntervalTrigger(minutes=5),
        id='sync_order_status',
        name='Sincronizar estado pedidos',
        replace_existing=True
    )
    
    logger.info("🚀 Sync Runner iniciado")
    logger.info("   - Stock: cada 2 minutos")
    logger.info("   - Productos: cada 30 minutos")
    logger.info("   - Estado pedidos: cada 5 minutos")
    logger.info("   Presiona Ctrl+C para detener")
    
    # Ejecutar una vez al inicio
    job_sync_stock()
    job_sync_products()
    job_sync_order_status()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Sync Runner detenido")


if __name__ == '__main__':
    main()