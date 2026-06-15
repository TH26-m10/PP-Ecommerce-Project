from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from django.db.models import F

from store.serializers import (
    ProductSerializer,
)

from store.models import Product


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
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def product_delete(request, product_id):

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)

    product.delete()

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
    try:
        product = Product.objects.get(id=product_id)

    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)

    serializer = ProductSerializer(product)
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

    product.refresh_from_db()

    serializer = ProductSerializer(product)

    return Response({
        'success': True,
        'data': serializer.data
    })
