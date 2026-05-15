from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Bank)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(ProductOrder)
admin.site.register(Cart)
admin.site.register(CartProduct)