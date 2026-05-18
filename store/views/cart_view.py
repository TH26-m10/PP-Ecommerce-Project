from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User

from store.models import *
from store.serializers import CartProductSerializer
from store.services.inventory import checkout_cart_safely


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
def cart_empty(request, user_id):

    try:
        user = User.objects.get(id=user_id)
        cart = Cart.objects.get(user=user)

        CartProduct.objects.filter(cart=cart).delete()

        return Response({
            'message': 'Cart emptied'
        })

    except Exception as e:
        return Response({
            'error': str(e)
        }, status=500)


@api_view(['POST'])
def cart_confirm_payment(request, user_id):

    try:
        user = User.objects.get(id=user_id)

        order, error = checkout_cart_safely(user)

        if error:
            return Response({
                'message': error
            }, status=400)

        return Response({
            'message': 'Payment successful',
            'order_id': order.id
        })

    except User.DoesNotExist:
        return Response({
            'message': 'User not found'
        }, status=404)

    except Exception as e:
        return Response({
            'error': str(e)
        }, status=500)