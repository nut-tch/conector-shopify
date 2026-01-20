from django.db import models

class Shop(models.Model):
    shop = models.CharField(max_length=255, unique=True)
    access_token = models.CharField(max_length=255)

    def __str__(self):
        return self.shop
        
class Product(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    shopify_id = models.BigIntegerField(unique=True)
    title = models.CharField(max_length=255)
    vendor = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50)

class Order(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    shopify_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=50)
    email = models.CharField(max_length=255, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    financial_status = models.CharField(max_length=50)
    fulfillment_status = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField()

    def __str__(self):
        return self.name

class Product(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    shopify_id = models.BigIntegerField(unique=True)
    title = models.CharField(max_length=255)
    vendor = models.CharField(max_length=255, blank=True)
    product_type = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField()

    def __str__(self):
        return self.title





