# 🛒 Conector Shopify - Verial - Django

> Middleware de integración entre Shopify y ERP Verial para sincronización de pedidos, productos y clientes.

---

## 📋 Descripción

Este proyecto es un middleware desarrollado en **Django** que conecta la tienda Shopify con el ERP Verial:

- ✅ Sincronización de **pedidos** desde Shopify
- ✅ Sincronización de **productos y variantes** desde Shopify
- ✅ Sincronización de **clientes** desde Shopify
- ✅ Recepción de **webhooks** en tiempo real
- ✅ **Mapeo automático** de productos por código de barras
- ✅ **Envío de pedidos** a Verial con cliente embebido
- ✅ **Mapeo de clientes** Shopify ↔ Verial
- ✅ Panel de administración con botones de sincronización
- ✅ Dashboard con estadísticas

# Conector Shopify-Verial

![Tests](https://github.com/nut-tch/conector-shopify/workflows/Tests/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Django](https://img.shields.io/badge/django-5.1-green)
![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen)

Sistema de integración entre Shopify y ERP Verial con sincronización automática de productos, clientes y pedidos.

## ✨ Features

- 🔄 Sincronización automática de stock (GraphQL optimizado)
- 📦 Mapeo automático de productos por barcode
- 👥 Gestión inteligente de clientes (búsqueda por NIF)
- 📝 Envío automático de pedidos a Verial
- 🔐 Webhooks seguros con validación HMAC
- 🧪 124 tests automatizados (~80% cobertura)
- 🚀 CI/CD con GitHub Actions

---

## 🏗️ Arquitectura

```
┌─────────────────┐
│    Shopify      │
│   (Tienda)      │
└────────┬────────┘
         │ OAuth + API + Webhooks
         ▼
┌─────────────────┐
│     Django      │
│  (Middleware)   │
├─────────────────┤
│ - shopify_app   │
│ - erp_connector │
└────────┬────────┘
         │ REST API
         ▼
┌─────────────────┐
│   ERP Verial    │
│  (Webservices)  │
└─────────────────┘
```

**Flujo de datos:**
- **Verial es el MAESTRO** → Los productos y stock se gestionan en Verial
- **Shopify es el escaparate** → Recibe pedidos de clientes
- **El middleware sincroniza** → Pedidos de Shopify → Verial

---

## 🚀 Instalación

### Requisitos previos

- Python 3.10+
- pip
- Git

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/nut-tch/conector-shopify.git
cd conector-shopify

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 6. Aplicar migraciones
python manage.py migrate

# 7. Crear superusuario
python manage.py createsuperuser

# 8. Arrancar servidor
python manage.py runserver
```

---

## ⚙️ Configuración

### Variables de entorno (`.env`)

```env
# Shopify
SHOPIFY_API_KEY=tu_client_id
SHOPIFY_API_SECRET=tu_client_secret
SHOPIFY_SCOPES=read_products,read_orders,read_customers
SHOPIFY_REDIRECT_URI=http://127.0.0.1:8000/shopify/callback/

# Verial ERP
VERIAL_SERVER=ip:puerto
VERIAL_SESSION=tu_sesion
VERIAL_ONLINE_SESSION=tu_sesion_online

# Webhook
WEBHOOK_URL=https://tu-dominio.com/shopify/webhook/orders/create/
```

---

## 📁 Estructura del proyecto

```
conector-shopify/
├── conector_shopify/          # Configuración Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── shopify_app/               # App principal
│   ├── models.py              # Shop, Order, OrderLine, Product, ProductVariant, Customer, ProductMapping, CustomerMapping
│   ├── views.py               # Sincronización y webhooks
│   ├── admin.py               # Panel administración
│   ├── urls.py
│   ├── order_to_verial.py     # Envío pedidos a Verial
│   ├── product_mapping.py     # Mapeo productos por código barras
│   ├── customer_mapping.py    # Mapeo clientes
│   └── templates/
├── erp_connector/             # Conector Verial
│   ├── verial_client.py       # Cliente API Verial
│   ├── views.py
│   └── urls.py
├── .env
├── manage.py
└── README.md
```

---

## 🔗 Endpoints disponibles

### Shopify App

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/shopify/health/` | Health check |
| GET | `/shopify/install/` | Iniciar OAuth |
| GET | `/shopify/callback/` | Callback OAuth |
| GET | `/shopify/dashboard/` | Dashboard estadísticas |
| GET | `/shopify/orders/` | Ver pedidos (JSON) |
| GET | `/shopify/sync-orders/` | Sincronizar pedidos |
| GET | `/shopify/sync-products/` | Sincronizar productos y variantes |
| GET | `/shopify/sync-customers/` | Sincronizar clientes |
| GET | `/shopify/map-products/` | Mapeo automático productos |
| POST | `/shopify/webhook/orders/create/` | Webhook nuevos pedidos |
| GET | `/shopify/register-webhook/` | Registrar webhook en Shopify |

### ERP Connector

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/erp/test-connection/` | Test conexión Verial |
| GET | `/erp/products/` | Obtener productos Verial |
| GET | `/erp/stock/` | Obtener stock Verial |

---

## 📊 Modelos de datos

### Shop
```python
- shop: CharField (dominio myshopify.com)
- access_token: CharField
```

### Order
```python
- shop: ForeignKey(Shop)
- shopify_id: BigIntegerField
- name: CharField (#1001, #1002...)
- email: CharField
- total_price: DecimalField
- financial_status: CharField
- fulfillment_status: CharField
- created_at: DateTimeField
```

### OrderLine
```python
- order: ForeignKey(Order, related_name='lines')
- shopify_id: BigIntegerField
- product_title: CharField
- variant_title: CharField
- sku: CharField (igual que barcode)
- quantity: IntegerField
- price: DecimalField
```

### Product
```python
- shop: ForeignKey(Shop)
- shopify_id: BigIntegerField
- title: CharField
- vendor: CharField
- product_type: CharField
- status: CharField
- created_at: DateTimeField
```

### ProductVariant
```python
- product: ForeignKey(Product, related_name='variants')
- shopify_id: BigIntegerField
- title: CharField
- sku: CharField
- barcode: CharField (CLAVE PARA MAPEO)
- price: DecimalField
- inventory_quantity: IntegerField
```

### ProductMapping
```python
- variant: OneToOneField(ProductVariant, related_name='verial_mapping')
- verial_id: BigIntegerField
- verial_barcode: CharField
- last_sync: DateTimeField
```

### Customer
```python
- shop: ForeignKey(Shop)
- shopify_id: BigIntegerField
- email: CharField
- first_name: CharField
- last_name: CharField
- phone: CharField
- created_at: DateTimeField
```

### CustomerMapping
```python
- customer: OneToOneField(Customer, related_name='verial_mapping')
- verial_id: BigIntegerField
- verial_nif: CharField
- last_sync: DateTimeField
```

---

## 🔄 Flujos de sincronización

### 1. Sincronizar productos
```
GET /shopify/sync-products/
→ Obtiene productos de Shopify
→ Guarda Product + ProductVariant (con barcode)
→ Respuesta: {"products": 73, "variants": 79}
```

### 2. Mapeo automático de productos
```
GET /shopify/map-products/
→ Obtiene artículos de Verial (GetArticulosWS)
→ Busca coincidencias por código de barras
→ Crea ProductMapping
→ Respuesta: {"mapeados_nuevos": X, "sin_match": [...]}
```

### 3. Envío de pedido a Verial
```python
from shopify_app.order_to_verial import send_order_by_id

success, message = send_order_by_id(order_id)
```
- Si el cliente ya tiene mapeo → usa `ID_Cliente`
- Si es cliente nuevo → envía datos embebidos en el pedido
- Verial crea el cliente automáticamente

---

## 🔔 Webhooks

### Orders Create

Cuando se crea un pedido en Shopify:
1. Recibe el POST de Shopify
2. Valida el HMAC (seguridad)
3. Guarda Order + OrderLine
4. Responde 200 OK

**Configuración en Shopify:**
- Evento: `Order creation`
- URL: `https://tu-dominio.com/shopify/webhook/orders/create/`
- Formato: JSON

---

## 🖥️ Panel de Administración

Accede a: `http://127.0.0.1:8000/admin/`

### Secciones:
- **Pedidos** - Con líneas de pedido inline
- **Productos** - Con variantes
- **Variantes** - SKU, barcode, precio, stock
- **Clientes**
- **Mapeo de productos** - Variant ↔ Verial
- **Mapeo de clientes** - Customer ↔ Verial

### Funcionalidades:
- ✅ Botón "Sincronizar" en cada sección
- ✅ Filtros por estado de pago/envío
- ✅ Búsqueda por nombre, email, SKU
- ✅ Ordenación por fecha

---

## 🛠️ API Verial

### Endpoints principales

| Endpoint | Descripción |
|----------|-------------|
| GetArticulosWS | Obtener productos |
| GetStockArticulosWS | Obtener stock |
| GetClientesWS | Obtener clientes |
| NuevoClienteWS | Crear/actualizar cliente |
| NuevoDocClienteWS | Crear pedido (Tipo=5) |
| EstadoPedidosWS | Consultar estado pedidos |

### Respuesta estándar
```json
{
  "InfoError": {
    "Codigo": 0,
    "Descripcion": null
  }
}
```
- `Codigo: 0` = OK
- `Codigo: X` = Error

---

## 🧪 Testing con ngrok

Para probar webhooks en local:

```bash
# Terminal 1: Django
python manage.py runserver

# Terminal 2: ngrok
ngrok http 8000
```

Usa la URL de ngrok para configurar webhooks en Shopify.

---

## 📝 Próximos pasos

- [ ] Botón en admin para enviar pedido a Verial
- [ ] Envío automático cuando llega webhook
- [ ] Incluir dirección de envío en pedidos
- [ ] Sincronización de stock Verial → Shopify
- [ ] Consultar estado de pedidos en Verial
- [ ] Deploy en producción

---

## 🛠️ Tecnologías

| Tecnología | Versión |
|------------|---------|
| Python | 3.12 |
| Django | 6.0.1 |
| Shopify API | 2024-01 |
| Verial | Web Service REST |
| Base de datos | SQLite (dev) |

---

## 👤 Autor

**NutricioneTech**

- GitHub: [@nut-tch](https://github.com/nut-tch)

---

## 📄 Licencia

Este proyecto es privado y de uso interno.

---

> 💡 **Nota:** Verial es el sistema maestro. Los compañeros siguen trabajando en Verial normalmente. El middleware solo sincroniza pedidos de Shopify hacia Verial.