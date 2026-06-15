from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth.models import User
from faker import Faker
from decimal import Decimal
import random

from store.models import (
    Bank,
    Product,
    Order,
    ProductOrder,
    Cart,
    CartProduct
)
from store.product_names import realistic_product_names

fake = Faker()


class Command(BaseCommand):
    help = "Reset and seed database"

    def truncate_tables(self):
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

            tables = [
                "store_productorder",
                "store_cartproduct",
                "store_order",
                "store_cart",
                "store_product",
                "store_bank",
                "auth_user",
            ]

            for table in tables:
                cursor.execute(f"TRUNCATE TABLE {table};")

            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    def handle(self, *args, **kwargs):

        self.stdout.write("Resetting database...")

        self.truncate_tables()

        self.stdout.write("Database reset complete")

        # =========================
        # USERS
        # =========================

        self.stdout.write("Creating users...")

        users = []

        for i in range(300):
            user = User.objects.create_user(
                username=f"user{i}",
                email=fake.email(),
                password="password123"
            )
            users.append(user)

            if (i + 1) % 50 == 0:
                self.stdout.write(f"  {i + 1} users created")

        # =========================
        # BANKS
        # =========================

        self.stdout.write("Creating banks...")

        Bank.objects.bulk_create([
            Bank(
                user=user,
                balance=Decimal(random.randint(10000, 100000))
            )
            for user in users
        ], batch_size=100)

        # =========================
        # PRODUCTS
        # =========================

        self.stdout.write("Creating products...")

        product_names = realistic_product_names(300)
        products = []

        for name in product_names:

            product = Product.objects.create(
                name=name,
                price=Decimal(str(round(random.uniform(9.99, 499.99), 2))),
                quantity=random.randint(100, 5000)
            )

            products.append(product)

        # =========================
        # CARTS
        # =========================

        self.stdout.write("Creating carts...")

        carts = []

        for user in users:

            cart = Cart(user=user)

            carts.append(cart)

        Cart.objects.bulk_create(carts, batch_size=100)

        all_carts = list(Cart.objects.select_related('user'))

        # =========================
        # CART PRODUCTS
        # =========================

        self.stdout.write("Creating cart products...")

        cart_products = []

        for cart in all_carts:

            selected_products = random.sample(
                products,
                random.randint(5, 15)
            )

            for product in selected_products:

                cart_products.append(
                    CartProduct(
                        cart=cart,
                        product=product,
                        quantity=random.randint(1, 5)
                    )
                )

        CartProduct.objects.bulk_create(
            cart_products,
            batch_size=500
        )

        # =========================
        # ORDERS
        # =========================

        self.stdout.write("Creating orders...")

        statuses = [
            'pending',
            'preparing',
            'delivering',
            'success',
            'cancelled'
        ]

        orders = []

        for user in users:

            orders.append(
                Order(
                    user=user,
                    status=random.choice(statuses)
                )
            )

        Order.objects.bulk_create(orders, batch_size=100)

        all_orders = list(Order.objects.select_related('user'))

        # =========================
        # PRODUCT ORDERS
        # =========================

        self.stdout.write("Creating product orders...")

        product_orders = []

        for order in all_orders:

            selected_products = random.sample(
                products,
                random.randint(3, 10)
            )

            for product in selected_products:

                product_orders.append(
                    ProductOrder(
                        order=order,
                        product=product,
                        quantity=random.randint(1, 5),
                        price=product.price
                    )
                )

        ProductOrder.objects.bulk_create(
            product_orders,
            batch_size=500
        )

        self.stdout.write("Updating order totals...")

        for order in all_orders:
            total_amount = sum(
                item.price * item.quantity
                for item in ProductOrder.objects.filter(order=order)
            )
            Order.objects.filter(id=order.id).update(total_amount=total_amount)

        self.stdout.write(
            self.style.SUCCESS(
                "Database seeded successfully!"
            )
        )
