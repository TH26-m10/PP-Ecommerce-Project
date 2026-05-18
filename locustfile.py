from locust import HttpUser, task, between
import random


class EcommerceUser(HttpUser):

    wait_time = between(0.1, 0.3)

    # users موجودين
    user_ids = list(range(1, 100))

    # products موجودة
    product_ids = list(range(1, 200))


    @task
    def create_order(self):

        try:

            # =========================
            # random user/product
            # =========================

            user_id = random.choice(
                self.user_ids
            )

            product_id = random.choice(
                self.product_ids
            )

            # =========================
            # add product to cart
            # =========================

            add_response = self.client.post(
                "/api/cart-product/create",
                json={
                    "user_id": user_id,
                    "product_id": product_id,
                    "quantity": 1
                }
            )

            print(
                f"ADD => user={user_id}, "
                f"product={product_id}, "
                f"status={add_response.status_code}"
            )

            # =========================
            # confirm payment
            # =========================

            confirm_response = self.client.get(
                f"/api/cart/confirm/{user_id}"
            )

            print(
                f"CONFIRM => user={user_id}, "
                f"status={confirm_response.status_code}, "
                f"response={confirm_response.text}"
            )

            # =========================
            # get orders
            # =========================

            orders_response = self.client.get(
                f"/api/order/show/{user_id}"
            )

            if orders_response.status_code != 200:
                return

            orders = orders_response.json()

            if not orders:
                return

            latest_order = orders[-1]

            order_id = latest_order["order_id"]

            # =========================
            # preparing
            # =========================

            self.client.post(
                f"/api/order/change-status/{order_id}",
                json={
                    "status": "preparing"
                }
            )

            # =========================
            # delivering
            # =========================

            self.client.post(
                f"/api/order/change-status/{order_id}",
                json={
                    "status": "delivering"
                }
            )

            # =========================
            # success
            # =========================

            self.client.post(
                f"/api/order/change-status/{order_id}",
                json={
                    "status": "success"
                }
            )

            print(
                f"SUCCESS ORDER => {order_id}"
            )

        except Exception as e:

            print(f"ERROR => {str(e)}")