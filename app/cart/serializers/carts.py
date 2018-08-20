from django.contrib.auth import get_user_model
from rest_framework import serializers

from product.models import Product
from ..models import Cart, CartItem
from members.serializers import UserSerializer
User = get_user_model()


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = CartItem
        fields = (
            'pk',
            'product',
            'amount',
            'item_total_price',
        )

    def create(self, validated_data):
        product = validated_data['product']
        amount = validated_data['amount']
        cart = Cart.objects.get(user=self.context['request'].user)
        cart_item, __ = CartItem.objects.get_or_create(
            product=product,
            defaults={
                'cart': cart,
                'amount': amount,
            }
        )
        if __ is False:
            cart_item.amount += amount
            cart_item.save()
        return cart_item

    def update(self, instance, validated_data):
        instance.amount = validated_data.get('amount', instance.amount)
        instance.save()
        return instance


class CartSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)
    cart_items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = (
            'user',
            'cart_items',
            'total_price',
        )

