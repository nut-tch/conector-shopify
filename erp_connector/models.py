from django.db import models

class ERPSyncLog(models.Model):
    ACTION_CHOICES = [
        ('order_sent', 'Pedido enviado'),
        ('product_sent', 'Producto enviado'),
        ('customer_sent', 'Cliente enviado'),
        ('error', 'Error'),
    ]
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    shopify_id = models.BigIntegerField(null=True, blank=True)
    erp_response = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.shopify_id} - {'OK' if self.success else 'ERROR'}"