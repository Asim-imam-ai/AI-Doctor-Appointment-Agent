"""Schemas package initialization."""

from app.schemas.agent import AgentStateSchema
from app.schemas.appointment import (
    AppointmentBase,
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatus,
)
from app.schemas.availability import DoctorAvailabilityResponse, TimeSlot
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, MessageRole
from app.schemas.common import HealthCheckResponse, ResponseWrapper
from app.schemas.doctor import DoctorBase, DoctorResponse
from app.schemas.management_agent import (
    ApproveCancellationApiResponse,
    ApproveReschedulingApiResponse,
    CancellationApprovalDecision,
    CancellationApprovalRequest,
    CancellationProposal,
    CancellationResult,
    PrepareCancellationApiRequest,
    PrepareCancellationApiResponse,
    PrepareReschedulingApiRequest,
    PrepareReschedulingApiResponse,
    ReschedulingApprovalDecision,
    ReschedulingApprovalRequest,
    ReschedulingProposal,
    ReschedulingResult,
)
from app.schemas.patient import PatientBase, PatientCreate, PatientResponse
from app.schemas.reminder import (
    ListRemindersResponse,
    NotificationPreferenceResponse,
    ProcessRemindersRequest,
    ProcessRemindersResponse,
    ReminderResponse,
    UpdateNotificationPreferenceRequest,
)

__all__ = [
    "HealthCheckResponse",
    "ResponseWrapper",
    "MessageRole",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "PatientBase",
    "PatientCreate",
    "PatientResponse",
    "DoctorBase",
    "DoctorResponse",
    "AppointmentStatus",
    "AppointmentBase",
    "AppointmentCreate",
    "AppointmentResponse",
    "TimeSlot",
    "DoctorAvailabilityResponse",
    "AgentStateSchema",
    "CancellationProposal",
    "ReschedulingProposal",
    "CancellationApprovalDecision",
    "CancellationApprovalRequest",
    "ReschedulingApprovalDecision",
    "ReschedulingApprovalRequest",
    "CancellationResult",
    "ReschedulingResult",
    "PrepareCancellationApiRequest",
    "PrepareCancellationApiResponse",
    "ApproveCancellationApiResponse",
    "PrepareReschedulingApiRequest",
    "PrepareReschedulingApiResponse",
    "ApproveReschedulingApiResponse",
    "NotificationPreferenceResponse",
    "UpdateNotificationPreferenceRequest",
    "ReminderResponse",
    "ListRemindersResponse",
    "ProcessRemindersRequest",
    "ProcessRemindersResponse",
]
