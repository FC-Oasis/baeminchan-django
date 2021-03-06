from django.urls import path, include

urlpatterns = [
    path('users/', include('members.urls.apis')),
    path('products/', include('product.urls.apis')),
    path('carts/', include('cart.urls.apis')),
    path('comments/', include('comment.urls.apis')),
]
