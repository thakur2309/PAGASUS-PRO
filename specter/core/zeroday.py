"""Zero-day detection and real-time notification engine.

Monitors findings in real-time during an assessment. When a finding matches
zero-day indicators (unpatched vulnerability with no known CVE, anomalous
behavior outside known threat patterns, or exploit evidence without a
corresponding advisory), the operator is immediately notified.

Example::

    from specter.core.zeroday import ZeroDayMonitor, NotificationChannel

    monitor = ZeroDayMonitor()
    monitor.add_channel(NotificationChannel.TERMINAL)
    monitor.add_channel(NotificationChannel.WEBHOOK, url="https://hooks.slack.com/...")

    # Called automatically when findings are produced:
    alert = monitor.evaluate(finding)
    if alert:
        print(f"ZERO-DAY ALERT: {alert.title}")
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum, unique
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)

_console = Console(stderr=True)


# ── Known vulnerability baselines ────────────────────────────────────

# Android security patch levels with known critical CVEs.
# Devices below these thresholds are "known vulnerable" (not zero-day).
KNOWN_ANDROID_PATCH_CUTOFFS = {
    "2025-01-01": ["CVE-2024-43767", "CVE-2024-43097"],
    "2025-02-01": ["CVE-2024-53104"],
    "2025-03-01": ["CVE-2025-0090"],
}

# Known dangerous permission combos that are "expected" in certain app categories.
KNOWN_PERMISSION_PATTERNS = {
    "messaging": {"READ_SMS", "SEND_SMS", "READ_CONTACTS", "INTERNET"},
    "navigation": {"ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION", "INTERNET"},
    "camera": {"CAMERA", "RECORD_AUDIO", "WRITE_EXTERNAL_STORAGE"},
}

# Known rootkit / jailbreak artifacts (finding these is NOT zero-day).
KNOWN_ROOT_INDICATORS = {
    "su", "magisk", "supersu", "kingroot", "kingoroot",
    "cydia", "sileo", "unc0ver", "checkra1n", "taurine",
}


@unique
class NotificationType(StrEnum):
    """Classification of the zero-day alert."""
    UNKNOWN_VULN = "unknown_vulnerability"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    NOVEL_EXPLOIT_EVIDENCE = "novel_exploit_evidence"
    UNPATCHED_UNKNOWN = "unpatched_no_cve"
    SUSPICIOUS_BINARY = "suspicious_binary"


@unique
class NotificationChannel(StrEnum):
    """Supported notification delivery channels."""
    TERMINAL = "terminal"
    WEBHOOK = "webhook"
    FILE = "file"
    SOUND = "sound"


@dataclass(frozen=True)
class ZeroDayAlert:
    """Immutable alert record for a potential zero-day finding.

    Attributes:
        id: Alert identifier derived from the finding.
        title: Short description of the potential zero-day.
        notification_type: Classification of the alert.
        severity: Inherited from the triggering finding.
        details: Detailed explanation of why this is flagged.
        raw_evidence: The raw output that triggered detection.
        finding_id: Reference to the originating Finding.
        timestamp: When the alert was generated.
        mitre_technique: Associated MITRE ATT&CK technique.
        confidence: Confidence score (0.0 to 1.0) that this is a real zero-day.
    """
    id: str
    title: str
    notification_type: NotificationType
    severity: str
    details: str
    raw_evidence: str
    finding_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    mitre_technique: str = ""
    confidence: float = 0.0


class ZeroDayMonitor:
    """Real-time zero-day detection engine.

    Evaluates each finding as it's produced during an assessment. Uses
    heuristic analysis to distinguish between known vulnerabilities and
    potential zero-days that warrant immediate operator attention.

    Args:
        alert_log_path: Optional file path to log all alerts as JSONL.
    """

    def __init__(self, alert_log_path: str | None = None) -> None:
        self._channels: dict[NotificationChannel, dict[str, Any]] = {}
        self._alerts: list[ZeroDayAlert] = []
        self._alert_log_path = alert_log_path
        self._lock = threading.Lock()

        # Always enable terminal by default.
        self.add_channel(NotificationChannel.TERMINAL)

    def add_channel(
        self,
        channel: NotificationChannel,
        **config: Any,
    ) -> None:
        """Register a notification channel.

        Args:
            channel: The delivery channel to add.
            **config: Channel-specific configuration. For WEBHOOK, pass
                ``url="https://..."``. For FILE, pass ``path="/tmp/alerts.jsonl"``.
        """
        self._channels[channel] = config
        logger.info("Notification channel added: %s", channel)

    def evaluate(self, finding_data: dict[str, Any]) -> ZeroDayAlert | None:
        """Evaluate a finding for zero-day indicators.

        Called after every finding is produced. Runs heuristic checks
        and returns a ZeroDayAlert if the finding is suspicious.

        Args:
            finding_data: Dictionary with finding fields (title, severity,
                category, technique, evidence, raw_data, target, etc.)

        Returns:
            A ZeroDayAlert if zero-day indicators are detected, None otherwise.
        """
        alert = None

        # Run all detectors — first match wins.
        detectors = [
            self._check_unknown_vulnerability,
            self._check_anomalous_permissions,
            self._check_suspicious_binaries,
            self._check_novel_network_behavior,
            self._check_unpatched_unknown,
        ]

        for detector in detectors:
            alert = detector(finding_data)
            if alert is not None:
                break

        if alert is not None:
            with self._lock:
                self._alerts.append(alert)
            self._dispatch(alert)
            logger.warning("ZERO-DAY ALERT: %s (confidence=%.0f%%)",
                           alert.title, alert.confidence * 100)

        return alert

    @property
    def alerts(self) -> list[ZeroDayAlert]:
        """Return all alerts generated during this session."""
        with self._lock:
            return list(self._alerts)

    # ── Heuristic detectors ──────────────────────────────────────────

    def _check_unknown_vulnerability(
        self, finding: dict[str, Any],
    ) -> ZeroDayAlert | None:
        """Flag findings with CRITICAL/HIGH severity that have no associated CVEs."""
        severity = str(finding.get("severity", "")).lower()
        cve_ids = finding.get("cve_ids", [])
        technique = str(finding.get("technique", ""))

        if severity in ("critical", "high") and not cve_ids:
            raw_data = finding.get("raw_data", {})
            patch_level = raw_data.get("security_patch_level", "")

            # Check if this patch level is in our known database.
            if patch_level and patch_level not in KNOWN_ANDROID_PATCH_CUTOFFS:
                return ZeroDayAlert(
                    id=f"ZD-{finding.get('id', 'unknown')[:8]}",
                    title=f"Potential zero-day: {finding.get('title', 'Unknown')}",
                    notification_type=NotificationType.UNKNOWN_VULN,
                    severity=severity,
                    details=(
                        f"Critical/high severity finding with no CVE mapping. "
                        f"Patch level '{patch_level}' not in known vulnerability database. "
                        f"This may indicate an undisclosed vulnerability."
                    ),
                    raw_evidence=str(finding.get("evidence", ""))[:2000],
                    finding_id=str(finding.get("id", "")),
                    mitre_technique=technique,
                    confidence=0.6,
                )
        return None

    def _check_anomalous_permissions(
        self, finding: dict[str, Any],
    ) -> ZeroDayAlert | None:
        """Flag apps with permission combos that don't match any known pattern."""
        technique = str(finding.get("technique", ""))
        if technique != "permission_audit":
            return None

        raw_data = finding.get("raw_data", {})
        granted_perms = set(raw_data.get("granted_dangerous_permissions", []))
        package = raw_data.get("package", "unknown")

        if not granted_perms or len(granted_perms) < 4:
            return None

        # Check if permissions match ANY known benign pattern.
        matches_known = any(
            pattern.issubset(granted_perms)
            for pattern in KNOWN_PERMISSION_PATTERNS.values()
        )

        # Suspicious: many dangerous permissions that don't match known categories.
        suspicious_combos = {
            "READ_SMS", "CAMERA", "RECORD_AUDIO", "ACCESS_FINE_LOCATION",
            "READ_CONTACTS", "READ_CALL_LOG",
        }
        overlap = granted_perms & suspicious_combos

        if not matches_known and len(overlap) >= 4:
            return ZeroDayAlert(
                id=f"ZD-PERM-{package[:12]}",
                title=f"Anomalous permission set on {package}",
                notification_type=NotificationType.ANOMALOUS_BEHAVIOR,
                severity="high",
                details=(
                    f"App '{package}' has {len(granted_perms)} dangerous permissions "
                    f"including {overlap} which don't match any known legitimate "
                    f"app category. This could indicate spyware or a trojanized app."
                ),
                raw_evidence=str(finding.get("evidence", ""))[:2000],
                finding_id=str(finding.get("id", "")),
                mitre_technique="T1407",
                confidence=0.75,
            )
        return None

    def _check_suspicious_binaries(
        self, finding: dict[str, Any],
    ) -> ZeroDayAlert | None:
        """Flag unknown root/jailbreak binaries not in the known indicator list."""
        technique = str(finding.get("technique", ""))
        if technique not in ("root_detection", "jailbreak_detection"):
            return None

        raw_data = finding.get("raw_data", {})
        indicators_found = raw_data.get("indicators_found", [])

        unknown_indicators = [
            ind for ind in indicators_found
            if ind.lower() not in KNOWN_ROOT_INDICATORS
        ]

        if unknown_indicators:
            return ZeroDayAlert(
                id=f"ZD-BIN-{finding.get('id', 'x')[:8]}",
                title=f"Unknown root/jailbreak artifacts: {', '.join(unknown_indicators[:3])}",
                notification_type=NotificationType.SUSPICIOUS_BINARY,
                severity="critical",
                details=(
                    f"Found root/jailbreak indicators not in known database: "
                    f"{unknown_indicators}. These may be artifacts of a novel "
                    f"exploit or an unknown rootkit/jailbreak tool."
                ),
                raw_evidence=str(finding.get("evidence", ""))[:2000],
                finding_id=str(finding.get("id", "")),
                mitre_technique="T1400",
                confidence=0.8,
            )
        return None

    def _check_novel_network_behavior(
        self, finding: dict[str, Any],
    ) -> ZeroDayAlert | None:
        """Flag suspicious outbound connections to unknown C2-like endpoints."""
        technique = str(finding.get("technique", ""))
        if technique != "network_monitor":
            return None

        raw_data = finding.get("raw_data", {})
        connections = raw_data.get("connections", [])

        suspicious = []
        for conn in connections:
            remote_ip = conn.get("remote_addr", "")
            remote_port = conn.get("remote_port", 0)
            state = conn.get("state", "")

            # Flag: established connections to non-standard high ports
            # from system processes, or to known C2 port ranges.
            if state == "ESTABLISHED" and remote_port not in (
                80, 443, 8080, 8443, 53, 5228, 5229, 5230,  # Google services
            ):
                suspicious.append(f"{remote_ip}:{remote_port}")

        if len(suspicious) >= 2:
            return ZeroDayAlert(
                id=f"ZD-NET-{finding.get('id', 'x')[:8]}",
                title=f"Suspicious outbound connections: {len(suspicious)} non-standard endpoints",
                notification_type=NotificationType.NOVEL_EXPLOIT_EVIDENCE,
                severity="critical",
                details=(
                    f"Device has {len(suspicious)} established connections to "
                    f"non-standard ports: {suspicious[:5]}. This pattern is "
                    f"consistent with C2 beaconing behavior."
                ),
                raw_evidence=str(finding.get("evidence", ""))[:2000],
                finding_id=str(finding.get("id", "")),
                mitre_technique="T1437",
                confidence=0.7,
            )
        return None

    def _check_unpatched_unknown(
        self, finding: dict[str, Any],
    ) -> ZeroDayAlert | None:
        """Flag devices with very old patches that may have undisclosed vulns."""
        technique = str(finding.get("technique", ""))
        if technique != "vulnerability_scan":
            return None

        raw_data = finding.get("raw_data", {})
        patch_level = raw_data.get("security_patch_level", "")
        months_behind = raw_data.get("months_behind", 0)

        if months_behind > 12:
            return ZeroDayAlert(
                id=f"ZD-PATCH-{finding.get('id', 'x')[:8]}",
                title=f"Device {months_behind} months behind on patches",
                notification_type=NotificationType.UNPATCHED_UNKNOWN,
                severity="critical",
                details=(
                    f"Device patch level '{patch_level}' is {months_behind} months "
                    f"behind current. Devices this far behind likely have undisclosed "
                    f"vulnerabilities beyond tracked CVEs. Treat as potentially "
                    f"compromised."
                ),
                raw_evidence=str(finding.get("evidence", ""))[:2000],
                finding_id=str(finding.get("id", "")),
                mitre_technique="T1404",
                confidence=0.65,
            )
        return None

    # ── Notification dispatch ────────────────────────────────────────

    def _dispatch(self, alert: ZeroDayAlert) -> None:
        """Send alert through all registered channels."""
        for channel, config in self._channels.items():
            try:
                if channel == NotificationChannel.TERMINAL:
                    self._notify_terminal(alert)
                elif channel == NotificationChannel.WEBHOOK:
                    self._notify_webhook(alert, config.get("url", ""))
                elif channel == NotificationChannel.FILE:
                    self._notify_file(alert, config.get("path", "zero_day_alerts.jsonl"))
                elif channel == NotificationChannel.SOUND:
                    self._notify_sound()
            except Exception:
                logger.exception("Failed to dispatch alert via %s", channel)

    def _notify_terminal(self, alert: ZeroDayAlert) -> None:
        """Display a prominent Rich panel alert in the terminal."""
        severity_colors = {
            "critical": "bold white on red",
            "high": "bold red",
            "medium": "bold yellow",
            "low": "bold blue",
        }
        style = severity_colors.get(alert.severity, "bold red")

        title_text = Text()
        title_text.append(" ZERO-DAY ALERT ", style="bold white on red")
        title_text.append(f" [{alert.notification_type.value}]", style="bold yellow")

        content = (
            f"[bold]{alert.title}[/bold]\n\n"
            f"[{style}]Severity: {alert.severity.upper()}[/{style}]\n"
            f"Confidence: {alert.confidence:.0%}\n"
            f"MITRE: {alert.mitre_technique or 'N/A'}\n\n"
            f"{alert.details}\n\n"
            f"[dim]Finding ID: {alert.finding_id}[/dim]\n"
            f"[dim]Alert ID: {alert.id}[/dim]\n"
            f"[dim]Time: {alert.timestamp.isoformat()}[/dim]"
        )

        _console.print()
        _console.print(Panel(
            content,
            title=str(title_text),
            border_style="red",
            padding=(1, 2),
        ))
        _console.print()

    def _notify_webhook(self, alert: ZeroDayAlert, url: str) -> None:
        """POST alert as JSON to a webhook URL (Slack, Teams, etc.)."""
        if not url:
            return

        payload = {
            "text": (
                f":rotating_light: *ZERO-DAY ALERT*\n"
                f"*{alert.title}*\n"
                f"Severity: {alert.severity.upper()} | "
                f"Confidence: {alert.confidence:.0%}\n"
                f"MITRE: {alert.mitre_technique}\n"
                f"{alert.details}"
            ),
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        # Fire and forget — don't block the assessment.
        def _send() -> None:
            try:
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                logger.exception("Webhook delivery failed: %s", url)

        threading.Thread(target=_send, daemon=True).start()

    def _notify_file(self, alert: ZeroDayAlert, path: str) -> None:
        """Append alert as a JSON line to a log file."""
        record = {
            "id": alert.id,
            "title": alert.title,
            "type": alert.notification_type.value,
            "severity": alert.severity,
            "confidence": alert.confidence,
            "details": alert.details,
            "finding_id": alert.finding_id,
            "mitre_technique": alert.mitre_technique,
            "timestamp": alert.timestamp.isoformat(),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _notify_sound(self) -> None:
        """Emit a terminal bell character to trigger system alert sound."""
        _console.print("\a", end="")
