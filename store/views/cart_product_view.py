from django.db import IntegrityError, transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth.models import User

from store.auth_helpers import deny_if_not_owner
from store.models import Cart, CartProduct, Product


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cart_product_create(request):
    user_id = request.data.get('user_id')
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity')

    if user_id is None or product_id is None:
        return Response({'message': 'user_id and product_id are required'}, status=400)

    denied = deny_if_not_owner(request, user_id)
    if denied:
        return denied

    if quantity is None:
        return Response({'message': 'Quantity is required'}, status=400)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response({'message': 'Invalid quantity'}, status=400)

    if quantity <= 0:
        return Response({'message': 'Quantity must be greater than zero'}, status=400)

    try:
        user = User.objects.get(id=user_id)
        product = Product.objects.select_for_update().get(id=product_id)
        # product = Product.objects.get(id=product_id)

        if quantity > product.quantity:
            return Response(
                {'message': f'{product.name} out of stock'},
                status=400
            )

        cart = Cart.objects.get(user=user)

        try:
            cart_product, created = CartProduct.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
        except IntegrityError:
            with transaction.atomic():
                # cart_product = CartProduct.objects.get(
                #     cart=cart,
                #     product=product
                # )
                cart_product = CartProduct.objects.select_for_update().get(
                    cart=cart,
                    product=product
                )
                created = False

        if not created:
            new_quantity = cart_product.quantity + quantity
            if new_quantity > product.quantity:
                return Response({
                    'message': f'{product.name} out of stock'
                }, status=400)

            cart_product.quantity = new_quantity
            cart_product.save()

        return Response({'message': 'Product added to cart'})

    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)

    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cart_product_update(request, cart_product_id):

    quantity = request.data.get('quantity')

    if quantity is None:
        return Response({'message': 'Quantity is required'}, status=400)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response({'message': 'Invalid quantity'}, status=400)

    if quantity <= 0:
        return Response({'message': 'Quantity must be greater than zero'}, status=400)

    try:
        # cart_product = CartProduct.objects.select_related(
        #     'cart', 'product'
        # ).get(id=cart_product_id)
        cart_product = CartProduct.objects.select_related(
            'cart', 'product'
        ).select_for_update().get(id=cart_product_id)

        denied = deny_if_not_owner(request, cart_product.cart.user_id)
        if denied:
            return denied

        # product = Product.objects.get(id=cart_product.product_id)
        product = Product.objects.select_for_update().get(id=cart_product.product_id)

        if quantity > product.quantity:
            return Response(
                {'message': f'{product.name} out of stock'},
                status=400
            )

        cart_product.quantity = quantity
        cart_product.save()

        return Response({'message': 'Cart updated'})

    except CartProduct.DoesNotExist:
        return Response({'message': 'Cart product not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cart_product_delete(request, cart_product_id):

    try:
        cart_product = CartProduct.objects.select_related('cart').get(
            id=cart_product_id
        )

        denied = deny_if_not_owner(request, cart_product.cart.user_id)
        if denied:
            return denied

        cart_product.delete()
        return Response({'message': 'Deleted successfully'})

    except CartProduct.DoesNotExist:
        return Response({'message': 'Cart product not found'}, status=404)
