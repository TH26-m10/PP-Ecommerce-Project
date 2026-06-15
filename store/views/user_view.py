from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.contrib.auth.models import User

from store.auth_helpers import deny_if_not_owner
from store.models import Cart, Bank
from store.serializers import (
    UserCreateSerializer,
)


@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def user_create(request):

    serializer = UserCreateSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        Cart.objects.create(user=user)
        bank = Bank.objects.create(
            user=user,
            balance=1000000
        )
        return Response({
            'message': 'User created successfully',
            'user_id': user.id,
            'username': user.username,
            'bank_id': bank.id,
            'balance': bank.balance
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
