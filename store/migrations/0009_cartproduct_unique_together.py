from django.db import migrations
from django.db.models import Count, Sum


def merge_duplicate_cart_products(apps, schema_editor):
    CartProduct = apps.get_model('store', 'CartProduct')

    duplicates = (
        CartProduct.objects
        .values('cart_id', 'product_id')
        .annotate(count=Count('id'), total_qty=Sum('quantity'))
        .filter(count__gt=1)
    )

    for entry in duplicates:
        items = list(
            CartProduct.objects.filter(
                cart_id=entry['cart_id'],
                product_id=entry['product_id']
            ).order_by('id')
        )
        keeper = items[0]
        keeper.quantity = entry['total_qty']
        keeper.save(update_fields=['quantity'])
        CartProduct.objects.filter(
            id__in=[item.id for item in items[1:]]
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_merge_20260518_2311'),
    ]

    operations = [
        migrations.RunPython(
            merge_duplicate_cart_products,
            migrations.RunPython.noop
        ),
        migrations.AlterUniqueTogether(
            name='cartproduct',
            unique_together={('cart', 'product')},
        ),
    ]
