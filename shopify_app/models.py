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






