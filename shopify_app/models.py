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


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='lines')
    shopify_id = models.BigIntegerField()
    product_title = models.CharField(max_length=255, verbose_name="Producto")
    variant_title = models.CharField(max_length=255, blank=True, verbose_name="Variante")
    sku = models.CharField(max_length=100, blank=True, verbose_name="SKU")
    quantity = models.IntegerField(verbose_name="Cantidad")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")

    class Meta:
        verbose_name = "Línea de pedido"
        verbose_name_plural = "Líneas de pedido"

    def __str__(self):
        return f"{self.quantity}x {self.product_title}"

    @property
    def total(self):
        if self.quantity and self.price:
            return self.quantity * self.price
        return 0


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

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    shopify_id = models.BigIntegerField(unique=True)
    title = models.CharField(max_length=255, verbose_name="Título")
    sku = models.CharField(max_length=100, blank=True, verbose_name="SKU")
    barcode = models.CharField(max_length=100, blank=True, verbose_name="Código de barras")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")
    inventory_quantity = models.IntegerField(default=0, verbose_name="Stock")
    
    class Meta:
        verbose_name = "Variante"
        verbose_name_plural = "Variantes"
    
    def __str__(self):
        return f"{self.product.title} - {self.title}"
    
class ProductMapping(models.Model):
    variant = models.OneToOneField(ProductVariant, on_delete=models.CASCADE, related_name='verial_mapping')
    verial_id = models.BigIntegerField(verbose_name="ID Verial")
    verial_barcode = models.CharField(max_length=100, blank=True, verbose_name="Código barras Verial")
    last_sync = models.DateTimeField(auto_now=True, verbose_name="Última sincronización")
    
    class Meta:
        verbose_name = "Mapeo de producto"
        verbose_name_plural = "Mapeos de productos"
    
    def __str__(self):
        return f"{self.variant} → Verial ID: {self.verial_id}"

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

class CustomerMapping(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='verial_mapping')
    verial_id = models.BigIntegerField(verbose_name="ID Verial")
    verial_nif = models.CharField(max_length=20, blank=True, verbose_name="NIF Verial")
    last_sync = models.DateTimeField(auto_now=True, verbose_name="Última sincronización")
    
    class Meta:
        verbose_name = "Mapeo de cliente"
        verbose_name_plural = "Mapeos de clientes"
    
    def __str__(self):
        return f"{self.customer} → Verial ID: {self.verial_id}"