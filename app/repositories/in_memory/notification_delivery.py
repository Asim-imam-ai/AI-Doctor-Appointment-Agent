"""In-memory NotificationDelivery repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from app.models import NotificationDeliveryModel, NotificationStatus
from app.repositories.base import NotificationDeliveryRepository


class InMemoryNotificationDeliveryRepository(NotificationDeliveryRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, NotificationDeliveryModel] = {}

    def create(self, delivery: NotificationDeliveryModel) -> NotificationDeliveryModel:
        self._storage[delivery.id] = delivery
        return delivery

    def get_by_id(self, delivery_id: uuid.UUID) -> Optional[NotificationDeliveryModel]:
        return self._storage.get(delivery_id)

    def update_status(
        self,
        delivery_id: uuid.UUID,
        status: NotificationStatus,
        provider_response_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[NotificationDeliveryModel]:
        d = self._storage.get(delivery_id)
        if not d:
            return None
        updates: dict = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if provider_response_id is not None:
            updates["provider_response_id"] = provider_response_id
        if error_message is not None:
            updates["error_message"] = error_message
        updated = d.model_copy(update=updates)
        self._storage[delivery_id] = updated
        return updated
