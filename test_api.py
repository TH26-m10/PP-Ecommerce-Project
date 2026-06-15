"""Full API integration test for the e-commerce project."""
import json
import sys
import requests

BASE = "http://127.0.0.1:8001/api"
PASS = 0
FAIL = 0
ERRORS = []


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [OK]   {name}")
    else:
        FAIL += 1
        msg = f"  [FAIL] {name}" + (f" — {detail}" if detail else "")
        print(msg)
        ERRORS.append(msg)


def section(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")


def main():
    section("1. Server reachability")
    try:
        r = requests.get(f"{BASE}/product/all", timeout=10)
        ok("GET /product/all", r.status_code == 200, f"status={r.status_code}")
        products = r.json()
        ok("Products exist", len(products) > 0, f"count={len(products)}")
        product_id = products[0]["id"] if products else None
    except Exception as e:
        ok("Server reachable", False, str(e))
        print("\n*** Server not reachable. Start with: waitress-serve --port=8001 project.wsgi:application ***")
        sys.exit(1)

    section("2. Load balancer (public)")
    try:
        r = requests.get(f"{BASE}/load-balance", timeout=10)
        ok("GET /load-balance", r.status_code == 200, r.text[:100])
    except Exception as e:
        ok("GET /load-balance", False, str(e))

    section("3. User registration")
    import random
    uname = f"testuser_{random.randint(10000,99999)}"
    try:
        r = requests.post(f"{BASE}/user/create", json={
            "username": uname,
            "email": f"{uname}@test.com",
            "password": "testpass123"
        }, timeout=10)
        ok("POST /user/create", r.status_code == 201, f"status={r.status_code} {r.text[:80]}")
        new_user_id = r.json().get("user_id") if r.status_code == 201 else None
    except Exception as e:
        ok("POST /user/create", False, str(e))
        new_user_id = None

    section("4. Login (JWT)")
    token = None
    try:
        r = requests.post(f"{BASE}/user/login", json={
            "username": "user0",
            "password": "password123"
        }, timeout=10)
        ok("POST /user/login", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            token = r.json().get("access")
            ok("JWT access token received", bool(token))
    except Exception as e:
        ok("POST /user/login", False, str(e))

    if not token:
        print("\n*** Cannot continue without JWT token ***")
        summary()
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    user_id = 1

    section("5. Bank")
    try:
        r = requests.get(f"{BASE}/bank/show/{user_id}", headers=headers, timeout=10)
        ok("GET /bank/show", r.status_code == 200, f"status={r.status_code} {r.text[:80]}")
    except Exception as e:
        ok("GET /bank/show", False, str(e))

    section("6. Products (public)")
    try:
        r = requests.get(f"{BASE}/product/{product_id}", timeout=10)
        ok("GET /product/<id>", r.status_code == 200)
    except Exception as e:
        ok("GET /product/<id>", False, str(e))

    section("7. Cart — add product")
    try:
        r = requests.post(f"{BASE}/cart-product/create", headers=headers, json={
            "user_id": user_id,
            "product_id": product_id,
            "quantity": 1
        }, timeout=10)
        ok("POST /cart-product/create", r.status_code == 200, f"status={r.status_code} {r.text[:80]}")
    except Exception as e:
        ok("POST /cart-product/create", False, str(e))

    section("8. Cart — show")
    cart_product_id = None
    try:
        r = requests.get(f"{BASE}/cart/show/{user_id}", headers=headers, timeout=10)
        ok("GET /cart/show", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            ok("Cart has items", data.get("success") and len(data.get("products", [])) > 0)
            if data.get("products"):
                cart_product_id = data["products"][0]["cart_product_id"]
    except Exception as e:
        ok("GET /cart/show", False, str(e))

    section("9. Cart — update item")
    if cart_product_id:
        try:
            r = requests.post(
                f"{BASE}/cart-product/update/{cart_product_id}",
                headers=headers,
                json={"quantity": 2},
                timeout=10
            )
            ok("POST /cart-product/update", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            ok("POST /cart-product/update", False, str(e))

    section("10. Checkout / payment")
    order_id = None
    try:
        r = requests.post(f"{BASE}/cart/confirm/{user_id}", headers=headers, timeout=30)
        ok("POST /cart/confirm", r.status_code == 200, f"status={r.status_code} {r.text[:120]}")
        if r.status_code == 200:
            order_id = r.json().get("order_id")
            ok("Order created", bool(order_id))
    except Exception as e:
        ok("POST /cart/confirm", False, str(e))

    section("11. Orders — show")
    try:
        r = requests.get(f"{BASE}/order/show/{user_id}", headers=headers, timeout=10)
        ok("GET /order/show", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        ok("GET /order/show", False, str(e))

    section("12. Order status flow")
    if order_id:
        for status in ["preparing", "delivering", "success"]:
            try:
                r = requests.post(
                    f"{BASE}/order/change-status/{order_id}",
                    headers=headers,
                    json={"status": status},
                    timeout=10
                )
                ok(f"Status -> {status}", r.status_code == 200, f"status={r.status_code} {r.text[:60]}")
            except Exception as e:
                ok(f"Status -> {status}", False, str(e))

    section("13. Auth — deny without token")
    try:
        r = requests.get(f"{BASE}/cart/show/{user_id}", timeout=10)
        ok("Cart without token denied", r.status_code == 401, f"status={r.status_code}")
    except Exception as e:
        ok("Cart without token denied", False, str(e))

    section("14. Auth — deny wrong user")
    if new_user_id and new_user_id != user_id:
        try:
            r2 = requests.post(f"{BASE}/user/login", json={
                "username": uname, "password": "testpass123"
            }, timeout=10)
            t2 = r2.json().get("access") if r2.status_code == 200 else None
            if t2:
                r = requests.get(
                    f"{BASE}/cart/show/{user_id}",
                    headers={"Authorization": f"Bearer {t2}"},
                    timeout=10
                )
                ok("Wrong user denied", r.status_code == 403, f"status={r.status_code}")
        except Exception as e:
            ok("Wrong user denied", False, str(e))

    summary()


def summary():
    print(f"\n{'='*50}")
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    if ERRORS:
        print("\nFailures:")
        for e in ERRORS:
            print(e)
    print(f"{'='*50}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
