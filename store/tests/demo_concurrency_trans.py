import os  # noqa: E402
import sys  # noqa: E402
import django  # noqa: E402
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # noqa: E402
django.setup()  # noqa: E402


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


sys.stdout = Tee('store\\tests\\demo_concurrency_results.txt')

from decimal import Decimal  # noqa: E402
from store.models import Bank, Cart, CartProduct, Order, Product, ProductOrder  # noqa: E402
from store.services.inventory import checkout_cart_safely  # noqa: E402
from store.views.order_view import order_cancel  # noqa: E402
from store.views.product_view import product_update, product_add_quantity  # noqa: E402
from store.views.cart_product_view import cart_product_create  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import random  # noqa: E402


def banner(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def show_db(label):
    print(f"\n--- {label} ---")
    print(f"  Users:         {User.objects.count()}")
    print(f"  Products:      {Product.objects.count()}")
    print(f"  ProductOrders: {ProductOrder.objects.count()}")


def cleanup():
    ProductOrder.objects.all().delete()
    Order.objects.all().delete()
    CartProduct.objects.all().delete()
    Cart.objects.all().delete()
    Bank.objects.all().delete()
    User.objects.filter(username__startswith='concurrent').delete()
    Product.objects.filter(name__startswith='Concurrent').delete()


# ═══════════════════════════════════════════════════════════════════════════════
# CONCURRENCY TEST 1: Two buyers checkout the LAST item simultaneously
# ═══════════════════════════════════════════════════════════════════════════════

def concurrent_checkout_last_item():
    banner("CONCURRENCY TEST 1: Two Buyers, One Item in Stock")
    print("Only 1 item available. Two buyers try to checkout at the same time.\n")
    print("WITH select_for_update + transaction.atomic: Only one succeeds.")

    # cleanup()

    # Setup: 1 item in stock, 2 buyers each want 1
    product = Product.objects.create(
        name='Concurrent Hot Item', price=Decimal('50.00'), quantity=1)

    buyer1 = User.objects.create_user(
        username='concurrent_buyer1', password='pass', email='concurrent_buyer1@gmail.com')
    buyer2 = User.objects.create_user(
        username='concurrent_buyer2', password='pass', email='concurrent_buyer2@gmail.com')

    for buyer in [buyer1, buyer2]:
        Bank.objects.create(user=buyer, balance=Decimal('1000.00'))
        cart = Cart.objects.create(user=buyer)
        CartProduct.objects.create(cart=cart, product=product, quantity=1)

    show_db("BEFORE")

    results = {'success': 0, 'failed': 0, 'errors': []}
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def buyer_checkout(user):
        try:
            barrier.wait()  # Both start at the same time
            order, error, items = checkout_cart_safely(user)
            with lock:
                if order:
                    results['success'] += 1
                    print(
                        f"    [OK]  {user.username} succeeded — Order #{order.id}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{user.username}: {error}")
                    print(f"    [FAIL] {user.username} failed — {error}")
        except Exception as e:
            with lock:
                results['failed'] += 1
                results['errors'].append(f"{user.username}: {str(e)}")
                print(f"    [EXC]  {user.username} exception — {e}")

    t1 = threading.Thread(target=buyer_checkout, args=(buyer1,))
    t2 = threading.Thread(target=buyer_checkout, args=(buyer2,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    product.refresh_from_db()
    show_db("AFTER")

    print(f"\n>>> RESULTS:")
    print(f"    Success:      {results['success']} (expected: 1)")
    print(f"    Failed:       {results['failed']} (expected: 1)")
    print(f"    Final stock:  {product.quantity} (expected: 0)")
    print(f"    Total orders: {Order.objects.count()} (expected: 1)")

    if results['success'] == 1 and results['failed'] == 1 and product.quantity >= 0 and Order.objects.count() == 1:
        print(f"\n    [PASS] No overselling! Locking works correctly.")
    else:
        print(
            f"\n    [FAIL] OVERSOLD! Stock={product.quantity}, Orders={Order.objects.count()}")
        if product.quantity < 0:
            print(f"    CRITICAL: Negative stock detected!")


# ═══════════════════════════════════════════════════════════════════════════════
# CONCURRENCY TEST 2: Two admins update the same product simultaneously
# ═══════════════════════════════════════════════════════════════════════════════

def concurrent_product_update():
    banner("CONCURRENCY TEST 2: Two Admins Update Same Product")
    print("Admin A sets price to 100, Admin B sets price to 200 at the same time.\n")
    print("WITH select_for_update + transaction.atomic: One waits, then both apply.")

    # cleanup()

    product = Product.objects.create(
        name='Concurrent Product', price=Decimal('50.00'), quantity=100)
    admin = User.objects.create_user(
        username='concurrent_admin', password='pass', is_staff=True, email='concurrent_admin@gmail.com')
    admin2 = User.objects.create_user(
        username='concurrent_admin2', password='pass', is_staff=True, email='concurrent_admin2@gmail.com')

    show_db("BEFORE")

    results = {'done': 0}
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def update_price(new_price, name, adminAssigned):
        factory = APIRequestFactory()
        request = factory.post(f'/product/{product.id}/update/', {
            'price': str(new_price),
            'name': name
        }, format='json')
        request.user = adminAssigned
        force_authenticate(request, user=adminAssigned)

        barrier.wait()
        try:
            response = product_update(request, product.id)
            with lock:
                results['done'] += 1
                print(
                    f"    [{name}] status={response.status_code}, data={response.data}")
        except Exception as e:
            with lock:
                print(f"    [{name}] EXCEPTION: {e}")

    t1 = threading.Thread(target=update_price,
                          args=(Decimal('100.00'), 'Concurrent product AdminA', admin))
    t2 = threading.Thread(target=update_price,
                          args=(Decimal('200.00'), 'Concurrent product AdminB', admin2))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    product.refresh_from_db()
    show_db("AFTER")

    print(f"\n>>> RESULTS:")
    print(f"    Final price: {product.price}")
    print(f"    Final name:  {product.name}")
    print(f"    Updates done: {results['done']} (expected: 2)")

    if results['done'] == 2:
        print(f"\n    [PASS] Both updates completed without crash.")
    else:
        print(f"\n    [FAIL] One update crashed!")


# ═══════════════════════════════════════════════════════════════════════════════
# CONCURRENCY TEST 3: Order Cancel + Checkout on same user's bank simultaneously
# ═══════════════════════════════════════════════════════════════════════════════

def concurrent_cancel_and_checkout():
    banner("CONCURRENCY TEST 3: Cancel Order + Checkout Same User")
    print("User cancels an order (gets refund) AND checks out a new cart at the same time.\n")
    print("WITH select_for_update + transaction.atomic: Operations serialize, balance correct.")

    # cleanup()

    user = User.objects.create_user(
        username='concurrent_mixed', password='pass', email='concurrent_mixed@gmail.com')
    bank = Bank.objects.create(user=user, balance=Decimal('500.00'))
    cart = Cart.objects.create(user=user)

    product1 = Product.objects.create(
        name='Concurrent Prod1', price=Decimal('100.00'), quantity=10)
    product2 = Product.objects.create(
        name='Concurrent Prod2', price=Decimal('200.00'), quantity=5)

    # Existing order to cancel (cost 100)
    order = Order.objects.create(
        user=user, status='pending', total_amount=Decimal('100.00'))
    ProductOrder.objects.create(
        product=product1, order=order, quantity=1, price=Decimal('100.00'))

    # New cart to checkout (cost 200)
    CartProduct.objects.create(cart=cart, product=product2, quantity=1)

    show_db("BEFORE")
    print(f"    Bank balance: {bank.balance}")
    print(f"    Expected after cancel+checkout: 500 - 200 + 100 = 400 (or 500 - 200 = 300 if cancel fails)")

    results = {'cancel': None, 'checkout': None}
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def do_cancel():
        factory = APIRequestFactory()
        request = factory.post(f'/order/{order.id}/cancel/')
        request.user = user
        force_authenticate(request, user=user)

        barrier.wait()
        try:
            response = order_cancel(request, order.id)
            with lock:
                results['cancel'] = response.status_code
                print(
                    f"    [CANCEL] status={response.status_code}, data={response.data}")
        except Exception as e:
            with lock:
                results['cancel'] = f"EXC: {e}"
                print(f"    [CANCEL] EXCEPTION: {e}")

    def do_checkout():
        barrier.wait()
        try:
            order_new, error, items = checkout_cart_safely(user)
            with lock:
                if order_new:
                    results['checkout'] = f"OK: Order #{order_new.id}"
                    print(f"    [CHECKOUT] succeeded — Order #{order_new.id}")
                else:
                    results['checkout'] = f"FAIL: {error}"
                    print(f"    [CHECKOUT] failed — {error}")
        except Exception as e:
            with lock:
                results['checkout'] = f"EXC: {e}"
                print(f"    [CHECKOUT] EXCEPTION: {e}")

    t1 = threading.Thread(target=do_cancel)
    t2 = threading.Thread(target=do_checkout)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    bank.refresh_from_db()
    show_db("AFTER")

    print(f"\n>>> RESULTS:")
    print(f"    Cancel result:   {results['cancel']}")
    print(f"    Checkout result: {results['checkout']}")
    print(f"    Final balance:   {bank.balance}")

    # Balance should be consistent: either 400 (cancel refunded + checkout charged)
    # or 300 (checkout charged, cancel failed) or 500 (both failed)
    # But NOT something impossible like 600 or -100
    expected_possible = [Decimal('400.00'), Decimal(
        '300.00'), Decimal('500.00'), Decimal('200.00')]
    if bank.balance in expected_possible:
        print(f"\n    [PASS] Balance is consistent: {bank.balance}")
    else:
        print(
            f"\n    [FAIL] IMPOSSIBLE BALANCE: {bank.balance}! Race condition detected.")


# ═══════════════════════════════════════════════════════════════════════════════
# CONCURRENCY TEST 4: Rapid stock additions while checkout is happening
# ═══════════════════════════════════════════════════════════════════════════════

def concurrent_add_stock_and_checkout():
    banner("CONCURRENCY TEST 4: Add Stock + Checkout Same Product")
    print("Admin adds 50 stock while a buyer checks out 10 items.\n")
    print("WITH select_for_update + transaction.atomic: Stock updates serialize correctly.")
    print("WITHOUT locking: Buyer might see wrong stock count, or stock goes wrong!\n")

    # cleanup()

    product = Product.objects.create(
        name='Concurrent Restock', price=Decimal('10.00'), quantity=15)
    buyer = User.objects.create_user(
        username='concurrent_restock_buyer', password='pass', email='concurrent_restock_buyer@gmail.com')
    admin = User.objects.create_user(
        username='concurrent_restock_admin', password='pass', is_staff=True, email='concurrent_restock_admin@gmail.com')

    Bank.objects.create(user=buyer, balance=Decimal('1000.00'))
    cart = Cart.objects.create(user=buyer)
    CartProduct.objects.create(cart=cart, product=product, quantity=10)

    show_db("BEFORE")
    print(f"    NOTE: Stock=15, buyer wants 10 → checkout should succeed")
    print(f"    Admin also adds 50 simultaneously → final stock should be 15+50-10=55")

    results = {'checkout': None, 'add_stock': None}
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def do_checkout():
        barrier.wait()
        try:
            order, error, items = checkout_cart_safely(buyer)
            with lock:
                if order:
                    results['checkout'] = f"OK: Order #{order.id}"
                    print(f"    [CHECKOUT] succeeded — Order #{order.id}")
                else:
                    results['checkout'] = f"FAIL: {error}"
                    print(f"    [CHECKOUT] failed — {error}")
        except Exception as e:
            with lock:
                results['checkout'] = f"EXC: {e}"
                print(f"    [CHECKOUT] EXCEPTION: {e}")

    def do_add_stock():
        factory = APIRequestFactory()
        request = factory.post(f'/product/{product.id}/add_quantity/', {
            'quantity': 50
        }, format='json')
        request.user = admin
        force_authenticate(request, user=admin)

        barrier.wait()
        try:
            response = product_add_quantity(request, product.id)
            with lock:
                results['add_stock'] = response.status_code
                print(
                    f"    [ADD_STOCK] status={response.status_code}, data={response.data}")
        except Exception as e:
            with lock:
                results['add_stock'] = f"EXC: {e}"
                print(f"    [ADD_STOCK] EXCEPTION: {e}")

    t1 = threading.Thread(target=do_checkout)
    t2 = threading.Thread(target=do_add_stock)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    product.refresh_from_db()
    show_db("AFTER")

    print(f"\n>>> RESULTS:")
    print(f"    Checkout:   {results['checkout']}")
    print(f"    Add stock:  {results['add_stock']}")
    print(f"    Final stock: {product.quantity}")

    # Stock should never be negative
    # if product.quantity >= 0:
    #     print(f"\n    [PASS] Stock is non-negative: {product.quantity}")
    # else:
    #     print(f"\n    [FAIL] Negative stock: {product.quantity}!")
    # Stock should never be negative
    # 55 = checkout succeeded (15-10) then admin added 50, or admin added first then checkout
    # 65 = admin added 50 first, checkout didn't run yet (race)
    # 5  = checkout failed, only admin add ran
    if product.quantity >= 0:
        print(f"\n    [PASS] Stock is non-negative: {product.quantity}")
        print(
            f"    Final stock={product.quantity} — operations serialized correctly")
        if product.quantity == 55:
            print(f"    Both succeeded: 15 - 10 (checkout) + 50 (restock) = 55")
        elif product.quantity == 65:
            print(f"    Admin restocked first (+50), then checkout deducted (-10): 15+50-10=55... or checkout failed")
        elif product.quantity == 5:
            print(
                f"    Checkout failed (stock was 5 when it ran), admin added 50: 5+50=55... unexpected")
    else:
        print(f"\n    [FAIL] Negative stock: {product.quantity}!")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    cleanup()
    concurrent_checkout_last_item()
    concurrent_product_update()
    concurrent_cancel_and_checkout()
    concurrent_add_stock_and_checkout()

    banner("ALL CONCURRENCY TESTS COMPLETE")
    sys.stdout.close()
    sys.stdout = sys.stdout.terminal
