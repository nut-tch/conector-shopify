from django.db import models


class Shop(models.Model):
    shop = models.CharField(max_length=255, unique=True)
    access_token = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Tienda"
        verbose_name_plural = "Tiendas"

    def __str__(self):
        return self.shop


class Order(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    shopify_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=50, verbose_name="Número")
    email = models.CharField(max_length=255, blank=True, verbose_name="Email")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total")
    financial_status = models.CharField(max_length=50, verbose_name="Estado pago")
    fulfillment_status = models.CharField(max_length=50, blank=True, verbose_name="Estado envío")
    created_at = models.DateTimeField(verbose_name="Fecha")

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return self.name


class Product(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    shopify_id = models.BigIntegerField(unique=True)
    title = models.CharField(max_length=255, verbose_name="Título")
    vendor = models.CharField(max_length=255, blank=True, verbose_name="Proveedor")
    product_type = models.CharField(max_length=255, blank=True, verbose_name="Tipo")
    status = models.CharField(max_length=50, verbose_name="Estado")
    created_at = models.DateTimeField(verbose_name="Fecha")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return self.title


class Customer(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    shopify_id = models.BigIntegerField(unique=True)
    email = models.CharField(max_length=255, blank=True, verbose_name="Email")
    first_name = models.CharField(max_length=255, blank=True, verbose_name="Nombre")
    last_name = models.CharField(max_length=255, blank=True, verbose_name="Apellidos")
    phone = models.CharField(max_length=50, blank=True, verbose_name="Teléfono")
    created_at = models.DateTimeField(verbose_name="Fecha")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"