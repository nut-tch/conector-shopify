"""
Configuración de Django para Testing

Este archivo hereda de settings.py pero sobrescribe configuraciones
para hacer los tests más rápidos y seguros.
"""
from .settings import *

# Usar base de datos en memoria para tests (más rápido)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Desactivar migraciones en tests (opcional, para mayor velocidad)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# 
# MIGRATION_MODULES = DisableMigrations()

# Configuración de password hashers más rápida para tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Desactivar logging en tests (opcional)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': False,
        },
        'shopify_app': {
            'handlers': ['null'],
            'propagate': False,
        },
        'erp_connector': {
            'handlers': ['null'],
            'propagate': False,
        },
    },
}

# Variables de entorno para testing (valores por defecto seguros)
SECRET_KEY = 'test-secret-key-not-for-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Shopify config para tests
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "test_shopify_secret")

# Verial config para tests
VERIAL_SERVER = os.getenv("VERIAL_SERVER", "192.168.1.100:8080")
VERIAL_SESSION = int(os.getenv("VERIAL_SESSION", "12345"))
VERIAL_ONLINE_SESSION = int(os.getenv("VERIAL_ONLINE_SESSION", "15"))
VERIAL_BASE_URL = f"http://{VERIAL_SERVER}/WcfServiceLibraryVerial"
VERIAL_HEADERS = {"Content-Type": "application/json"}

# URLs de Verial
VERIAL_SEARCH_CLIENT_URL = f"{VERIAL_BASE_URL}/BuscarClienteWS"
VERIAL_CREATE_CLIENT_URL = f"{VERIAL_BASE_URL}/NuevoClienteWS"
VERIAL_CREATE_ORDER_URL = f"{VERIAL_BASE_URL}/NuevoDocClienteWS"

# No enviar a Verial en tests (a menos que se especifique)
SEND_TO_VERIAL = os.getenv("TEST_SEND_TO_VERIAL", "false").lower() == "true"