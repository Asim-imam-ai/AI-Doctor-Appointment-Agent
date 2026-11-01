"""Generic durable approval request and response schemas."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ApprovalRequest(BaseModel):
    version: int = Field(ge=1)
    decision: ApprovalDecision


class ApprovalResponse(BaseModel):
    proposal_id: str
    status: str
    result: dict[str, Any] | None = None
