# 🛒 Conector Shopify-Verial

![Tests](https://github.com/nut-tch/conector-shopify/workflows/Tests/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Django](https://img.shields.io/badge/django-5.1-green)
![PostgreSQL](https://img.shields.io/badge/postgresql-16-blue)
![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen)

> Middleware profesional de integración bidireccional entre Shopify y ERP Verial con sincronización automática en tiempo real.

---

## 📋 Descripción

Sistema de integración desarrollado en **Django** que conecta Shopify con el ERP Verial, permitiendo sincronización bidireccional completa de productos, clientes, pedidos y stock.

### ✨ Características Principales

- 🔄 **Sincronización Bidireccional Completa**
  - Shopify → Verial: Pedidos, clientes, productos
  - Verial → Shopify: Stock en tiempo real (optimizado con GraphQL)
  
- ⚡ **Optimización GraphQL**
  - Actualización de stock: 79 llamadas REST (60s) → 1 llamada GraphQL (1-2s)
  - Batch updates de hasta 250 productos simultáneos
  
- 🎯 **Mapeo Inteligente**
  - Mapeo automático por código de barras
  - Sincronización de clientes con búsqueda por NIF
  - Gestión de relaciones Shopify ↔ Verial
  
- 🔐 **Seguridad**
  - Validación HMAC en webhooks
  - Variables de entorno para secretos
  - Autenticación OAuth 2.0
  
- 🧪 **Testing Profesional**
  - 124 tests automatizados
  - ~80% de cobertura de código
  - CI/CD con GitHub Actions
  
- 📊 **Panel de Administración**
  - Dashboard con estadísticas en tiempo real
  - Botones de sincronización manual
  - Visualización de mappings

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│           SHOPIFY (Tienda)              │
│     - Productos (escaparate)            │
│     - Pedidos de clientes               │
│     - Stock actualizado desde Verial    │
└──────────────┬──────────────────────────┘
               │
               │ OAuth + REST API + GraphQL + Webhooks
               │
               ▼
┌─────────────────────────────────────────┐
│        DJANGO MIDDLEWARE                 │
├─────────────────────────────────────────┤
│  shopify_app/                           │
│  ├─ models.py (9 modelos)               │
│  ├─ views.py (14 endpoints)             │
│  ├─ order_to_verial.py                  │
│  ├─ product_mapping.py                  │
│  ├─ stock_sync.py (GraphQL)             │
│  └─ services/customer_sync.py           │
│                                         │
│  erp_connector/                         │
│  └─ verial_client.py                    │
│                                         │
│  Base de datos: PostgreSQL              │
└──────────────┬──────────────────────────┘
               │
               │ REST API (SOAP/JSON)
               │
               ▼
┌─────────────────────────────────────────┐
│         ERP VERIAL (Maestro)            │
│     - Catálogo de productos             │
│     - Gestión de stock                  │
│     - Procesamiento de pedidos          │
└─────────────────────────────────────────┘
```

**Flujo de datos:**
- **Verial = MAESTRO**: Gestión de productos, stock y pedidos
- **Shopify = ESCAPARATE**: Captura de pedidos de clientes
- **Middleware = SINCRONIZADOR**: Bidireccional en tiempo real

---

## 🚀 Instalación

### Requisitos previos

- Python 3.11 o 3.12
- PostgreSQL 14+
- pip
- Git

### Instalación Rápida

```bash
# 1. Clonar repositorio
git clone https://github.com/nut-tch/conector-shopify.git
cd conector-shopify

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar PostgreSQL
sudo -u postgres psql
```

```sql
CREATE USER conector_user WITH PASSWORD 'tu_password_segura';
CREATE DATABASE conector_shopify_db OWNER conector_user;
GRANT ALL PRIVILEGES ON DATABASE conector_shopify_db TO conector_user;
\c conector_shopify_db
GRANT ALL ON SCHEMA public TO conector_user;
\q
```

```bash
# 5. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus credenciales

# 6. Aplicar migraciones
python manage.py migrate

# 7. Crear superusuario
python manage.py createsuperuser

# 8. Ejecutar tests (opcional)
pytest

# 9. Iniciar servidor
python manage.py runserver
```

---

## ⚙️ Configuración

### Variables de entorno (`.env`)

```env
# Django
SECRET_KEY=tu-secret-key-super-segura
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,tu-dominio.com

# PostgreSQL
DATABASE_ENGINE=postgresql
DATABASE_NAME=conector_shopify_db
DATABASE_USER=conector_user
DATABASE_PASSWORD=tu_password_segura
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Shopify
SHOPIFY_API_KEY=tu_client_id
SHOPIFY_API_SECRET=shpss_tu_client_secret
SHOPIFY_SCOPES=read_products,write_products,read_orders,write_orders,read_customers,write_customers
SHOPIFY_REDIRECT_URI=http://127.0.0.1:8000/shopify/callback/

# Verial ERP
VERIAL_SERVER=ip:puerto
VERIAL_SESSION=tu_sesion
VERIAL_ONLINE_SESSION=tu_sesion_online
SEND_TO_VERIAL=true

# Webhook
WEBHOOK_URL=https://tu-dominio.com/shopify/webhook/orders/create/
```

---

## 📁 Estructura del Proyecto

```
conector-shopify/
├── .github/workflows/
│   └── tests.yml                   # CI/CD GitHub Actions
├── conector_shopify/               # Configuración Django
│   ├── settings.py                 # Config general
│   ├── settings_test.py            # Config testing
│   ├── urls.py
│   └── wsgi.py
├── shopify_app/                    # App principal
│   ├── models.py                   # 9 modelos de datos
│   ├── views.py                    # 14 endpoints
│   ├── admin.py                    # Panel administración
│   ├── urls.py
│   ├── order_to_verial.py          # Envío pedidos a Verial
│   ├── product_mapping.py          # Mapeo automático por barcode
│   ├── stock_sync.py               # Sync stock (GraphQL optimizado)
│   ├── services/
│   │   └── customer_sync.py        # Sincronización clientes
│   ├── templates/
│   │   └── shopify_app/
│   │       └── dashboard.html
│   └── tests/                      # 75 tests
│       ├── test_models.py          # 49 tests
│       ├── test_views.py           # 27 tests
│       ├── test_order_to_verial.py # 15 tests
│       └── test_customer_sync.py   # 14 tests
├── erp_connector/                  # Conector Verial
│   ├── verial_client.py            # Cliente API Verial
│   ├── views.py
│   ├── urls.py
│   └── tests/
│       └── test_verial_client.py   # 19 tests
├── conftest.py                     # Fixtures globales pytest
├── pytest.ini                      # Configuración pytest
├── requirements.txt                # Dependencias Python
├── .env.example                    # Template variables entorno
├── .gitignore
└── README.md
```

---

## 🔗 API Endpoints

### Shopify App

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/shopify/health/` | Health check del sistema |
| GET | `/shopify/install/?shop=X` | Iniciar OAuth con Shopify |
| GET | `/shopify/callback/` | Callback OAuth |
| GET | `/shopify/dashboard/` | Dashboard con estadísticas |
| GET | `/shopify/orders/` | Listar pedidos (JSON) |
| GET | `/shopify/sync-orders/` | Sincronizar pedidos desde Shopify |
| GET | `/shopify/sync-products/` | Sincronizar productos y variantes |
| GET | `/shopify/sync-customers/` | Sincronizar clientes |
| GET | `/shopify/map-products/` | Mapeo automático productos por barcode |
| GET | `/shopify/sync-stock/` | Sincronizar stock Verial → Shopify |
| POST | `/shopify/webhook/orders/create/` | Webhook nuevos pedidos |
| GET | `/shopify/register-webhook/` | Registrar webhook en Shopify |
| GET | `/shopify/test-locations/` | Test locations de Shopify |

### ERP Connector

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/erp/test-connection/` | Verificar conexión con Verial |
| GET | `/erp/products/` | Obtener productos de Verial |
| GET | `/erp/stock/` | Obtener stock de Verial |

---

## 📊 Modelos de Datos

### Core Models

**Shop**
```python
shop: CharField            # Dominio myshopify.com
access_token: CharField    # Token OAuth
```

**Product**
```python
shop: FK(Shop)
shopify_id: BigIntegerField (unique)
title, vendor, product_type, status
created_at: DateTimeField
```

**ProductVariant**
```python
product: FK(Product, related_name='variants')
shopify_id: BigIntegerField (unique)
sku, barcode: CharField          # ⭐ Clave para mapeo
price: DecimalField
inventory_quantity: IntegerField
```

**Customer**
```python
shop: FK(Shop)
shopify_id: BigIntegerField (unique)
email, first_name, last_name, phone
created_at: DateTimeField
```

**Order**
```python
shop: FK(Shop)
shopify_id: BigIntegerField (unique)
name: CharField              # #1001, #1002...
email, total_price
financial_status, fulfillment_status
status: CharField            # RECEIVED/READY/SENT/ERROR
sent_to_verial: BooleanField
sent_to_verial_at: DateTimeField
verial_status, verial_error
received_at, created_at
```

**OrderLine**
```python
order: FK(Order, related_name='lines')
shopify_id: BigIntegerField
product_title, variant_title, sku
quantity: IntegerField
price: DecimalField
@property total()            # quantity * price
```

### Mapping Models

**ProductMapping** (OneToOne)
```python
variant: OneToOne(ProductVariant, related_name='verial_mapping')
verial_id: BigIntegerField
verial_barcode: CharField
last_sync: DateTimeField (auto_now)
```

**CustomerMapping** (OneToOne)
```python
customer: OneToOne(Customer, related_name='verial_mapping')
verial_id: BigIntegerField
verial_nif: CharField
last_sync: DateTimeField (auto_now)
```

**OrderMapping** (OneToOne)
```python
order: OneToOne(Order, related_name='verial_mapping')
verial_id: BigIntegerField
verial_referencia: CharField
verial_numero: CharField
created_at, last_sync
```

---

## 🔄 Flujos de Sincronización

### 1. Sincronización de Productos

```
GET /shopify/sync-products/
→ Obtiene productos de Shopify (REST API)
→ Paginación automática (250 productos/página)
→ Guarda Product + ProductVariant (con barcode)
→ Respuesta: {"products": 73, "variants": 79}
```

### 2. Mapeo Automático de Productos

```
GET /shopify/map-products/
→ Obtiene catálogo de Verial (GetArticulosWS)
→ Busca coincidencias por código de barras
→ Crea/actualiza ProductMapping
→ Respuesta: {"nuevos": X, "actualizados": Y, "sin_match": [...]}
```

### 3. Sincronización de Stock (Verial → Shopify)

```
GET /shopify/sync-stock/
→ Obtiene stock desde Verial (GetStockArticulosWS)
→ Obtiene catálogo Verial por barcode
→ Obtiene inventory items de Shopify (GraphQL)
→ Actualiza stock en batch (mutation inventorySetQuantities)
→ Optimización: 250 productos por llamada
→ Respuesta: {"actualizados": 250, "total": 300}
```

**Optimización GraphQL:**
- **Antes**: 79 llamadas REST individuales (~60 segundos)
- **Ahora**: 1 llamada GraphQL batch (~1-2 segundos)

### 4. Sincronización de Clientes

```
GET /shopify/sync-customers/
→ Obtiene clientes de Shopify
→ Paginación automática
→ Guarda Customer en BD local
→ Respuesta: {"count": 150}
```

### 5. Envío de Pedido a Verial

```python
from shopify_app.order_to_verial import send_order_to_verial

success, message = send_order_to_verial(order)
```

**Flujo:**
1. Busca/crea cliente en Verial (por NIF si existe)
2. Verifica mapeo de productos
3. Construye payload con Tipo=5 (No fiscal)
4. Envía a `NuevoDocClienteWS`
5. Crea OrderMapping con ID de Verial
6. Actualiza estado del pedido

---

## 🔔 Webhooks

### Orders/Create

**Configuración en Shopify:**
- **Evento**: Order creation
- **URL**: `https://tu-dominio.com/shopify/webhook/orders/create/`
- **Formato**: JSON

**Proceso:**
1. Recibe POST de Shopify
2. Valida HMAC SHA256 (seguridad)
3. Parsea JSON del pedido
4. Guarda Order + OrderLine
5. Responde 200 OK

**Seguridad HMAC:**
```python
def validate_hmac(data, hmac_header):
    secret = settings.SHOPIFY_API_SECRET
    computed = base64.b64encode(
        hmac.new(secret.encode(), data, hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(computed, hmac_header)
```

---

## 🖥️ Panel de Administración

**Acceso**: `http://127.0.0.1:8000/admin/`

### Secciones Disponibles

- **📦 Pedidos**: Visualización completa con líneas inline, filtros por estado
- **🛍️ Productos**: Con variantes inline
- **📊 Variantes**: SKU, barcode, precio, stock
- **👥 Clientes**: Email, nombre, teléfono
- **🔗 Mapeo Productos**: Relación Shopify ↔ Verial
- **🔗 Mapeo Clientes**: Relación Shopify ↔ Verial
- **🔗 Mapeo Pedidos**: IDs y referencias Verial

### Funcionalidades

- ✅ Botones de sincronización en cada sección
- ✅ Filtros avanzados (estado pago, envío, fecha)
- ✅ Búsqueda full-text (nombre, email, SKU, barcode)
- ✅ Ordenación personalizada
- ✅ Exportación a CSV
- ✅ Dashboard con métricas en tiempo real

---

## 🛠️ Cliente API Verial

### Endpoints Implementados

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `GetArticulosWS` | Obtener catálogo completo |
| GET | `GetStockArticulosWS` | Obtener stock (filtrado o total) |
| GET | `GetClientesWS` | Buscar clientes (por NIF) |
| POST | `NuevoClienteWS` | Crear/actualizar cliente |
| POST | `NuevoDocClienteWS` | Crear pedido (Tipo 5) |

### Respuesta Estándar

```json
{
  "InfoError": {
    "Codigo": 0,
    "Descripcion": null
  },
  "Data": {...}
}
```

- `Codigo: 0` → Éxito
- `Codigo: X` → Error (se retorna descripción)

### Ejemplo de Uso

```python
from erp_connector.verial_client import VerialClient

client = VerialClient()

# Obtener artículos
success, result = client.get_articles()
if success:
    articulos = result.get('Articulos', [])

# Buscar cliente por NIF
success, cliente = client.find_customer_by_nif('12345678A')

# Crear pedido
payload = {
    'Tipo': 5,
    'ID_Cliente': 12345,
    'Contenido': [
        {'IdArticulo': 1001, 'Cantidad': 2, 'Precio': 29.99}
    ]
}
success, response = client.create_order(payload)
```

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Con cobertura
pytest --cov=shopify_app --cov=erp_connector --cov-report=html

# Ver cobertura en navegador
xdg-open htmlcov/index.html

# Tests específicos
pytest shopify_app/tests/test_models.py -v
pytest -m unit -v
pytest -m integration -v
pytest -m webhook -v
```

### Estadísticas de Testing

```
shopify_app/tests/test_models.py         49 tests ✅
shopify_app/tests/test_views.py          27 tests ✅
erp_connector/tests/test_verial_client.py 19 tests ✅
shopify_app/tests/test_order_to_verial.py 15 tests ✅
shopify_app/tests/test_customer_sync.py  14 tests ✅
──────────────────────────────────────────────────
TOTAL                                    124 tests ✅
Cobertura                                ~80%     ✅
```

### CI/CD

**GitHub Actions** ejecuta automáticamente:
- Tests en Python 3.11 y 3.12
- Verificación de cobertura (>70%)
- Linting con flake8
- Se ejecuta en cada push y pull request

---

## 🚀 Desarrollo Local con Webhooks

### Usando ngrok

```bash
# Terminal 1: Django
python manage.py runserver

# Terminal 2: ngrok
ngrok http 8000
# Copia la URL: https://abc123.ngrok.io

# Actualizar .env
WEBHOOK_URL=https://abc123.ngrok.io/shopify/webhook/orders/create/

# Registrar webhook en Shopify
curl http://127.0.0.1:8000/shopify/register-webhook/
```

---

## 📈 Roadmap

### ✅ Completado

- [x] Integración OAuth con Shopify
- [x] Sincronización productos y variantes
- [x] Sincronización clientes
- [x] Sincronización pedidos
- [x] Webhooks con validación HMAC
- [x] Mapeo automático por barcode
- [x] Envío pedidos a Verial
- [x] Sincronización stock Verial → Shopify (GraphQL)
- [x] Testing completo (124 tests)
- [x] CI/CD con GitHub Actions
- [x] Migración a PostgreSQL
- [x] Panel de administración completo

### 🔜 En Desarrollo

- [ ] Sincronización estado pedidos Verial → Shopify
- [ ] Dashboard con gráficas en tiempo real
- [ ] Automatización con APScheduler/Celery
- [ ] Notificaciones por email/Slack
- [ ] Logs centralizados (Sentry)
- [ ] Rate limiting en webhooks
- [ ] API REST para integraciones externas

### 💡 Futuro

- [ ] Multi-tenant (múltiples tiendas)
- [ ] Sincronización de imágenes
- [ ] Gestión de devoluciones
- [ ] Reportes avanzados
- [ ] Mobile app (React Native)

---

## 🛠️ Stack Tecnológico

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Python** | 3.11/3.12 | Backend |
| **Django** | 5.1.5 | Framework web |
| **PostgreSQL** | 14+ | Base de datos |
| **pytest** | 7.4.3 | Testing |
| **Shopify API** | 2024-01 | REST + GraphQL |
| **Verial API** | REST/SOAP | ERP integration |
| **GitHub Actions** | - | CI/CD |

---

## 📝 Contribución

Este es un proyecto privado de **NutricioneTech**. No se aceptan contribuciones externas.

---

## 👤 Autor

**NutricioneTech**
- GitHub: [@nut-tch](https://github.com/nut-tch)
- Repositorio: [conector-shopify](https://github.com/nut-tch/conector-shopify)

---

## 📄 Licencia

Proyecto privado de uso interno. Todos los derechos reservados.

---

## 🆘 Soporte

Para issues o preguntas sobre el proyecto, abrir un issue en GitHub o contactar directamente.

---

> 💡 **Nota Importante**: Verial es el sistema maestro para productos y stock. Los compañeros siguen trabajando normalmente en Verial. El middleware sincroniza automáticamente pedidos de Shopify hacia Verial y actualiza el stock de Shopify desde Verial.

---

**Última actualización**: Febrero 2026
