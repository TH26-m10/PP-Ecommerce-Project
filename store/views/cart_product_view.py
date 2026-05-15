from rest_framework.decorators import api_view
from rest_framework.response import Response
from store.models import *


@api_view(['POST'])
def cart_product_create(request):
    user_id = request.data.get('user_id')
    product_id = request.data.get('product_id')
    quantity = int(request.data.get('quantity'))

    try:
        user = User.objects.get(id=user_id)
        product = Product.objects.get(id=product_id)

        if quantity > product.quantity:
            return Response({'message': f'{product.name} out of stock'})

        cart = Cart.objects.get(user=user)

        # check if product already exists
        cart_product = CartProduct.objects.filter(
            cart=cart,
            product=product
        ).first()

        if cart_product:
            cart_product.quantity += quantity
            cart_product.save()

        else:
            cart_product = CartProduct.objects.create(
                cart=cart,
                product=product,
                quantity=quantity
            )

        return Response({'message': 'Product added to cart'})

    except Exception as e:
        return Response({'error': str(e)})
    

@api_view(['POST'])
def cart_product_update(request, cart_product_id):

    quantity = int(request.data.get('quantity'))

    try:
        cart_product = CartProduct.objects.get(id=cart_product_id)

        if quantity > cart_product.product.quantity:
            return Response({'message': f'{cart_product.product.name} out of stock'})

        cart_product.quantity = quantity
        cart_product.save()

        return Response({'message': 'Cart updated'})

    except CartProduct.DoesNotExist:
        return Response({'message': 'Cart product not found'})
    

@api_view(['POST'])
def cart_product_delete(request, cart_product_id):

    try:
        cart_product = CartProduct.objects.get(id=cart_product_id)
        cart_product.delete()
        return Response({'message': 'Deleted successfully'})

    except CartProduct.DoesNotExist:
        return Response({'message': 'Cart product not found'})