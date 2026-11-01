"""MemoryService: Business logic layer for managing user preferences and structured memories."""

import logging
import re
import uuid
from datetime import datetime
from typing import List, Optional

from app.domain.models import MemoryItemModel, MemorySource, MemoryType
from app.domain.repository import MemoryRepository

logger = logging.getLogger(__name__)

# Strict allowlist of keys supported for memory creation/persistence
ALLOWED_MEMORY_KEYS = {
    "preferred_specialty": MemoryType.PREFERRED_SPECIALTY,
    "preferred_doctor": MemoryType.PREFERRED_DOCTOR,
    "preferred_time_range": MemoryType.PREFERRED_TIME_RANGE,
    "timezone": MemoryType.TIMEZONE,
}

# Sensitive/Unallowed patterns that must NEVER be persisted in general memory
SENSITIVE_MEDICAL_PATTERNS = [
    r"\bdiagnose\b",
    r"\bdiagnosis\b",
    r"\bsymptom\b",
    r"\bchest\s+pain\b",
    r"\bmedication\b",
    r"\bprescription\b",
    r"\bdosage\b",
    r"\bcancer\b",
    r"\bdisease\b",
    r"\billness\b",
    r"\btreatment\b",
]


class MemoryService:
    """Service governing memory creation, policy validation, retrieval, and deletion."""

    def __init__(self, memory_repo: MemoryRepository):
        self.memory_repo = memory_repo

    def validate_memory_content(self, key: str, value: str) -> None:
        """Enforces policy constraints on memory key and value."""
        norm_key = key.strip().lower()
        if norm_key not in ALLOWED_MEMORY_KEYS:
            raise ValueError(
                f"Memory key '{key}' is not allowed. Supported keys: {list(ALLOWED_MEMORY_KEYS.keys())}"
            )

        if not value or not value.strip():
            raise ValueError("Memory value cannot be empty.")

        if len(value) > 500:
            raise ValueError(
                "Memory value exceeds maximum allowed length of 500 characters."
            )

        # Inspect value for sensitive medical content injection
        lower_val = value.lower()
        for pattern in SENSITIVE_MEDICAL_PATTERNS:
            if re.search(pattern, lower_val):
                raise ValueError(
                    f"Memory value contains disallowed sensitive/medical content matching pattern: '{pattern}'"
                )

    def save_preference(
        self,
        patient_id: uuid.UUID,
        key: str,
        value: str,
        source: MemorySource = MemorySource.EXPLICIT_USER,
        expires_at: Optional[datetime] = None,
    ) -> MemoryItemModel:
        """Validates and persists an approved user memory preference."""
        norm_key = key.strip().lower()
        self.validate_memory_content(norm_key, value)
        mem_type = ALLOWED_MEMORY_KEYS[norm_key]

        memory_item = MemoryItemModel(
            patient_id=patient_id,
            memory_type=mem_type,
            key=norm_key,
            value=value.strip(),
            source=source,
            is_active=True,
            expires_at=expires_at,
        )

        saved = self.memory_repo.create_or_update(memory_item)
        logger.info(
            f"Successfully saved memory preference '{norm_key}' for patient {patient_id}"
        )
        return saved

    def get_user_memories(
        self, patient_id: uuid.UUID, active_only: bool = True
    ) -> List[MemoryItemModel]:
        """Retrieves authorized memories for a patient."""
        return self.memory_repo.list_for_patient(patient_id, active_only=active_only)

    def get_memory_by_key(
        self, patient_id: uuid.UUID, key: str
    ) -> Optional[MemoryItemModel]:
        """Retrieves a specific memory item by key for an authorized patient."""
        norm_key = key.strip().lower()
        return self.memory_repo.get_by_key(patient_id, norm_key)

    def delete_memory(self, patient_id: uuid.UUID, memory_id: uuid.UUID) -> bool:
        """Deletes/deactivates a memory item enforcing ownership."""
        existing = self.memory_repo.get_by_id(memory_id)
        if not existing:
            return False
        if existing.patient_id != patient_id:
            logger.warning(
                f"Unauthorized memory deletion attempt: auth_patient={patient_id}, owner={existing.patient_id}"
            )
            raise PermissionError("Unauthorized: You do not own this memory item.")
        return self.memory_repo.delete_memory(memory_id)

    def delete_memory_by_key(self, patient_id: uuid.UUID, key: str) -> bool:
        """Deletes/deactivates a memory item by key enforcing ownership."""
        norm_key = key.strip().lower()
        existing = self.memory_repo.get_by_key(patient_id, norm_key)
        if not existing:
            return False
        if existing.patient_id != patient_id:
            raise PermissionError("Unauthorized: You do not own this memory item.")
        return self.memory_repo.delete_by_key(patient_id, norm_key)
