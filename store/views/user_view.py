from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.contrib.auth.models import User

from store.models import User, Cart, Bank
from store.serializers import (
    UserCreateSerializer,
)

@api_view(['POST'])
def user_create(request):

    serializer = UserCreateSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        Cart.objects.create(user=user)
        Bank.objects.create(
            user=user,
            balance=0
        )
        return Response({
            'message': 'User created successfully'
        })
    return Response(serializer.errors)




