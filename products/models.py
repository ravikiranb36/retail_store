from django.db import models

# Create your models here.

class Store(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    sku = models.CharField(max_length=64)
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    class Meta:
        unique_together = ('store', 'sku')

    def __str__(self):
        return f"{self.product_name} ({self.sku}) - {self.store.name}"
