"""Specter core infrastructure — configuration, context, evidence, and authorization."""

from specter.core.authorization import ScopeEnforcer, require_approval, require_scope
from specter.core.config import SpecterConfig
from specter.core.context import OperationContext
from specter.core.evidence import EvidenceCollector, EvidenceRecord
from specter.core.exceptions import (
    AuthorizationRequired,
    SpecterConnectionError,
    DeviceNotFound,
    EvidenceIntegrityError,
    ScopeViolation,
    SpecterError,
)

__all__ = [
    # config
    "SpecterConfig",
    # context
    "OperationContext",
    # evidence
    "EvidenceCollector",
    "EvidenceRecord",
    # authorization
    "ScopeEnforcer",
    "require_approval",
    "require_scope",
    # exceptions
    "AuthorizationRequired",
    "SpecterConnectionError",
    "DeviceNotFound",
    "EvidenceIntegrityError",
    "ScopeViolation",
    "SpecterError",
]
