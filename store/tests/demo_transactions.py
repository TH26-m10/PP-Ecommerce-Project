import os  
import sys 
import django 
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) 
django.setup() 


class Tee:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.file = open(filename, 'w', encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.file.write(message)

    def flush(self):
        self.terminal.flush()
        self.file.flush()

    def close(self):
        self.file.close()


sys.stdout = Tee('store\\tests\\demo_results.txt')

from store.views.order_view import order_cancel 
from store.views.user_view import user_create 
from store.services.inventory import checkout_cart_safely 
from store.models import Bank, Cart, CartProduct, Order, Product, ProductOrder  
from rest_framework.test import APIRequestFactory, force_authenticate  
from django.contrib.auth.models import User  
from decimal import Decimal 
import store.models


def banner(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def show_db(label):
    print(f"\n--- {label} ---")
    print(f"  Users:         {User.objects.count()}")
    print(f"  Carts:         {Cart.objects.count()}")
    print(f"  Banks:         {Bank.objects.count()}")
    print(f"  Orders:        {Order.objects.count()}")
    print(f"  ProductOrders: {ProductOrder.objects.count()}")
    print(f"  Products:      {Product.objects.count()}")
    # for p in Product.objects.all():
    #     print(f"    - {p.name}: qty={p.quantity}")
    # for b in Bank.objects.all():
    #     print(f"    - Bank #{b.id}: balance={b.balance}")
    # for o in Order.objects.all():
    #     print(
    #         f"    - Order #{o.id}: status={o.status}, amount={o.total_amount}")


def cleanup():
    ProductOrder.objects.all().delete()
    Order.objects.all().delete()
    CartProduct.objects.all().delete()
    Cart.objects.all().delete()
    Bank.objects.all().delete()
    User.objects.filter(username__startswith='demo').delete()
    Product.objects.filter(name__startswith='Demo').delete()


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 1: USER CREATE FAILURE
# ═══════════════════════════════════════════════════════════════════════════════

def demo_user_create_failure():
    banner("DEMO 1: User Create Failure")
    print("Simulating: Bank creation fails during user registration.\n")
    print("WITH transaction.atomic: User + Cart + Bank should ALL be rolled back.")
    print("WITHOUT transaction.atomic: User + Cart exist, but NO Bank (orphaned data!).\n")

    # cleanup()
    show_db("BEFORE")

    factory = APIRequestFactory()
    request = factory.post('/user/create/', {
        'username': 'demo_user',
        'password': 'pass123',
        'email': 'demo@test.com'
    }, format='json')

    original_bank_create = store.models.Bank.objects.create

    def fake_bank_create(*args, **kwargs):
        raise Exception("Bank creation failed!")

    store.models.Bank.objects.create = fake_bank_create

    try:
        user_create(request)
    except Exception as e:
        print(f"\n>>> Exception raised: {e}")
    finally:
        store.models.Bank.objects.create = original_bank_create

    show_db("AFTER")

    user_exists = User.objects.filter(username='demo_user').exists()
    cart_exists = Cart.objects.filter(user__username='demo_user').exists()
    bank_exists = Bank.objects.filter(user__username='demo_user').exists()

    print(f"\n>>> RESULTS:")
    print(f"    User exists:  {user_exists}")
    print(f"    Cart exists:  {cart_exists}")
    print(f"    Bank exists:  {bank_exists}")

    if user_exists and cart_exists and not bank_exists:
        print(f"\n    [BUG] Orphaned data! User+Cart exist without Bank.")
    elif not user_exists and not cart_exists and not bank_exists:
        print(f"\n    [OK]  All rolled back cleanly.")
    else:
        print(f"\n    [?]   Unexpected state.")


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 2: CHECKOUT FAILURE — Payment Gateway Crashes After Order Created
# ═══════════════════════════════════════════════════════════════════════════════

def demo_checkout_payment_failure():
    banner("DEMO 2: Checkout Payment Failure")
    print("Simulating: Payment succeeds, order created, stock deducted,")
    print("            THEN payment gateway crashes.\n")
    print("WITH transaction.atomic: Order + stock deduction + bank charge all rolled back.")
    print("WITHOUT transaction.atomic: Order exists, stock deducted, bank charged — CORRUPTED!\n")

    # cleanup()

    user = User.objects.create_user(
        username='demo_buyer', password='pass', email='demo_buyer@gmail.com')
    bank = Bank.objects.create(user=user, balance=Decimal('1000.00'))
    cart = Cart.objects.create(user=user)
    product = Product.objects.create(
        name='Demo Product', price=Decimal('100.00'), quantity=10)
    CartProduct.objects.create(cart=cart, product=product, quantity=2)

    show_db("BEFORE")

    import store.services.inventory as inv
    original_bank_pay = inv.bank_pay

    def fake_bank_pay(bank_id, amount):
        # call_count[0] += 1
        # if call_count[0] == 1:
        #     print(
        #         f"\n    [FAKE] bank_pay call #{call_count[0]}: succeeded (balance check)")
        #     return True
        # print(f"\n    [FAKE] bank_pay call #{call_count[0]}: CRASHING!")
        # raise Exception("Payment gateway crashed after order created!")
        print(f"\n    [FAKE] bank_pay: CRASHING!")
        raise Exception("Payment gateway crashed!")

    inv.bank_pay = fake_bank_pay

    try:
        order, error, items = checkout_cart_safely(user)
    except Exception as e:
        print(f"\n>>> Exception raised: {e}")
        order = None

    inv.bank_pay = original_bank_pay

    show_db("AFTER")

    order_count = Order.objects.count()
    product.refresh_from_db()
    bank.refresh_from_db()
    cart_items = CartProduct.objects.filter(cart=cart).count()

    print(f"\n>>> RESULTS:")
    print(f"    Orders:       {order_count}")
    print(f"    Stock:        {product.quantity} (expected: 10)")
    print(f"    Bank balance: {bank.balance} (expected: 1000.00)")
    print(f"    Cart items:   {cart_items} (expected: 1)")

    if order_count == 0 and product.quantity == 10 and bank.balance == Decimal('1000.00') and cart_items == 1:
        print(f"\n    [OK]  All rolled back cleanly.")
    else:
        print(f"\n    [BUG] Partial data persisted! Database is corrupted.")


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 3: CHECKOUT FAILURE — ProductOrder Creation Crashes
# ═══════════════════════════════════════════════════════════════════════════════

def demo_checkout_productorder_failure():
    banner("DEMO 3: Checkout ProductOrder Creation Failure")
    print("Simulating: Payment succeeds, order created, stock deducted,")
    print("            THEN ProductOrder.objects.create crashes.\n")
    print("WITH transaction.atomic: Everything rolled back.")
    print("WITHOUT transaction.atomic: Order exists, stock deducted, bank charged,")
    print("                            but NO ProductOrder records — CORRUPTED!\n")

    # cleanup()

    user = User.objects.create_user(
        username='demo_buyer2', password='pass', email='demo_buyer2@gmail.com')
    bank = Bank.objects.create(user=user, balance=Decimal('1000.00'))
    cart = Cart.objects.create(user=user)
    product = Product.objects.create(
        name='Demo Product 2', price=Decimal('100.00'), quantity=10)
    CartProduct.objects.create(cart=cart, product=product, quantity=2)

    show_db("BEFORE")

    import store.models
    original_create = store.models.ProductOrder.objects.create

    def fake_create(*args, **kwargs):
        print(f"\n    [FAKE] ProductOrder.objects.create: CRASHING!")
        raise Exception("DB crashed during ProductOrder creation!")

    store.models.ProductOrder.objects.create = fake_create

    try:
        order, error, items = checkout_cart_safely(user)
    except Exception as e:
        print(f"\n>>> Exception raised: {e}")
        order = None

    store.models.ProductOrder.objects.create = original_create

    show_db("AFTER")

    order_count = Order.objects.count()
    product.refresh_from_db()
    bank.refresh_from_db()
    cart_items = CartProduct.objects.filter(cart=cart).count()
    productorder_count = ProductOrder.objects.count()

    print(f"\n>>> RESULTS:")
    print(f"    Orders:        {order_count}")
    print(f"    ProductOrders: {productorder_count} (expected: 0)")
    print(f"    Stock:         {product.quantity} (expected: 10)")
    print(f"    Bank balance:  {bank.balance} (expected: 1000.00)")
    print(f"    Cart items:    {cart_items} (expected: 1)")

    if order_count == 0 and productorder_count == 0 and product.quantity == 10 and bank.balance == Decimal('1000.00'):
        print(f"\n    [OK]  All rolled back cleanly.")
    else:
        print(
            f"\n    [BUG] Partial data persisted! Order exists but no ProductOrders.")


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO 4: ORDER CANCEL — Refund Succeeds, Stock Restore Crashes
# ═══════════════════════════════════════════════════════════════════════════════

def demo_order_cancel_failure():
    banner("DEMO 4: Order Cancel — Refund OK, Stock Restore Crashes")
    print("Simulating: Refund succeeds, then stock restoration crashes.\n")
    print("WITH transaction.atomic: Refund + stock restore rolled back. Order stays pending.")
    print("WITHOUT transaction.atomic: Bank refunded, stock NOT restored, order may be cancelled — CORRUPTED!\n")

    # cleanup()

    user = User.objects.create_user(
        username='demo_buyer3', password='pass', email='demo_buyer3@gmail.com')
    bank = Bank.objects.create(user=user, balance=Decimal('800.00'))
    cart = Cart.objects.create(user=user)
    product = Product.objects.create(
        name='Demo Product 3', price=Decimal('100.00'), quantity=8)
    order = Order.objects.create(
        user=user, status='pending', total_amount=Decimal('200.00'))
    ProductOrder.objects.create(
        product=product, order=order, quantity=2, price=Decimal('100.00'))

    show_db("BEFORE")

    import store.models
    original_filter = store.models.Product.objects.filter

    def fake_filter(*args, **kwargs):
        qs = original_filter(*args, **kwargs)

        def fake_qs_update(*args, **kwargs):
            print(f"\n    [FAKE] Product.objects.filter().update: CRASHING!")
            raise Exception("DB crashed during stock restore!")

        qs.update = fake_qs_update
        return qs

    store.models.Product.objects.filter = fake_filter

    factory = APIRequestFactory()
    request = factory.post(f'/order/{order.id}/cancel/')
    request.user = user
    force_authenticate(request, user=user)

    from django.db.models import QuerySet
    original_update = QuerySet.update

    def fake_update(self, **kwargs):
        if 'quantity' in kwargs:
            print(f"\n    [FAKE] QuerySet.update: CRASHING!")
            raise Exception("DB crashed during stock restore!")
        return original_update(self, **kwargs)

    QuerySet.update = fake_update

    try:
        response = order_cancel(request, order.id)
        print(f"\n>>> Response: {response.status_code} — {response.data}")
    except Exception as e:
        print(f"\n>>> Exception raised: {e}")
    finally:
        QuerySet.update = original_update

    store.models.Product.objects.filter = original_filter

    show_db("AFTER")

    order.refresh_from_db()
    product.refresh_from_db()
    bank.refresh_from_db()

    print(f"\n>>> RESULTS:")
    print(f"    Order status: {order.status} (expected: pending)")
    print(f"    Stock:        {product.quantity} (expected: 8)")
    print(f"    Bank balance: {bank.balance} (expected: 800.00)")

    if order.status == 'pending' and product.quantity == 8 and bank.balance == Decimal('800.00'):
        print(f"\n    [OK]  All rolled back cleanly.")
    else:
        print(
            f"\n    [BUG] Partial changes persisted! Database is inconsistent.")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    cleanup()
    demo_user_create_failure()
    demo_checkout_payment_failure()
    demo_checkout_productorder_failure()
    demo_order_cancel_failure()

    banner("ALL DEMOS COMPLETE")
    sys.stdout.close()
    sys.stdout = sys.stdout.terminal
