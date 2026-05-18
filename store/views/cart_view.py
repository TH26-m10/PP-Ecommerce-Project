from rest_framework.decorators import api_view
from rest_framework.response import Response
from store.models import *
from django.db import transaction

from store.views import bank_view
from store.serializers import (
    CartProductSerializer,
)


@api_view(['GET'])
def cart_show(request, user_id):

    try:
        user = User.objects.get(id=user_id)
        cart = Cart.objects.get(user=user)
        cart_products = CartProduct.objects.filter(cart=cart)

        total_price = 0
        data = []

        for item in cart_products:
            item_total = item.product.price * item.quantity
            total_price += item_total
            data.append({
                'cart_product_id': item.id,
                'product_id': item.product.id,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price': item.product.price,
                'total': item_total
            })

        return Response({
            'success': True,
            'products': data,
            'total_price': total_price
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        })


@api_view(['GET'])
def cart_show(request, user_id):

    user = User.objects.get(id=user_id)
    cart = Cart.objects.get(user=user)

    products = CartProduct.objects.filter(cart=cart)
    serializer = CartProductSerializer(
        products,
        many=True
    )
    return Response({
        'order_id': cart.id,
        'products': serializer.data
    })


@api_view(['GET'])
def cart_empty(request, user_id):
    user = User.objects.get(id=user_id)
    cart = Cart.objects.get(user=user)
    CartProduct.objects.filter(cart=cart).delete()

    return Response({
        'message': 'Cart emptied'
    })


@api_view(['POST'])
@transaction.atomic
def cart_confirm_payment(request, user_id):

    try:
        user = User.objects.get(id=user_id)
        cart = Cart.objects.get(user=user)
        cart_products = CartProduct.objects.filter(cart=cart)

        if not cart_products.exists():
            return Response({'message': 'Cart is empty'})

        total_price = 0

        # recheck quantities
        for item in cart_products:

            if item.quantity > item.product.quantity:
                return Response({'message': f'{item.product.name} out of stock'})

            total_price += item.product.price * item.quantity

        # create order
        order = Order.objects.create(
            user=user,
            status='pending'
        )

        # create product orders
        for item in cart_products:
            ProductOrder.objects.create(
                product=item.product,
                order=order,
                quantity=item.quantity,
                price=item.product.price
            )

        # reduce stock
        item.product.quantity -= item.quantity
        item.product.save()

        # empty cart
        cart_products.delete()

        return Response({
            'message': 'Payment successful',
            'order_id': order.id
        })

    except Exception as e:
        return Response({
            'error': str(e)
        })
