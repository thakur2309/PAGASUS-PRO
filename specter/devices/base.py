"""Abstract base class for mobile device assessment.

Defines the :class:`DeviceAssessor` interface that both the Android (ADB)
and iOS (pymobiledevice3) implementations must satisfy, along with the
:class:`DeviceInfo` Pydantic model used to represent discovered device
metadata.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from specter.core.evidence import EvidenceCollector
    from specter.reporting.models import Finding


class DeviceInfo(BaseModel):
    """Structured representation of a mobile device.

    Attributes:
        serial: Unique device serial / UDID.
        name: Human-readable device name (e.g. "Pixel 7").
        platform: Target platform -- ``"android"`` or ``"ios"``.
        os_version: Operating-system version string.
        model: Device model identifier.
        manufacturer: Device manufacturer (empty string when unknown).
        battery_level: Current battery percentage, ``-1`` when unavailable.
        storage_total_gb: Total on-device storage in GiB.
        storage_free_gb: Free on-device storage in GiB.
        is_rooted_jailbroken: Whether root / jailbreak indicators were found.
        extra: Arbitrary key-value pairs for platform-specific metadata.
    """

    serial: str
    name: str
    platform: str
    os_version: str
    model: str
    manufacturer: str = ""
    battery_level: int = -1
    storage_total_gb: float = 0.0
    storage_free_gb: float = 0.0
    is_rooted_jailbroken: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class DeviceAssessor(ABC):
    """Abstract base class for platform-specific device assessors.

    Concrete subclasses (e.g. ``AndroidAssessor``, ``IOSAssessor``) must
    implement every :func:`abstractmethod` declared here.  The class also
    provides a small set of concrete helper methods that are shared across
    platforms.

    Args:
        evidence: An :class:`~specter.core.evidence.EvidenceCollector`
            instance used to persist findings and artefacts.
    """

    # ------------------------------------------------------------------
    # Concrete helpers
    # ------------------------------------------------------------------

    def __init__(self, evidence: EvidenceCollector) -> None:
        """Initialise the assessor with an evidence collector.

        Args:
            evidence: Collector responsible for persisting findings and
                raw artefacts gathered during an assessment.
        """
        self._evidence = evidence

    def _record_finding(
        self,
        title: str,
        severity: str,
        category: str,
        description: str,
        evidence_str: str,
        recommendation: str,
        technique: str,
        target: str,
        module: str = "",
        raw_data: dict[str, Any] | None = None,
    ) -> Finding:
        """Create a :class:`Finding`, record evidence, and return it.

        This is the primary helper that concrete assessors should call
        whenever they discover a security-relevant observation.

        Args:
            title: Short human-readable title for the finding.
            severity: Severity level (e.g. ``"critical"``, ``"high"``,
                ``"medium"``, ``"low"``, ``"info"``).
            category: Logical grouping (e.g. ``"device_security"``,
                ``"data_exposure"``, ``"configuration"``).
            description: Detailed prose explaining the finding.
            evidence_str: Supporting evidence such as a command output
                snippet or file contents.
            recommendation: Actionable remediation guidance.
            technique: MITRE ATT&CK technique ID or custom identifier.
            target: The specific device, application, or asset to which
                this finding applies.
            module: Dot-separated module path (e.g. ``"android.security"``).
            raw_data: Optional dictionary of unstructured data to attach
                to the finding for downstream processing.

        Returns:
            The newly created :class:`Finding` instance after it has been
            recorded by the evidence collector.
        """
        from specter.reporting.models import Finding

        finding = Finding(
            id=str(uuid.uuid4()),
            title=title,
            severity=severity,
            category=category,
            description=description,
            evidence=evidence_str,
            recommendation=recommendation,
            technique=technique,
            target=target,
            module=module,
            timestamp=datetime.now(UTC),
            raw_data=raw_data or {},
        )

        # Record raw evidence through the collector for chain-of-custody.
        self._evidence.record(
            operation=technique,
            target=target,
            data=raw_data or {},
            raw_output=evidence_str,
        )

        return finding

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @abstractmethod
    def connect(self, target: str | None = None) -> bool:
        """Establish a connection to a target device.

        Args:
            target: Optional device identifier (serial, UDID, IP, etc.).
                When ``None``, the assessor should attempt to connect to
                the first available device.

        Returns:
            ``True`` if the connection was established successfully.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down the current device connection."""

    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        """Retrieve metadata for the currently connected device.

        Returns:
            A populated :class:`DeviceInfo` instance.

        Raises:
            ConnectionError: If no device is currently connected.
        """

    @abstractmethod
    def list_devices(self) -> list[DeviceInfo]:
        """Enumerate all reachable devices on the host.

        Returns:
            A list of :class:`DeviceInfo` instances, one per discovered
            device.  The list may be empty when no devices are attached.
        """

    @abstractmethod
    def is_connected(self) -> bool:
        """Check whether a device session is active.

        Returns:
            ``True`` if a device is currently connected and responsive.
        """

    # ------------------------------------------------------------------
    # Data extraction
    # ------------------------------------------------------------------

    @abstractmethod
    def extract_contacts(self) -> list[dict[str, Any]]:
        """Extract the device contact list.

        Returns:
            A list of dictionaries, each representing a single contact
            entry with platform-specific keys.
        """

    @abstractmethod
    def extract_sms(self) -> list[dict[str, Any]]:
        """Extract SMS / text message records.

        Returns:
            A list of dictionaries, each representing a single message.
        """

    @abstractmethod
    def extract_call_logs(self) -> list[dict[str, Any]]:
        """Extract call-history records.

        Returns:
            A list of dictionaries, each representing a single call log
            entry.
        """

    @abstractmethod
    def pull_file(self, remote_path: str, local_path: str) -> bool:
        """Copy a file from the device to the local filesystem.

        Args:
            remote_path: Absolute path on the device.
            local_path: Destination path on the local host.

        Returns:
            ``True`` if the file was transferred successfully.
        """

    @abstractmethod
    def take_screenshot(self, output_path: str) -> str:
        """Capture a screenshot and save it locally.

        Args:
            output_path: Destination file path for the screenshot image.

        Returns:
            The absolute path to the saved screenshot file.
        """

    # ------------------------------------------------------------------
    # Security auditing
    # ------------------------------------------------------------------

    @abstractmethod
    def security_audit(self) -> list[Finding]:
        """Run a full security audit against the connected device.

        The audit should aggregate results from specialised checks
        (root/jailbreak detection, permission analysis, etc.).

        Returns:
            A list of :class:`Finding` instances describing every
            security-relevant observation.
        """

    @abstractmethod
    def detect_root_jailbreak(self) -> Finding:
        """Determine whether the device is rooted or jailbroken.

        Returns:
            A :class:`Finding` that describes the detection outcome,
            including severity and supporting evidence.
        """

    @abstractmethod
    def audit_permissions(self) -> list[Finding]:
        """Audit application permissions for over-privilege.

        Returns:
            A list of :class:`Finding` instances, one per permission
            anomaly detected.
        """
