"""Shared ownership, persistence, and transition boundary for all proposals."""

import uuid
from datetime import datetime
from typing import Any

from app.domain.proposals.repository import ProposalRepository


class ProposalLifecycle:
    """Coordinates durable proposal access and transitions without owning storage."""

    def __init__(self, repository: ProposalRepository):
        self.repository = repository

    def create(
        self,
        proposal_id: uuid.UUID,
        patient_id: uuid.UUID,
        action: str,
        version: int,
        payload: dict[str, Any],
        expires_at: datetime,
    ) -> None:
        if action not in {"BOOKING", "CANCELLATION", "RESCHEDULING"}:
            raise ValueError("Unsupported proposal action.")
        if version < 1:
            raise ValueError("Proposal version must be positive.")
        self.repository.create(
            proposal_id, patient_id, action, version, payload, expires_at
        )

    def get_owned(
        self,
        proposal_id: uuid.UUID,
        patient_id: uuid.UUID,
        action: str | None = None,
    ) -> dict[str, Any] | None:
        record = self.repository.get(proposal_id, patient_id)
        if record is None or (action is not None and record.get("action") != action):
            return None
        return record

    def reject(
        self, proposal_id: uuid.UUID, patient_id: uuid.UUID, version: int
    ) -> dict[str, Any]:
        result = self.repository.reject(proposal_id, patient_id, version)
        if result.get("status") != "REJECTED":
            raise ValueError("Proposal cannot be rejected.")
        return result

    def execute(
        self,
        proposal_id: uuid.UUID,
        patient_id: uuid.UUID,
        version: int,
        cancellation_window_minutes: int,
    ) -> dict[str, Any]:
        return self.repository.execute(
            proposal_id, patient_id, version, cancellation_window_minutes
        )
