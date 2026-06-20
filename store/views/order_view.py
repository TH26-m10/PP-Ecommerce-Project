from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import F

from store.auth_helpers import deny_if_not_owner, deny_if_not_order_owner
from store.models import Bank, Order, Product, ProductOrder
from store.views import bank_view
from store.celery_utils import safe_delay
from store.tasks import generate_invoice_task

from store.serializers import (
    ProductOrderSerializer,
)

STATUS_FLOW = [
    'pending',
    'preparing',
    'delivering',
    'success'
]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_show(request, user_id):

    denied = deny_if_not_owner(request, user_id)
    if denied:
        return denied

    orders = Order.objects.filter(user_id=user_id).order_by('created_at')
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
            'total_amount': order.total_amount,
            'created_at': order.created_at,
            'products': serializer.data
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_change_status(request, order_id):

    new_status = request.data.get('status')

    if not new_status:
        return Response({'message': 'status is required'}, status=400)

    if new_status not in STATUS_FLOW:
        return Response({'message': 'Invalid status'}, status=400)

    try:
        order = Order.objects.get(id=order_id)

        denied = deny_if_not_order_owner(request, order)
        if denied:
            return denied

        if order.status == 'cancelled':
            return Response(
                {'message': 'Cannot change cancelled order'},
                status=400
            )

        if order.status == 'success':
            return Response(
                {'message': 'Order already completed'},
                status=400
            )

        if order.status not in STATUS_FLOW:
            return Response(
                {'message': 'Invalid current status'},
                status=400
            )

        current_index = STATUS_FLOW.index(order.status)
        new_index = STATUS_FLOW.index(new_status)

        if new_index != current_index + 1:
            return Response(
                {'message': 'Must follow status sequence'},
                status=400
            )

        order.status = new_status
        order.save(update_fields=['status'])

        if new_status == 'success':
            safe_delay(generate_invoice_task, order.id)

        return Response({'message': 'Status updated'})

    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def order_cancel(request, order_id):

    try:
        order = Order.objects.select_for_update().get(id=order_id)
        # order = Order.objects.get(id=order_id)

        denied = deny_if_not_order_owner(request, order)
        if denied:
            return denied

        if order.user_id is None:
            return Response({'error': 'Order has no owner'}, status=400)

        bank = Bank.objects.select_for_update().get(user_id=order.user_id)
        # bank = Bank.objects.get(user_id=order.user_id)

        if order.status != 'pending':
            return Response({'message': 'Cannot cancel this order'}, status=400)

        items = ProductOrder.objects.select_related(
            'product').filter(order=order)

        total_price = sum(item.price * item.quantity for item in items)

        if not bank_view.bank_charge(bank.id, total_price):
            return Response({'message': 'Refund failed'}, status=400)

        product_ids = [
            item.product_id for item in items if item.product_id
        ]
        if product_ids:
            for item in items:
                if item.product_id:
                    Product.objects.select_for_update().filter(
                        id=item.product_id).update(quantity=F('quantity') + item.quantity)
                    # Product.objects.filter(id=item.product_id).update(
                    #     quantity=F('quantity') + item.quantity
                    # )

        order.status = 'cancelled'
        order.save(update_fields=['status'])

        return Response({'message': 'Order cancelled'})

    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)

    except Bank.DoesNotExist:
        return Response({'error': 'Bank account not found'}, status=404)
