from locust import HttpUser, between, task
import random


def login_as_user(client, user_id):
    username = f"user{user_id - 1}"
    response = client.post(
        "/api/user/login",
        json={"username": username, "password": "password123"},
        name="/api/user/login",
    )
    if response.status_code != 200:
        return None
    return response.json().get("access")


class StressCheckoutUser(HttpUser):
    weight = 3
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.user_id = random.randint(1, 300)
        token = login_as_user(self.client, self.user_id)
        if token:
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(5)
    def confirm_payment(self):
        self.client.post(
            f"/api/cart/confirm/{self.user_id}",
            name="/api/cart/confirm/[user_id]",
        )

    @task(2)
    def show_cart(self):
        self.client.get(
            f"/api/cart/show/{self.user_id}",
            name="/api/cart/show/[user_id]",
        )

    @task(1)
    def list_products(self):
        self.client.get("/api/product/all", name="/api/product/all")


class StressBrowseUser(HttpUser):
    weight = 1
    wait_time = between(0.1, 0.4)

    @task(3)
    def list_products(self):
        self.client.get("/api/product/all", name="/api/product/all")

    @task(2)
    def best_sellers(self):
        self.client.get("/api/product/best-sellers", name="/api/product/best-sellers")

    @task(1)
    def lrt_status(self):
        self.client.get("/api/load-balance/lrt-status", name="/api/load-balance/lrt-status")


class EcommerceUser(HttpUser):
    weight = 1
    wait_time = between(0.5, 1.0)

    user_ids = list(range(1, 100))
    product_ids = list(range(1, 200))

    @task
    def create_order(self):
        user_id = random.choice(self.user_ids)
        product_id = random.choice(self.product_ids)

        token = login_as_user(self.client, user_id)
        if not token:
            return

        headers = {"Authorization": f"Bearer {token}"}

        add_response = self.client.post(
            "/api/cart-product/create",
            json={"user_id": user_id, "product_id": product_id, "quantity": 1},
            headers=headers,
            name="/api/cart-product/create",
        )
        if add_response.status_code not in (200, 201):
            return

        confirm_response = self.client.post(
            f"/api/cart/confirm/{user_id}",
            headers=headers,
            name="/api/cart/confirm/[user_id]",
        )
        if confirm_response.status_code != 200:
            return

        orders_response = self.client.get(
            f"/api/order/show/{user_id}",
            headers=headers,
            name="/api/order/show/[user_id]",
        )
        if orders_response.status_code != 200:
            return

        orders = orders_response.json()
        if not orders:
            return

        order_id = orders[-1]["order_id"]
        for status in ("preparing", "delivering", "success"):
            self.client.post(
                f"/api/order/change-status/{order_id}",
                json={"status": status},
                headers=headers,
                name="/api/order/change-status/[order_id]",
            )
