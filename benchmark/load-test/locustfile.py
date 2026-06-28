import uuid
import random
from locust import HttpUser, task, between


class WebhookUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(7)
    def approve(self):
        self.client.post(
            "/api/webhook/",
            json={
                "idempotency_key": str(uuid.uuid4()),
                "user_id": f"user-{random.randint(1, 1000)}",
                "amount": random.randint(1_000, 10_000_000),
                "currency": "IDR",
                "merchant_name": "Normal Merchant",
                "description": "routine payment",
                "memo": "",
                "location": "Jakarta",
            },
        )

    @task(3)
    def block(self):
        self.client.post(
            "/api/webhook/",
            json={
                "idempotency_key": str(uuid.uuid4()),
                "user_id": f"user-{random.randint(1, 1000)}",
                "amount": random.randint(60_000_000, 200_000_000),
                "currency": "IDR",
                "merchant_name": "Suspicious Merchant",
                "description": "large transfer",
                "memo": "",
                "location": "Jakarta",
            },
        )
