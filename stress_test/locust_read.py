"""Locust read-only — used by: python stress_test/run.py lb"""

from locust import HttpUser, between, task


class ReadUser(HttpUser):
    wait_time = between(0.1, 0.3)

    @task(3)
    def products(self):
        self.client.get("/api/product/all", name="/api/product/all")

    @task(1)
    def best_sellers(self):
        self.client.get("/api/product/best-sellers", name="/api/product/best-sellers")
