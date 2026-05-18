from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F

from store.serializers import (
    ProductSerializer,
)

from store.models import *

@api_view(['POST'])
def product_create(request):

    product = Product.objects.create(
        name = request.data.get('name'),
        quantity = request.data.get('quantity'),
        price = request.data.get('price')
    )

    serializer = ProductSerializer(product)
    return Response(serializer.data)


@api_view(['POST'])
@transaction.atomic
def product_update(request, product_id):

    product = Product.objects.select_for_update().get(id=product_id)

    product.name = request.data.get('name')
    product.quantity = request.data.get('quantity')
    product.price = request.data.get('price')

    product.save()

    serializer = ProductSerializer(product)

    return Response(serializer.data)

@api_view(['POST'])
def product_delete(request,product_id):
    product = Product.objects.get(id=product_id)
    product.delete()
    
    return Response({'message': 'Product deleted'})


@api_view(['GET'])
def product_show(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def product_show_one(request, product_id):
    try:
        product = Product.objects.get(id=product_id)

    except Product.DoesNotExist:
        return Response({'error': 'Product not found'})

    serializer = ProductSerializer(product)
    return Response(serializer.data)



@api_view(['POST'])
@transaction.atomic
def product_add_quantity(request, product_id):

    quantity = int(request.data.get('quantity'))

    product = Product.objects.select_for_update().get(id=product_id)

    product.quantity = F('quantity') + quantity
    product.save(update_fields=['quantity'])

    product.refresh_from_db()

    serializer = ProductSerializer(product)

    return Response({
        'success': True,
        'data': serializer.data
    })