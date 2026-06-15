from rest_framework import serializers


class WebhookSerializer(serializers.Serializer):

    amount = serializers.IntegerField()
    currency = serializers.CharField(max_length=3)
    user_id = serializers.CharField()
    merchant_name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    memo = serializers.CharField(required=False, allow_blank=True, default="")
    location = serializers.CharField(required=False, allow_blank=True, default="")
    user_location = serializers.CharField(required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField()
