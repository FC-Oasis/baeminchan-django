from rest_framework import generics, permissions
from rest_framework.generics import get_object_or_404

from ..models import Cart, CartItem
from ..serializers.carts import CartSerializer, CartItemSerializer, CartItemAddSerializer


class CartList(generics.ListAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer


class UserCart(generics.RetrieveUpdateAPIView):
    """
    request.user의 cart정보를 보여줌
    """
    permission_classes = (
        permissions.IsAuthenticated,
    )
    serializer_class = CartSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        queryset = Cart.objects.all()
        cart, __ = Cart.objects.get_or_create(
            user=self.request.user
        )
        return queryset.filter(user=self.request.user)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        obj = queryset.get()
        return obj


class UserCartItemList(generics.ListCreateAPIView):
    """
    request.user의 cart에 담긴 아이템리스트를 보여줌
    """
    permission_classes = (
        permissions.IsAuthenticated,
    )
    #serializer_class = CartItemSerializer

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CartItemSerializer
        elif self.request.method == 'POST':
            return CartItemAddSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        queryset = CartItem.objects.all()
        cart = get_object_or_404(
            Cart,
            user=self.request.user,
        )
        return queryset.filter(cart=cart)


class UserCartItemDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    request.user의 cart에 담긴 아이템을 보여줌
    """
    permission_classes = (
        permissions.IsAuthenticated,
    )
    #serializer_class = CartItemSerializer

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CartItemSerializer
        else:
            return CartItemAddSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        queryset = CartItem.objects.all()
        cart = get_object_or_404(
            Cart,
            user=self.request.user,
        )
        return queryset.filter(cart=cart)
