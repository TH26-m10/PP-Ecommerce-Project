from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User

from store.auth_helpers import deny_if_not_owner
from store.models import Cart, CartProduct
from store.services.inventory import checkout_cart_safely


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_show(request, user_id):

    denied = deny_if_not_owner(request, user_id)
    if denied:
        return denied

    try:
        user = User.objects.get(id=user_id)
        cart = Cart.objects.get(user=user)

        cart_products = CartProduct.objects.select_related(
            'product').filter(cart=cart)

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

    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_empty(request, user_id):

    denied = deny_if_not_owner(request, user_id)
    if denied:
        return denied

    try:
        user = User.objects.get(id=user_id)
        cart = Cart.objects.get(user=user)

        CartProduct.objects.filter(cart=cart).delete()

        return Response({
            'message': 'Cart emptied'
        })

    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cart_confirm_payment(request, user_id):

    denied = deny_if_not_owner(request, user_id)
    if denied:
        return denied

    try:
        user = User.objects.get(id=user_id)

        order, error = checkout_cart_safely(user)

        if error:
            return Response({
                'message': error
            }, status=400)

        return Response({
            'message': 'Payment successful',
            'order_id': order.id,
            'total_amount': order.total_amount
        })

    except User.DoesNotExist:
        return Response({
            'message': 'User not found'
        }, status=404)
