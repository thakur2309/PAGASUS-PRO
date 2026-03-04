"""Pydantic v2 models for Specter assessment reporting.

Defines the data structures used to capture, validate, and organize
findings produced during authorized offensive security assessments.
Every finding carries cryptographic evidence integrity via SHA-256
hashing so that raw tool/command output can be verified after the fact.
"""

from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum, unique

from pydantic import BaseModel, Field


@unique
class Severity(StrEnum):
    """Qualitative severity rating aligned with CVSS v3 categories.

    Values are ordered from most to least severe so that sorting
    a list of findings by ``Severity`` produces a natural priority order.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@unique
class FindingCategory(StrEnum):
    """High-level classification bucket for a finding.

    Categories map to the top-level domains evaluated during a typical
    mobile / IoT / network penetration test.
    """

    DEVICE_SECURITY = "device_security"
    DATA_EXPOSURE = "data_exposure"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONFIGURATION = "configuration"
    VULNERABILITY = "vulnerability"
    COMPLIANCE = "compliance"


# ---------------------------------------------------------------------------
# Core finding model
# ---------------------------------------------------------------------------


class Finding(BaseModel):
    """A single security finding produced by an assessment module.

    Attributes:
        id: Unique identifier (UUID v4) for this finding.
        title: Short human-readable title.
        severity: Qualitative severity rating.
        category: High-level classification bucket.
        description: Detailed narrative explaining the finding.
        evidence: Raw command or tool output that proves the finding.
        evidence_hash: SHA-256 hex digest of ``evidence`` for integrity
            verification.
        recommendation: Actionable remediation guidance.
        target: Identifier for the assessed asset (device serial, IP, etc.).
        module: Dot-separated module path that produced the finding
            (e.g. ``"android.security"``).
        technique: Specific technique name (e.g. ``"root_detection"``).
        timestamp: UTC timestamp of when the finding was recorded.
        cvss_score: Optional CVSS v3 base score (0.0 -- 10.0).
        cve_ids: Associated CVE identifiers, if any.
        raw_data: Structured parsed data extracted from the evidence.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    severity: Severity
    category: FindingCategory
    description: str
    evidence: str
    evidence_hash: str = ""
    recommendation: str
    target: str
    module: str
    technique: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    cvss_score: float | None = None
    cve_ids: list[str] = Field(default_factory=list)
    raw_data: dict[str, object] = Field(default_factory=dict)

    def model_post_init(self, __context: object) -> None:
        """Automatically compute the evidence hash after initialization."""
        if not self.evidence_hash:
            self.evidence_hash = self.compute_evidence_hash()

    def compute_evidence_hash(self) -> str:
        """Return the SHA-256 hex digest of ``self.evidence``.

        Returns:
            A lowercase hex string representing the SHA-256 hash of the
            evidence field encoded as UTF-8.
        """
        return hashlib.sha256(self.evidence.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Attack chain models
# ---------------------------------------------------------------------------


class AttackChainStep(BaseModel):
    """One discrete step within a multi-stage attack chain.

    Attributes:
        step_number: Ordinal position of this step in the chain (1-based).
        finding_id: UUID reference to the :class:`Finding` that supports
            this step.
        action: Plain-language description of what the attacker does at
            this stage.
        success_probability: Estimated likelihood of success (0.0 -- 1.0).
        prerequisites: Finding IDs that must succeed before this step
            can be attempted.
        defensive_control: Description of the defensive measure that
            would block or detect this step.
    """

    step_number: int
    finding_id: str
    action: str
    success_probability: float = Field(ge=0.0, le=1.0)
    prerequisites: list[str] = Field(default_factory=list)
    defensive_control: str


class AttackChain(BaseModel):
    """An ordered sequence of steps modelling a realistic attack path.

    Attributes:
        id: Unique identifier (UUID v4) for this chain.
        title: Short human-readable title.
        description: Narrative explaining the overall attack scenario.
        steps: Ordered list of :class:`AttackChainStep` instances.
        total_risk_score: Aggregate risk score for the entire chain.
        estimated_impact: Plain-language summary of worst-case impact if
            the chain is successfully executed.
        target_description: Description of the asset(s) targeted by
            this chain.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    steps: list[AttackChainStep]
    total_risk_score: float
    estimated_impact: str
    target_description: str


# ---------------------------------------------------------------------------
# Top-level assessment report
# ---------------------------------------------------------------------------


class AssessmentReport(BaseModel):
    """Complete report for an authorized offensive security assessment.

    Attributes:
        id: Unique identifier (UUID v4) for this report.
        title: Report title (e.g. ``"Q1 2026 Mobile Pentest"``).
        operator: Name or handle of the operator who conducted the
            assessment.
        target_description: Description of the target environment.
        authorization_reference: Reference to the authorization document
            (e.g. rules-of-engagement ID, SOW number).
        scope: List of in-scope targets / networks / applications.
        started_at: UTC timestamp of when the assessment began.
        completed_at: UTC timestamp of when the assessment ended, or
            ``None`` if still in progress.
        findings: All findings produced during the assessment.
        attack_chains: Modelled attack paths built from findings.
        executive_summary: AI-generated (or manually written) high-level
            summary intended for non-technical stakeholders.
        risk_score: Overall risk score for the assessed environment.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    operator: str
    target_description: str
    authorization_reference: str
    scope: list[str]
    started_at: datetime
    completed_at: datetime | None = None
    findings: list[Finding] = Field(default_factory=list)
    attack_chains: list[AttackChain] = Field(default_factory=list)
    executive_summary: str = ""
    risk_score: float = 0.0

    def findings_by_severity(self) -> dict[Severity, list[Finding]]:
        """Group findings by their severity level.

        Returns:
            A mapping from each :class:`Severity` value to the list of
            findings that carry that severity.  Severities with zero
            findings are included as empty lists.
        """
        grouped: dict[Severity, list[Finding]] = defaultdict(list)
        for finding in self.findings:
            grouped[finding.severity].append(finding)
        # Ensure every severity key is present even if it has no findings.
        for severity in Severity:
            grouped.setdefault(severity, [])
        return dict(grouped)

    def critical_findings(self) -> list[Finding]:
        """Return only findings rated as :attr:`Severity.CRITICAL`.

        Returns:
            A list of critical-severity findings, which may be empty.
        """
        return [f for f in self.findings if f.severity == Severity.CRITICAL]

    def finding_count_by_category(self) -> dict[FindingCategory, int]:
        """Count findings in each category.

        Returns:
            A mapping from each :class:`FindingCategory` to the number
            of findings in that category.  Categories with zero findings
            are included with a count of ``0``.
        """
        counts: dict[FindingCategory, int] = {cat: 0 for cat in FindingCategory}
        for finding in self.findings:
            counts[finding.category] += 1
        return counts

    def complete(self, summary: str = "") -> None:
        """Mark the assessment as complete.

        Sets :attr:`completed_at` to the current UTC time and optionally
        stores an executive summary.

        Args:
            summary: Optional executive summary text.  If provided, it
                replaces any existing value in :attr:`executive_summary`.
        """
        self.completed_at = datetime.now(UTC)
        if summary:
            self.executive_summary = summary
