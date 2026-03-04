"""Evidence collection and integrity verification.

Every significant action in a Specter engagement produces an
:class:`EvidenceRecord`.  The :class:`EvidenceCollector` writes raw output to
disk and maintains an append-only chain of custody so that post-engagement
reports can demonstrate exactly what happened and when.

SHA-256 hashes are computed over the raw output at collection time and stored
alongside the record so that tampering can be detected later.

Example::

    from pathlib import Path
    from specter.core.evidence import EvidenceCollector

    collector = EvidenceCollector(evidence_dir=Path("/tmp/evidence"))
    record = collector.record(
        operation="nmap_scan",
        target="192.168.1.1",
        data={"ports": [22, 80, 443]},
        raw_output="Starting Nmap 7.94 ...",
    )
    print(record.sha256_hash)
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from specter.core.exceptions import EvidenceIntegrityError

logger = logging.getLogger(__name__)


class EvidenceRecord(BaseModel):
    """Immutable record of a single evidence artifact.

    Attributes:
        id: Unique identifier for this evidence record.
        operation: Name of the operation that generated this evidence
            (e.g. ``"nmap_scan"``, ``"adb_shell"``).
        target: The target that was acted upon (IP, serial, etc.).
        timestamp: UTC timestamp when the evidence was collected.
        sha256_hash: Hex-encoded SHA-256 digest of the raw output.
        evidence_file: Absolute path to the raw-output file on disk.
        summary: Structured summary data captured at collection time.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operation: str
    target: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sha256_hash: str
    evidence_file: Path
    summary: dict = Field(default_factory=dict)

    model_config = {"frozen": True}


class EvidenceCollector:
    """Append-only collector that writes raw evidence to disk and tracks integrity.

    Args:
        evidence_dir: Directory where raw evidence files will be stored.
            Created automatically if it does not exist.
    """

    def __init__(self, evidence_dir: Path) -> None:
        self.evidence_dir = evidence_dir
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self._chain: list[EvidenceRecord] = []
        logger.debug("EvidenceCollector initialised at %s", self.evidence_dir)

    # ── public API ────────────────────────────────────────────────────

    def record(
        self,
        operation: str,
        target: str,
        data: dict,
        raw_output: str,
    ) -> EvidenceRecord:
        """Persist a raw evidence artifact and return its record.

        The method performs three steps:

        1. Compute the SHA-256 hash of *raw_output*.
        2. Write *raw_output* to a uniquely-named file inside *evidence_dir*.
        3. Append an :class:`EvidenceRecord` to the internal chain of custody.

        Args:
            operation: Identifier for the tool / action that produced the
                output (e.g. ``"nmap_scan"``).
            target: The target that was acted upon.
            data: Structured summary dictionary to attach to the record.
            raw_output: The verbatim output string to persist on disk.

        Returns:
            The newly created :class:`EvidenceRecord`.
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC)
        sha256_hash = self._compute_hash(raw_output)

        # Build a filename that sorts chronologically and is globally unique.
        ts_slug = timestamp.strftime("%Y%m%dT%H%M%S")
        filename = f"{ts_slug}_{operation}_{record_id[:8]}.raw"
        evidence_file = self.evidence_dir / filename

        evidence_file.write_text(raw_output, encoding="utf-8")
        logger.info(
            "Evidence written: %s (%d bytes, sha256=%s)",
            evidence_file.name,
            len(raw_output),
            sha256_hash[:16] + "...",
        )

        evidence_record = EvidenceRecord(
            id=record_id,
            operation=operation,
            target=target,
            timestamp=timestamp,
            sha256_hash=sha256_hash,
            evidence_file=evidence_file.resolve(),
            summary=data,
        )
        self._chain.append(evidence_record)
        return evidence_record

    def chain_of_custody(self) -> list[EvidenceRecord]:
        """Return the full chain of custody ordered by collection time.

        Returns:
            A list of :class:`EvidenceRecord` instances sorted by their
            ``timestamp`` field in ascending order.
        """
        return sorted(self._chain, key=lambda r: r.timestamp)

    def verify(self, evidence_record: EvidenceRecord) -> bool:
        """Re-compute the hash of the on-disk artifact and compare.

        Args:
            evidence_record: The record to verify.

        Returns:
            ``True`` if the hash matches.

        Raises:
            EvidenceIntegrityError: When the on-disk content no longer matches
                the originally recorded hash.
            FileNotFoundError: When the evidence file is missing.
        """
        content = evidence_record.evidence_file.read_text(encoding="utf-8")
        actual = self._compute_hash(content)
        if actual != evidence_record.sha256_hash:
            raise EvidenceIntegrityError(
                evidence_file=str(evidence_record.evidence_file),
                expected=evidence_record.sha256_hash,
                actual=actual,
            )
        return True

    def export_chain(self, output_path: Path) -> Path:
        """Serialize the full chain of custody to a JSON file.

        Args:
            output_path: Destination file path for the JSON export.

        Returns:
            The resolved path that was written.
        """
        chain = self.chain_of_custody()
        payload = [
            {
                "id": r.id,
                "operation": r.operation,
                "target": r.target,
                "timestamp": r.timestamp.isoformat(),
                "sha256_hash": r.sha256_hash,
                "evidence_file": str(r.evidence_file),
                "summary": r.summary,
            }
            for r in chain
        ]
        output_path.write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Chain of custody exported to %s (%d records)", output_path, len(payload))
        return output_path.resolve()

    # ── internals ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Return the hex-encoded SHA-256 digest of *content*.

        Args:
            content: The string to hash (encoded as UTF-8).

        Returns:
            Lowercase hex digest string.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
