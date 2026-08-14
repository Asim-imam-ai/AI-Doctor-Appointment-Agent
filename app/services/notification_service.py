"""Notification provider abstractions and service layer for Phase 7."""

import logging
import uuid
from typing import Optional, Tuple

from app.models import (
    NotificationChannel,
    NotificationDeliveryModel,
    NotificationStatus,
)
from app.repositories import get_notification_delivery_repository
from app.repositories.base import NotificationDeliveryRepository

logger = logging.getLogger(__name__)


class NotificationProvider:
    """Interface for notification delivery providers."""

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        channel: NotificationChannel = NotificationChannel.EMAIL,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Sends a notification payload.

        Returns:
            (success: bool, provider_response_id: str | None, error_message: str | None)
        """
        raise NotImplementedError


class MockNotificationProvider(NotificationProvider):
    """Mock notification provider for development and deterministic testing."""

    def __init__(self, should_fail: bool = False, is_transient: bool = False):
        self.should_fail = should_fail
        self.is_transient = is_transient
        self.sent_messages: list[dict] = []

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        channel: NotificationChannel = NotificationChannel.EMAIL,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        if self.should_fail:
            err_type = (
                "Transient failure: network timeout"
                if self.is_transient
                else "Permanent failure: invalid recipient"
            )
            logger.warning(
                f"MockNotificationProvider failed delivery to {recipient}: {err_type}"
            )
            return False, None, err_type

        provider_id = f"mock-msg-{uuid.uuid4().hex[:8]}"
        msg_payload = {
            "provider_id": provider_id,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "channel": channel.value if hasattr(channel, "value") else str(channel),
        }
        self.sent_messages.append(msg_payload)
        logger.info(
            f"MockNotificationProvider sent {channel} to {recipient} (ID: {provider_id})"
        )
        return True, provider_id, None


class NotificationService:
    """Service layer managing notification rendering, delivery, and audit records."""

    def __init__(
        self,
        provider: Optional[NotificationProvider] = None,
        delivery_repo: Optional[NotificationDeliveryRepository] = None,
    ):
        self.provider = provider or MockNotificationProvider()
        self.delivery_repo = delivery_repo or get_notification_delivery_repository()

    def send_notification(
        self,
        reminder_id: uuid.UUID,
        patient_id: uuid.UUID,
        recipient: str,
        subject: str,
        body: str,
        channel: NotificationChannel = NotificationChannel.EMAIL,
    ) -> NotificationDeliveryModel:
        """Renders notification delivery record and attempts provider dispatch."""
        delivery = NotificationDeliveryModel(
            reminder_id=reminder_id,
            patient_id=patient_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            status=NotificationStatus.SENDING,
        )
        saved_delivery = self.delivery_repo.create(delivery)

        success, provider_id, err_msg = self.provider.send(
            recipient=recipient,
            subject=subject,
            body=body,
            channel=channel,
        )

        final_status = NotificationStatus.SENT if success else NotificationStatus.FAILED
        updated = self.delivery_repo.update_status(
            delivery_id=saved_delivery.id,
            status=final_status,
            provider_response_id=provider_id,
            error_message=err_msg,
        )
        return updated or saved_delivery
