from decimal import Decimal
import random

from django.core.management.base import BaseCommand

from store.models import Product
from store.product_names import realistic_product_names


class Command(BaseCommand):
    help = 'Update existing products with realistic names and USD-friendly prices'

    def handle(self, *args, **options):
        products = list(Product.objects.order_by('id'))
        if not products:
            self.stdout.write(self.style.WARNING('No products found. Run: python manage.py seed'))
            return

        names = realistic_product_names(len(products))

        for product, name in zip(products, names):
            product.name = name
            if product.price > 500:
                product.price = Decimal(str(round(random.uniform(9.99, 499.99), 2)))
            product.save(update_fields=['name', 'price'])

        self.stdout.write(self.style.SUCCESS(
            f'Updated {len(products)} products with realistic names.'
        ))
