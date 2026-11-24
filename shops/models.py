from django.conf import settings
from django.db import models


class Shop(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shop')
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    latitude = models.FloatField(default=9.8965)
    longitude = models.FloatField(default=8.8583)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Dish(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='dishes')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='dishes/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.shop.name})"
