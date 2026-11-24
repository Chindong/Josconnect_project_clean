from decimal import Decimal
from django.conf import settings
from django.db import models
from shops.models import Dish, Shop


class Order(models.Model):
    class FulfillmentType(models.TextChoices):
        DELIVERY = 'DELIVERY', 'Dispatch Delivery'
        PICKUP = 'PICKUP', 'Shop Pickup'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted by Shop'
        READY = 'READY', 'Ready for Pickup/Dispatch'
        DISPATCHED = 'DISPATCHED', 'Out for Delivery'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_orders')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders')
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rider_deliveries',
    )
    fulfillment_type = models.CharField(
        max_length=15,
        choices=FulfillmentType.choices,
        default=FulfillmentType.DELIVERY,
    )
    delivery_address = models.CharField(max_length=255, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    rider_earning = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.shop.name} ({self.get_fulfillment_type_display()})"

    dropoff_lat = models.FloatField(null=True, blank=True)
    dropoff_lng = models.FloatField(null=True, blank=True)

    rider_lat = models.FloatField(null=True, blank=True)
    rider_lng = models.FloatField(null=True, blank=True)
    rider_location_updated_at = models.DateTimeField(null=True, blank=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price