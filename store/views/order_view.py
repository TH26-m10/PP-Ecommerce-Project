from rest_framework.decorators import api_view
from rest_framework.response import Response
from store.models import *
from store.views import bank_view
from django.db import transaction
from store.tasks import generate_invoice_task

from store.serializers import (
    ProductOrderSerializer,
)

@api_view(['GET'])
def order_show(request, user_id):

    orders = Order.objects.filter(user_id=user_id)
    data = []
    for order in orders:
        products = ProductOrder.objects.filter(order=order)
        serializer = ProductOrderSerializer(
            products,
            many=True
        )
        data.append({
            'order_id': order.id,
            'status': order.status,
            'products': serializer.data
        })
    return Response(data)


STATUS_FLOW = [
    'pending',
    'preparing',
    'delivering',
    'success'
]

@api_view(['POST'])
def order_change_status(request, order_id):

    new_status = request.data.get('status')

    try:
        order = Order.objects.get(id=order_id)
        current_index = STATUS_FLOW.index(order.status)
        new_index = STATUS_FLOW.index(new_status)

        if new_index <= current_index:
            return Response({'message': 'Cannot reverse status'})

        order.status = new_status
        order.save()
        if(new_status=='success'):
         generate_invoice_task.delay(order.id)

        return Response({'message': 'Status updated'})

    except Exception as e:
        return Response({'error': str(e)})
    

@api_view(['GET'])
@transaction.atomic
def order_cancel(request, order_id):

    try:
        order = Order.objects.get(id=order_id)
        bank = Bank.objects.get(user=order.user)

        if order.status != 'pending':
            return Response({'message': 'Cannot cancel this order'})

        items = ProductOrder.objects.filter(order=order)

        total_price = 0

        for item in items:
            total_price += item.price * item.quantity

        status = bank_view.bank_charge(bank.id,total_price)
        if not status:
            return Response({'message': 'Somthing went wrong'})

        # restore quantities
        for item in items:
            if item.product:
                item.product.quantity += item.quantity
                item.product.save()

        order.status = 'cancelled'
        order.save()

        return Response({'message': 'Order cancelled'})

    except Exception as e:
        return Response({'error': str(e)})