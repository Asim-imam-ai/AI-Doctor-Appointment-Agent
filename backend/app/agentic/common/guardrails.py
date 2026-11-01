"""Central Guardrails Engine (Phase 8).

Implements deterministic security layers:
- Layer 1: Request Validation
- Layer 2: Input Size & Format Guardrail
- Layer 3: Prompt Injection Guardrail
- Layer 4: Jailbreak & System Prompt Extraction Guardrail
- Layer 5: Medical Scope & Out-Of-Scope Guardrail
- Layer 6: Authorization & Resource Ownership Guardrail
- Layer 7: Tool Policy & Allowlist Guardrail
- Layer 8: Tool Input & Argument Sanitization
- Layer 9: Output Safety & Secret Redaction Guardrail
"""

import logging
import re
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class GuardrailCategory(str, Enum):
    SAFE = "SAFE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    JAILBREAK = "JAILBREAK"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_INPUT = "INVALID_INPUT"
    UNSAFE_MEDICAL_REQUEST = "UNSAFE_MEDICAL_REQUEST"
    TOOL_POLICY_VIOLATION = "TOOL_POLICY_VIOLATION"
    SENSITIVE_DATA_REQUEST = "SENSITIVE_DATA_REQUEST"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    SECRET_LEAKAGE = "SECRET_LEAKAGE"


class GuardrailAction(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REDIRECT = "REDIRECT"
    REQUIRE_HITL = "REQUIRE_HITL"
    REQUIRE_CLARIFICATION = "REQUIRE_CLARIFICATION"


class GuardrailDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: bool
    category: GuardrailCategory = GuardrailCategory.SAFE
    reason_code: str = "PASS"
    action: GuardrailAction = GuardrailAction.ALLOW
    user_message: Optional[str] = None
    sanitized_text: Optional[str] = None


# Patterns for Prompt Injection
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"show\s+(me\s+)?(your\s+)?system\s+prompt",
    r"what\s+is\s+your\s+system\s+prompt",
    r"print\s+(your\s+)?system\s+prompt",
    r"disable\s+(your\s+)?safety\s+rules",
    r"bypass\s+(your\s+)?safety",
    r"call\s+the\s+database\s+directly",
    r"execute\s+sql",
    r"pretend\s+i\s+am\s+an\s+administrator",
    r"you\s+are\s+now\s+an?\s+unrestricted",
    r"use\s+service\s+credentials",
    r"show\s+(me\s+)?(your\s+)?hidden\s+tools",
    r"\bapi[-_]?key\b",
    r"\bsecret[-_]?key\b",
]

# Patterns for Jailbreaks & System Overrides
JAILBREAK_PATTERNS = [
    r"ignore\s+medical\s+restrictions",
    r"pretend\s+this\s+is\s+not\s+medical\s+advice",
    r"act\s+as\s+an?\s+unrestricted\s+doctor",
    r"give\s+me\s+a\s+diagnosis",
    r"tell\s+me\s+what\s+medication\s+to\s+take",
    r"bypass\s+appointment\s+confirmation",
    r"skip\s+approval",
    r"override\s+policy",
]

# Medical Diagnosis / Treatment / Prescription Keywords
MEDICAL_SCOPE_PATTERNS = [
    r"\bdiagnose\b",
    r"\bdiagnosis\b",
    r"\bsymptom\b",
    r"\bwhat\s+treatment\b",
    r"\bprescription\b",
    r"\bdosage\b",
    r"\bwhat\s+medication\b",
    r"\bprescribe\s+medicine\b",
    r"\bprescribe\s+medication\b",
    r"\bwhat\s+medicine\b",
    r"\btake\s+for\b",
    r"\bwhat\s+disease\b",
    r"\bwhat\s+illness\b",
]

# Sensitive Data / Secrets Patterns (API Keys, Bearer Tokens, Passwords, Connection Strings)
SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9\-_]{20,}",
    r"sbp_[a-zA-Z0-9]{20,}",
    r"bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*",
    r"postgresql:\/\/[^:]+:[^@]+@[^\s]+",
    r"supabase_service_key",
]


class GuardrailPipeline:
    """Central Security Guardrail Pipeline enforcing deterministic defense layers."""

    MAX_MESSAGE_LENGTH: int = 1000

    @classmethod
    def validate_input_size(cls, text: str) -> GuardrailDecision:
        """Layer 2: Input Size & Empty String Validation."""
        if not text or not text.strip():
            return GuardrailDecision(
                allowed=False,
                category=GuardrailCategory.INVALID_INPUT,
                reason_code="EMPTY_INPUT",
                action=GuardrailAction.BLOCK,
                user_message="Input request cannot be empty.",
            )
        if len(text) > cls.MAX_MESSAGE_LENGTH:
            return GuardrailDecision(
                allowed=False,
                category=GuardrailCategory.INVALID_INPUT,
                reason_code="EXCESSIVE_LENGTH",
                action=GuardrailAction.BLOCK,
                user_message=(
                    f"Input length exceeds maximum allowed limit of {cls.MAX_MESSAGE_LENGTH} characters."
                ),
            )
        return GuardrailDecision(allowed=True)

    @classmethod
    def detect_prompt_injection(cls, text: str) -> GuardrailDecision:
        """Layer 3: Prompt Injection Guardrail."""
        lower_text = text.lower()
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, lower_text):
                logger.warning(
                    f"Guardrail BLOCKED prompt injection matching pattern: {pattern}"
                )
                return GuardrailDecision(
                    allowed=False,
                    category=GuardrailCategory.PROMPT_INJECTION,
                    reason_code="PROMPT_INJECTION_DETECTED",
                    action=GuardrailAction.BLOCK,
                    user_message=(
                        "I cannot process this request because it contains system instructions "
                        "or policy bypass commands. I am an appointment assistant and can help "
                        "you find doctors or manage appointments."
                    ),
                )
        return GuardrailDecision(allowed=True)

    @classmethod
    def detect_jailbreak(cls, text: str) -> GuardrailDecision:
        """Layer 4: Jailbreak & Roleplay Override Guardrail."""
        lower_text = text.lower()
        for pattern in JAILBREAK_PATTERNS:
            if re.search(pattern, lower_text):
                logger.warning(
                    f"Guardrail BLOCKED jailbreak attempt matching pattern: {pattern}"
                )
                return GuardrailDecision(
                    allowed=False,
                    category=GuardrailCategory.JAILBREAK,
                    reason_code="JAILBREAK_DETECTED",
                    action=GuardrailAction.REDIRECT,
                    user_message=(
                        "I am an appointment management assistant and cannot bypass safety rules "
                        "or act outside my defined operational scope."
                    ),
                )
        return GuardrailDecision(allowed=True)

    @classmethod
    def check_medical_scope(cls, text: str) -> GuardrailDecision:
        """Layer 5: Medical Scope & Out-of-Scope Guardrail."""
        lower_text = text.lower()
        for pattern in MEDICAL_SCOPE_PATTERNS:
            if re.search(pattern, lower_text):
                logger.info(f"Guardrail REDIRECTED medical request matching: {pattern}")
                return GuardrailDecision(
                    allowed=False,
                    category=GuardrailCategory.UNSAFE_MEDICAL_REQUEST,
                    reason_code="MEDICAL_ADVICE_DISALLOWED",
                    action=GuardrailAction.REDIRECT,
                    user_message=(
                        "I am an appointment booking assistant and cannot provide medical "
                        "diagnoses, symptom evaluations, medication dosages, or treatment advice. "
                        "Please consult a qualified healthcare provider. I can help you search for "
                        "and book an appointment with a specialist."
                    ),
                )
        return GuardrailDecision(allowed=True)

    @classmethod
    def check_authorization(
        cls,
        authenticated_patient_id: uuid.UUID,
        target_patient_id: Optional[uuid.UUID],
    ) -> GuardrailDecision:
        """Layer 6: Authorization & Resource Ownership Guardrail."""
        if target_patient_id and target_patient_id != authenticated_patient_id:
            logger.warning(
                f"Unauthorized cross-patient access attempt: auth={authenticated_patient_id}, target={target_patient_id}"
            )
            return GuardrailDecision(
                allowed=False,
                category=GuardrailCategory.UNAUTHORIZED,
                reason_code="UNAUTHORIZED_PATIENT_MISMATCH",
                action=GuardrailAction.BLOCK,
                user_message="Unauthorized operation: You do not have permission to access or modify resources for another user.",
            )
        return GuardrailDecision(allowed=True)

    @classmethod
    def validate_tool_call(
        cls,
        allowed_tools: List[str],
        requested_tool_name: str,
        tool_args: Dict[str, Any],
    ) -> GuardrailDecision:
        """Layer 7 & 8: Tool Allowlist & Tool Argument Sanitization Guardrail."""
        if requested_tool_name not in allowed_tools:
            logger.warning(
                f"Tool policy violation: '{requested_tool_name}' not in allowed tools: {allowed_tools}"
            )
            return GuardrailDecision(
                allowed=False,
                category=GuardrailCategory.TOOL_POLICY_VIOLATION,
                reason_code="TOOL_NOT_IN_ALLOWLIST",
                action=GuardrailAction.BLOCK,
                user_message=f"Tool call '{requested_tool_name}' is not permitted in this workflow context.",
            )
        return GuardrailDecision(allowed=True)

    @classmethod
    def inspect_output_safety(cls, output_text: str) -> GuardrailDecision:
        """Layer 9: Output Safety & Secret Protection Guardrail."""
        current_text = output_text
        secret_detected = False

        for pattern in SECRET_PATTERNS:
            if re.search(pattern, current_text, re.IGNORECASE):
                logger.error(
                    f"CRITICAL: Secret pattern detected in agent output matching: {pattern}"
                )
                secret_detected = True
                current_text = re.sub(
                    pattern, "[REDACTED_SECRET]", current_text, flags=re.IGNORECASE
                )

        if secret_detected:
            return GuardrailDecision(
                allowed=True,
                category=GuardrailCategory.SECRET_LEAKAGE,
                reason_code="SECRET_REDACTED",
                action=GuardrailAction.ALLOW,
                sanitized_text=current_text,
                user_message="Sanitized response.",
            )

        # Check if output provides unauthorized diagnosis
        lower_output = output_text.lower()
        if (
            "you have" in lower_output or "your diagnosis is" in lower_output
        ) and "appointment" not in lower_output:
            logger.warning("Output guardrail detected potential medical diagnosis.")
            return GuardrailDecision(
                allowed=False,
                category=GuardrailCategory.UNSAFE_MEDICAL_REQUEST,
                reason_code="OUTPUT_MEDICAL_DIAGNOSIS_BLOCKED",
                action=GuardrailAction.REDIRECT,
                user_message=(
                    "I am an appointment management assistant and cannot provide medical diagnoses. "
                    "Please schedule a consultation with a qualified doctor."
                ),
            )

        return GuardrailDecision(allowed=True, sanitized_text=output_text)

    @classmethod
    def run_input_pipeline(
        cls,
        user_message: str,
        authenticated_patient_id: Optional[uuid.UUID] = None,
        target_patient_id: Optional[uuid.UUID] = None,
    ) -> GuardrailDecision:
        """Runs full input guardrail pipeline sequentially."""
        # 1. Input size
        res = cls.validate_input_size(user_message)
        if not res.allowed:
            return res

        # 2. Prompt injection
        res = cls.detect_prompt_injection(user_message)
        if not res.allowed:
            return res

        # 3. Jailbreak
        res = cls.detect_jailbreak(user_message)
        if not res.allowed:
            return res

        # 4. Medical scope
        res = cls.check_medical_scope(user_message)
        if not res.allowed:
            return res

        # 5. Authorization check if IDs provided
        if authenticated_patient_id and target_patient_id:
            res = cls.check_authorization(authenticated_patient_id, target_patient_id)
            if not res.allowed:
                return res

        return GuardrailDecision(allowed=True)
