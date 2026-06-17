from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
from store.serializers import (
    ProductSerializer,
)
from django.db.models import Sum
from store.models import Product
from django_redis import get_redis_connection
import time

PRODUCT_CACHE_PREFIX = "product"
CHCHE_TIMEOUT_TO_LIVE=30

BEST_SELLERS_CACHE_KEY = "best_sellers"
BEST_SELLERS_LOCK_KEY = "best_sellers_rebuild"

@api_view(['POST'])
@permission_classes([AllowAny])
def product_create(request):

    serializer = ProductSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    serializer.save()
    return Response(serializer.data, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def product_delete(request, product_id):

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)

    product.delete()
    cache.delete(f"product:{product_id}")
    return Response({'message': 'Product deleted'})


@api_view(['GET'])
@permission_classes([AllowAny])
def product_show(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_show_one(request, product_id):

    cache_key = f"{PRODUCT_CACHE_PREFIX}:{product_id}"

    cached_product = cache.get(cache_key)

    # ===== CACHE HIT =====
    if cached_product is not None:
        print(f"CACHE HIT -> {cache_key}")
        return Response(cached_product)

    # ===== CACHE MISS =====
    print(f"CACHE MISS -> {cache_key}")

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)

    serializer = ProductSerializer(product)

    cache.set(
        cache_key,
        serializer.data,
        timeout=None
    )

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def product_add_quantity(request, product_id):

    quantity = request.data.get('quantity')

    if quantity is None:
        return Response({'message': 'Quantity is required'}, status=400)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response({'message': 'Invalid quantity'}, status=400)

    if quantity <= 0:
        return Response(
            {'message': 'Quantity must be greater than zero'},
            status=400
        )

    try:
        product = Product.objects.select_for_update().get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)

    product.quantity = F('quantity') + quantity
    product.save(update_fields=['quantity'])
    cache.delete(f"product:{product_id}")
    product.refresh_from_db()

    serializer = ProductSerializer(product)

    return Response({
        'success': True,
        'data': serializer.data
    })


from django.core.cache import cache
from django.db.models import Sum
from django_redis import get_redis_connection

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from store.models import Product
from store.serializers import ProductSerializer


BEST_SELLERS_CACHE_KEY = "best_sellers"
BEST_SELLERS_STALE_KEY = "best_sellers:stale"
BEST_SELLERS_LOCK_KEY = "best_sellers_lock"

CACHE_TTL = 60        # fresh (1 minute)
STALE_TTL = 3600      # stale (1 hour)


@api_view(['GET'])
@permission_classes([AllowAny])
def best_sellers(request):

    # ================= 1. FRESH =================
    fresh = cache.get(BEST_SELLERS_CACHE_KEY)

    if fresh is not None:
        print("CACHE HIT → FRESH")
        return Response(fresh)

    print("CACHE MISS → FRESH")

    # ================= 2. LOCK =================
    redis_client = get_redis_connection("default")

    lock = redis_client.lock(
        BEST_SELLERS_LOCK_KEY,
        timeout=30
    )

    if lock.acquire(blocking=False):
        try:
            print("LOCK ACQUIRED → REBUILD START")

            # 🔥 REBUILD (هون صار بدل Celery)
            products = (
                Product.objects
                .annotate(total_sold=Sum('productorder__quantity'))
                .order_by('-total_sold')[:5]
            )

            serializer = ProductSerializer(products, many=True)
            data = serializer.data

            # ✅ تحديث fresh
            cache.set(
                BEST_SELLERS_CACHE_KEY,
                data,
                timeout=CACHE_TTL
            )

            # ✅ تحديث stale (مهم!)
            cache.set(
                BEST_SELLERS_STALE_KEY,
                data,
                timeout=STALE_TTL
            )

            print("REBUILD DONE")

            return Response(data)

        finally:
            lock.release()

    # ================= 3. STALE =================
    print("LOCK BUSY → RETURN STALE")

    stale = cache.get(BEST_SELLERS_STALE_KEY)

    if stale is not None:
        return Response(stale)

    # ================= 4. FALLBACK =================
    print("NO STALE → DB FALLBACK")

    products = (
        Product.objects
        .annotate(total_sold=Sum('productorder__quantity'))
        .order_by('-total_sold')[:5]
    )

    serializer = ProductSerializer(products, many=True)

    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def product_update(request, product_id):

    try:
        product = Product.objects.select_for_update().get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)

    serializer = ProductSerializer(product, data=request.data, partial=True)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    serializer.save()
    cache.delete(f"product:{product_id}")

    return Response(serializer.data)
