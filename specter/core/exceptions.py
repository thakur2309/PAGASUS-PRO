"""Custom exception hierarchy for Project Specter.

All Specter-specific exceptions inherit from :class:`SpecterError` so callers
can catch the base class when broad error handling is acceptable while still
having granular types for targeted recovery.
"""

from __future__ import annotations


class SpecterError(Exception):
    """Base exception for all Specter operations.

    Args:
        message: Human-readable description of the error.
        detail: Optional machine-readable context (dict, id, path, etc.).
    """

    def __init__(self, message: str, *, detail: object = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __repr__(self) -> str:
        cls = type(self).__name__
        if self.detail is not None:
            return f"{cls}({self.message!r}, detail={self.detail!r})"
        return f"{cls}({self.message!r})"


class ScopeViolation(SpecterError):
    """Raised when a target is outside the authorized engagement scope.

    Args:
        target: The target identifier (IP, serial, hostname) that was rejected.
        scope: The list of authorized targets that was checked against.
    """

    def __init__(self, target: str, scope: list[str] | None = None) -> None:
        self.target = target
        self.scope = scope or []
        super().__init__(
            f"Target {target!r} is outside the authorized scope. "
            f"Authorized targets: {self.scope}",
            detail={"target": target, "scope": self.scope},
        )


class AuthorizationRequired(SpecterError):
    """Raised when an operation requires explicit human approval before proceeding.

    Args:
        action: Description of the action that needs approval.
    """

    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(
            f"Human authorization required for: {action}",
            detail={"action": action},
        )


class DeviceNotFound(SpecterError):
    """Raised when a required mobile device is not connected or not visible.

    Args:
        identifier: Device serial, UDID, or descriptive name that was expected.
        transport: The transport layer used for discovery (e.g. ``"adb"``, ``"usbmuxd"``).
    """

    def __init__(self, identifier: str, transport: str = "unknown") -> None:
        self.identifier = identifier
        self.transport = transport
        super().__init__(
            f"Device {identifier!r} not found via {transport}",
            detail={"identifier": identifier, "transport": transport},
        )


class SpecterConnectionError(SpecterError):
    """Raised when an ADB or iOS connection attempt fails.

    Args:
        host: The host or device endpoint that could not be reached.
        reason: Short description of the failure mode.
    """

    def __init__(self, host: str, reason: str = "connection refused") -> None:
        self.host = host
        self.reason = reason
        super().__init__(
            f"Connection to {host!r} failed: {reason}",
            detail={"host": host, "reason": reason},
        )


class EvidenceIntegrityError(SpecterError):
    """Raised when a SHA-256 hash verification of evidence data fails.

    Args:
        evidence_file: Path or identifier of the evidence artifact.
        expected: The expected SHA-256 hex digest.
        actual: The SHA-256 hex digest that was computed.
    """

    def __init__(self, evidence_file: str, expected: str, actual: str) -> None:
        self.evidence_file = evidence_file
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Evidence integrity check failed for {evidence_file!r}: "
            f"expected {expected}, got {actual}",
            detail={
                "evidence_file": evidence_file,
                "expected": expected,
                "actual": actual,
            },
        )
