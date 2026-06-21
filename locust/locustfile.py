from locust import HttpUser, task, between
import random


def login_as_user(client, user_id):
    username = f"user{user_id - 1}"
    response = client.post(
        "/api/user/login",
        json={
            "username": username,
            "password": "password123"
        }
    )
    if response.status_code != 200:
        return None
    return response.json().get("access")


class CartPaymentUser(HttpUser):

    wait_time = between(1, 2)

    def on_start(self):

        self.user_id = random.randint(1, 300)
        token = login_as_user(self.client, self.user_id)
        if token:
            self.client.headers.update({
                "Authorization": f"Bearer {token}"
            })

    @task
    def confirm_payment(self):

        self.client.post(
            f"/api/cart/confirm/{self.user_id}"
        )


class EcommerceUser(HttpUser):

    wait_time = between(0.1, 0.3)

    user_ids = list(range(1, 100))
    product_ids = list(range(1, 200))

    @task
    def create_order(self):

        try:

            user_id = random.choice(self.user_ids)
            product_id = random.choice(self.product_ids)

            token = login_as_user(self.client, user_id)
            if not token:
                return

            headers = {"Authorization": f"Bearer {token}"}

            add_response = self.client.post(
                "/api/cart-product/create",
                json={
                    "user_id": user_id,
                    "product_id": product_id,
                    "quantity": 1
                },
                headers=headers
            )

            print(
                f"ADD => user={user_id}, "
                f"product={product_id}, "
                f"status={add_response.status_code}"
            )

            confirm_response = self.client.post(
                f"/api/cart/confirm/{user_id}",
                headers=headers
            )

            print(
                f"CONFIRM => user={user_id}, "
                f"status={confirm_response.status_code}, "
                f"response={confirm_response.text}"
            )

            orders_response = self.client.get(
                f"/api/order/show/{user_id}",
                headers=headers
            )

            if orders_response.status_code != 200:
                return

            orders = orders_response.json()

            if not orders:
                return

            latest_order = orders[-1]
            order_id = latest_order["order_id"]

            self.client.post(
                f"/api/order/change-status/{order_id}",
                json={"status": "preparing"},
                headers=headers
            )

            self.client.post(
                f"/api/order/change-status/{order_id}",
                json={"status": "delivering"},
                headers=headers
            )

            self.client.post(
                f"/api/order/change-status/{order_id}",
                json={"status": "success"},
                headers=headers
            )

            print(f"SUCCESS ORDER => {order_id}")

        except Exception as e:

            print(f"ERROR => {str(e)}")



class BestSellerUser(HttpUser):

    wait_time = between(0.01, 0.05)

    @task
    def get_best_sellers(self):

        self.client.get(
            "/api/product/best-sellers"
        )         