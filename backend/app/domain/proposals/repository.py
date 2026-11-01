"""Durable approval proposal persistence contract."""

import uuid
from datetime import datetime
from typing import Any, Protocol


class ProposalRepository(Protocol):
    def create(
        self,
        proposal_id: uuid.UUID,
        patient_id: uuid.UUID,
        action: str,
        version: int,
        payload: dict[str, Any],
        expires_at: datetime,
    ) -> None: ...
    def get(
        self, proposal_id: uuid.UUID, patient_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None: ...
    def reject(
        self, proposal_id: uuid.UUID, patient_id: uuid.UUID, version: int
    ) -> dict[str, Any]: ...
    def execute(
        self,
        proposal_id: uuid.UUID,
        patient_id: uuid.UUID,
        version: int,
        cancellation_window_minutes: int,
    ) -> dict[str, Any]: ...
