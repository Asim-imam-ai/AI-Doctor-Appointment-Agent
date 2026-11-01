"""Supabase NotificationDelivery repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.models import NotificationDeliveryModel, NotificationStatus
from app.repositories.base import NotificationDeliveryRepository


class SupabaseNotificationDeliveryRepository(NotificationDeliveryRepository):
    def create(self, delivery: NotificationDeliveryModel) -> NotificationDeliveryModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = delivery.model_dump(mode="json")
        res = self.client.table("notification_deliveries").insert(data).execute()
        return NotificationDeliveryModel.model_validate(res.data[0])

    def get_by_id(self, delivery_id: uuid.UUID) -> Optional[NotificationDeliveryModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("notification_deliveries")
            .select("*")
            .eq("id", str(delivery_id))
            .execute()
        )
        if not res.data:
            return None
        return NotificationDeliveryModel.model_validate(res.data[0])

    def update_status(
        self,
        delivery_id: uuid.UUID,
        status: NotificationStatus,
        provider_response_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[NotificationDeliveryModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        updates: dict = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if provider_response_id is not None:
            updates["provider_response_id"] = provider_response_id
        if error_message is not None:
            updates["error_message"] = error_message
        res = (
            self.client.table("notification_deliveries")
            .update(updates)
            .eq("id", str(delivery_id))
            .execute()
        )
        if not res.data:
            return None
        return NotificationDeliveryModel.model_validate(res.data[0])
