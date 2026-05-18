from locust import HttpUser, task, between
import random


class CartPaymentUser(HttpUser):

    wait_time = between(1, 2)

    def on_start(self):

        self.user_id = random.randint(1, 301)

    @task
    def confirm_payment(self):

        self.client.post(
            f"/api/cart/confirm/{self.user_id}"
        )
