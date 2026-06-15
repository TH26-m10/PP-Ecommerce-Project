from rest_framework.response import Response
from rest_framework import status


def deny_if_not_owner(request, user_id):
    if request.user.id != int(user_id):
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    return None


def deny_if_not_order_owner(request, order):
    if order.user_id is None or order.user_id != request.user.id:
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    return None
