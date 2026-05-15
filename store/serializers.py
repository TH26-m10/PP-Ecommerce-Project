from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *


class UserCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    # hide password
    extra_kwargs = {
        'password': {'write_only': True}
    }

    # hash password
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
    

# Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class ProductOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOrder
        fields = '__all__'


class CartProductSerializer(serializers.ModelSerializer):
 
    product_name = serializers.CharField(
        source='product.name',
    )
    class Meta:
        model = CartProduct
        fields = '__all__'
