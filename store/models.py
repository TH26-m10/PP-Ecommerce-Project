from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.exceptions import ValidationError


class Bank(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(balance__gte=0),
                name='bank_balance_non_negative'
            )
        ]

    def __str__(self):
        return f"Bank Account {self.id} ({self.balance})"


class Product(models.Model):

    name = models.CharField(max_length=255)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    quantity = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name='product_quantity_non_negative'
            ),
            models.CheckConstraint(
                condition=Q(price__gt=0),
                name='product_price_positive'
            )
        ]


class DailySummary(models.Model):

    date = models.DateField()

    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    orders_processed = models.IntegerField(default=0)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(total_revenue__gte=0),
                name='dailysummary_revenue_non_negative'
            ),
            models.CheckConstraint(
                condition=Q(orders_processed__gte=0),
                name='dailysummary_orders_non_negative'
            )
        ]

    def __str__(self):
        return str(self.date)


class Order(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('delivering', 'Delivering'),
        ('success', 'Success'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name='order_total_amount_non_negative'
            )
        ]

    def __str__(self):
        return f"Order {self.id}"


class ProductOrder(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.product.name} - {self.order.id}"

    class Meta:
        unique_together = ['product', 'order']
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gt=0),
                name='productorder_price_positive'
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name='productorder_quantity_positive'
            )
        ]


class Cart(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.user.username} Cart"


class CartProduct(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    def clean(self):

        if self.quantity > self.product.quantity:
            raise ValidationError("Quantity exceeds stock")

    def save(self, *args, **kwargs):

        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ['cart', 'product']
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name='cartproduct_quantity_positive'
            )
        ]

    def __str__(self):
        return f"{self.product.name} in cart"
