# 🛒 Conector Shopify - Django

> Sistema de integración entre Shopify y Django para sincronización de pedidos, productos y clientes.

---

## 📋 Descripción

Este proyecto es un conector backend desarrollado en **Django** que permite:

- ✅ Sincronización de **pedidos** desde Shopify
- ✅ Sincronización de **productos** desde Shopify
- ✅ Sincronización de **clientes** desde Shopify
- ✅ Recepción de **webhooks** en tiempo real
- ✅ Panel de administración con botones de sincronización
- ✅ Preparado para conexión con **ERP Verial**

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
│   (Conector)    │
├─────────────────┤
│ - shopify_app   │
│ - erp_connector │
└────────┬────────┘
         │ (Pendiente)
         ▼
┌─────────────────┐
│   ERP Verial    │
│  (Webservices)  │
└─────────────────┘
```

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
# Windows (Git Bash)
source venv/Scripts/activate
# Windows (CMD)
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 4. Instalar dependencias
pip install django requests python-dotenv

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

# ERP (pendiente)
ERP_URL=
ERP_USER=
ERP_PASSWORD=
```

### Configuración en Shopify

1. Crear **Custom App** en Shopify Admin → Settings → Apps → Develop apps
2. Configurar **scopes**:
   - `read_products`
   - `read_orders`
   - `write_orders`
   - `read_customers`
3. Configurar **Redirect URL**: `http://127.0.0.1:8000/shopify/callback/`
4. Instalar la app y guardar el **Access Token**

---

## 📁 Estructura del proyecto

```
conector_shopify/
├── conector_shopify/          # Configuración Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── shopify_app/               # App principal Shopify
│   ├── models.py              # Shop, Order, Product, Customer
│   ├── views.py               # Vistas y webhooks
│   ├── urls.py                # Rutas API
│   ├── admin.py               # Panel administración
│   └── templates/admin/       # Templates botones sync
├── erp_connector/             # Conector ERP (preparado)
│   ├── models.py              # ERPSyncLog
│   ├── views.py               # Funciones ERP
│   └── urls.py
├── .env                       # Variables de entorno
├── .gitignore
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
| GET | `/shopify/orders/` | Ver pedidos (JSON) |
| GET | `/shopify/sync-orders/` | Sincronizar pedidos |
| GET | `/shopify/sync-products/` | Sincronizar productos |
| GET | `/shopify/sync-customers/` | Sincronizar clientes |
| POST | `/shopify/webhook/orders/create/` | Webhook nuevos pedidos |

### ERP Connector

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/erp/test-connection/` | Test conexión ERP |

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
- financial_status: CharField (paid, pending, refunded)
- fulfillment_status: CharField (fulfilled, unfulfilled)
- created_at: DateTimeField
```

### Product
```python
- shop: ForeignKey(Shop)
- shopify_id: BigIntegerField
- title: CharField
- vendor: CharField
- product_type: CharField
- status: CharField (active, draft, archived)
- created_at: DateTimeField
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

### ERPSyncLog
```python
- action: CharField (order_sent, product_sent, customer_sent, error)
- shopify_id: BigIntegerField
- erp_response: TextField
- success: BooleanField
- created_at: DateTimeField
```

---

## 🔔 Webhooks

### Orders Create

Cuando se crea un pedido en Shopify, el webhook:

1. Recibe el POST de Shopify
2. Valida el HMAC (seguridad)
3. Guarda el pedido en la BD
4. Responde 200 OK

**Configuración en Shopify:**
- Evento: `Order creation`
- URL: `https://tu-dominio.com/shopify/webhook/orders/create/`
- Formato: JSON

---

## 🖥️ Panel de Administración

Accede a: `http://127.0.0.1:8000/admin/`

### Funcionalidades:
- ✅ Ver pedidos, productos y clientes
- ✅ Botón "Sincronizar" en cada sección
- ✅ Ordenación por fecha (más reciente primero)
- ✅ Logs de sincronización ERP

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

## 🔐 Seguridad

- ✅ Credenciales en `.env` (no en código)
- ✅ `.gitignore` protege archivos sensibles
- ✅ Validación HMAC en webhooks
- ✅ CSRF exempt solo en webhooks
- ✅ ALLOWED_HOSTS configurado

---

## 📝 Próximos pasos

- [ ] Implementar conexión ERP Verial (webservices)
- [ ] Webhook para productos nuevos
- [ ] Webhook para clientes nuevos
- [ ] Sincronización bidireccional con ERP
- [ ] Deploy en servidor de producción

---

## 🛠️ Tecnologías

| Tecnología | Versión |
|------------|---------|
| Python | 3.14.2 |
| Django | 6.0.1 |
| Shopify API | 2024-01 |
| Base de datos | SQLite (dev) |

---

## 👤 Autor

**NutricioneTech**

- GitHub: [@nut-tch](https://github.com/nut-tch)

---

## 📄 Licencia

Este proyecto es privado y de uso interno.

---

> 💡 **Nota:** Este conector está diseñado para funcionar en paralelo sin afectar la tienda de Shopify ni interrumpir ventas.
