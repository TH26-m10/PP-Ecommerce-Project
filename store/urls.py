from django.urls import path

from store.views.user_view import *
from store.views.bank_view import *
from store.views.product_view import *
from store.views.cart_product_view import *
from store.views.cart_view import *
from store.views.order_view import *


urlpatterns = [

    # ================= USER =================

    path('user/create', user_create),

    # ================= PRODUCT =================

    path('product/create', product_create),
    path('product/update/<int:product_id>', product_update),
    path('product/delete/<int:product_id>', product_delete),
    path('product/all', product_show),
    path('product/<int:product_id>', product_show_one),
    path('product/add/<int:product_id>', product_add_quantity),

    # ================= CART PRODUCT =================

    path('cart-product/create', cart_product_create),
    path('cart-product/update/<int:cart_product_id>', cart_product_update),
    path('cart-product/delete/<int:cart_product_id>', cart_product_delete),

    # ================= CART =================

    path('cart/show/<int:user_id>', cart_show),
    path('cart/empty/<int:user_id>', cart_empty),
    path('cart/confirm/<int:user_id>', cart_confirm_payment),

    # ================= ORDER =================

    path('order/show/<int:user_id>', order_show),
    path('order/change-status/<int:order_id>', order_change_status),
    path('order/cancel/<int:order_id>', order_cancel),


]