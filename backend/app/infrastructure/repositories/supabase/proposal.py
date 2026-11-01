"""Durable approval proposal adapter."""

import uuid
from datetime import datetime
from typing import Any

from app.domain.proposals.repository import ProposalRepository
from app.infrastructure.db.transactions import execute_postgres_transaction
from app.infrastructure.repositories.supabase.base import SupabaseRepository


class SupabaseProposalRepository(SupabaseRepository, ProposalRepository):
    def create(
        self,
        proposal_id: uuid.UUID,
        patient_id: uuid.UUID,
        action: str,
        version: int,
        payload: dict[str, Any],
        expires_at: datetime,
    ) -> None:
        self.client.table("appointment_proposals").insert(
            {
                "id": str(proposal_id),
                "patient_id": str(patient_id),
                "action": action,
                "version": version,
                "status": "PENDING_APPROVAL",
                "payload": payload,
                "expires_at": expires_at.isoformat(),
            }
        ).execute()

    def get(
        self, proposal_id: uuid.UUID, patient_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        query = (
            self.client.table("appointment_proposals")
            .select("*")
            .eq("id", str(proposal_id))
        )
        if patient_id is not None:
            query = query.eq("patient_id", str(patient_id))
        result = query.maybe_single().execute()
        return result.data if isinstance(result.data, dict) else None

    def reject(
        self, proposal_id: uuid.UUID, patient_id: uuid.UUID, version: int
    ) -> dict[str, Any]:
        result = execute_postgres_transaction(
            self.client,
            "reject_appointment_proposal",
            {
                "p_proposal_id": str(proposal_id),
                "p_patient_id": str(patient_id),
                "p_version": version,
            },
        )
        return result

    def execute(
        self,
        proposal_id: uuid.UUID,
        patient_id: uuid.UUID,
        version: int,
        cancellation_window_minutes: int,
    ) -> dict[str, Any]:
        result = execute_postgres_transaction(
            self.client,
            "execute_appointment_proposal",
            {
                "p_proposal_id": str(proposal_id),
                "p_patient_id": str(patient_id),
                "p_version": version,
                "p_cancellation_window_minutes": cancellation_window_minutes,
            },
        )
        return result

    @staticmethod
    def _result(data: Any) -> dict[str, Any]:
        if isinstance(data, list) and data and isinstance(data[0], dict):
            data = data[0]
        if not isinstance(data, dict):
            raise RuntimeError("Proposal RPC returned an invalid response.")
        result = data.get("result", data)
        if not isinstance(result, dict):
            raise RuntimeError("Proposal RPC returned an invalid result.")
        if result.get("error"):
            raise ValueError(str(result["error"]))
        return result
