"""FastAPI routes for Notifications and Reminders (Phase 7)."""

import logging
import uuid

from fastapi import APIRouter, HTTPException, status

from app.schemas.reminder import (
    ListRemindersResponse,
    NotificationPreferenceResponse,
    ProcessRemindersRequest,
    ProcessRemindersResponse,
    ReminderResponse,
    UpdateNotificationPreferenceRequest,
)
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get notification preferences for authenticated patient",
)
async def get_notification_preferences(patient_id: uuid.UUID):
    """Retrieves notification preferences for patient."""
    try:
        service = ReminderService()
        return service.get_user_preferences(patient_id)
    except Exception as e:
        logger.error(f"Error fetching notification preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notification preferences: {str(e)}",
        ) from e


@router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update notification preferences for authenticated patient",
)
async def update_notification_preferences(
    patient_id: uuid.UUID, request: UpdateNotificationPreferenceRequest
):
    """Updates notification preferences for patient."""
    try:
        service = ReminderService()
        return service.update_user_preferences(
            patient_id=patient_id,
            reminders_enabled=request.reminders_enabled,
            email_enabled=request.email_enabled,
            sms_enabled=request.sms_enabled,
            in_app_enabled=request.in_app_enabled,
            user_timezone=request.user_timezone,
        )
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification preferences: {str(e)}",
        ) from e


@router.get(
    "/reminders",
    response_model=ListRemindersResponse,
    status_code=status.HTTP_200_OK,
    summary="List reminders for authenticated patient",
)
async def list_patient_reminders(patient_id: uuid.UUID):
    """Lists scheduled/sent reminders for patient."""
    try:
        service = ReminderService()
        reminders = service.reminder_repo.list_for_patient(patient_id)
        return ListRemindersResponse(reminders=reminders, total=len(reminders))
    except Exception as e:
        logger.error(f"Error listing reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reminders: {str(e)}",
        ) from e


@router.get(
    "/reminders/{reminder_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reminder details by ID",
)
async def get_reminder_by_id(reminder_id: uuid.UUID, patient_id: uuid.UUID):
    """Retrieves details of a specific reminder after ownership verification."""
    try:
        service = ReminderService()
        rem = service.reminder_repo.get_by_id(reminder_id)
        if not rem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder '{reminder_id}' not found.",
            )
        if rem.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: reminder does not belong to patient.",
            )
        return ReminderResponse(reminder=rem)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving reminder '{reminder_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reminder: {str(e)}",
        ) from e


@router.post(
    "/reminders/process-due",
    response_model=ProcessRemindersResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger worker to process due reminders (Internal/Worker Boundary)",
)
async def process_due_reminders_endpoint(request: ProcessRemindersRequest):
    """Internal/worker endpoint to process due reminders safely."""
    try:
        service = ReminderService()
        results = service.process_due_reminders(limit=request.limit)
        return ProcessRemindersResponse(
            processed_count=len(results),
            results=results,
        )
    except Exception as e:
        logger.error(f"Error executing reminder worker process: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process due reminders: {str(e)}",
        ) from e
