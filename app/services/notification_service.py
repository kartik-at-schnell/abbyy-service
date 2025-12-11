from typing import Dict, Any


class NotificationService:
    """Sends notifications/alerts for HOLDING_ZONE or other events."""

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    def send_alert(self, title: str, payload: Dict[str, Any]) -> None:
        # Placeholder: integrate with email, Slack, etc.
        print(f"ALERT: {title} - {payload}")

