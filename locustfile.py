from locust import HttpUser, task, between
import uuid

class WebhookUser(HttpUser):
    wait_time = between(0.1, 0.3)


    @task
    def send_webhook(self):
        self.client.post("/api/webhook/", json={
            "idempotency_key": str(uuid.uuid4()),
            "user_id": "user-001",
            "amount": 60000000,
            "currency": "IDR",
            "merchant_name": "Test Merchant",
            "description": "test transaction",
            "memo": "test",
            "location": "Jakarta"
        })
    
    