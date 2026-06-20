from decimal import Decimal
import random
import time

from django.db import transaction
from django.db.models import F

from store.models import Bank, Cart, CartProduct, Order, Product, ProductOrder
from store.views.bank_view import bank_pay


def checkout_cart_safely(user):

    time.sleep(2)
    payment_success = random.randint(1, 10) <= 9
    if not payment_success:
        return None, 'Payment failed'

    with transaction.atomic():
        # cart = Cart.objects.get(user=user)
        # bank = Bank.objects.filter(user=user).first()
        cart = Cart.objects.select_for_update().get(user=user)
        bank = Bank.objects.select_for_update().filter(user=user).first()

        if not bank:
            return None, 'Bank account not found'

        # items = list(
        #     CartProduct.objects
        #     .select_related('product')
        #     .filter(cart=cart)
        #     .order_by('product_id')
        # )
        items = list(
            CartProduct.objects
            .select_related('product')
            .select_for_update()
            .filter(cart=cart)
            .order_by('product_id')
        )

        if not items:
            return None, 'Cart is empty'

        required = {}
        for item in items:
            required[item.product_id] = required.get(
                item.product_id, 0) + item.quantity

        # products = Product.objects.filter(
        #     id__in=required.keys()
        # ).order_by('id')
        products = Product.objects.select_for_update().filter(
            id__in=required.keys()
        ).order_by('id')

        product_map = {p.id: p for p in products}

        for product_id, qty in required.items():
            product = product_map.get(product_id)
            if not product:
                return None, 'Product not found'
            if product.quantity < qty:
                return None, f'{product.name} out of stock'

        total_amount = sum(
            item.product.price * item.quantity for item in items
        )

        if bank.balance < Decimal(str(total_amount)):
            return None, 'Insufficient balance'

        if not bank_pay(bank.id, total_amount):
            return None, 'Payment failed'

        order = Order.objects.create(
            user=user,
            status='pending',
            total_amount=total_amount
        )

        for item in items:
            ProductOrder.objects.create(
                product=item.product,
                order=order,
                quantity=item.quantity,
                price=item.product.price
            )
            Product.objects.filter(id=item.product_id).update(
                quantity=F('quantity') - item.quantity
            )

        CartProduct.objects.filter(cart=cart).delete()

        return order, None
