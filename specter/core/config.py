"""Specter application configuration backed by Pydantic Settings.

Configuration values are loaded from environment variables with the prefix
``SPECTER_`` (e.g. ``SPECTER_LOG_LEVEL=DEBUG``) and can also be set
programmatically.

Example::

    from specter.core.config import SpecterConfig

    cfg = SpecterConfig(log_level="DEBUG")
    cfg.ensure_dirs()
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class SpecterConfig(BaseSettings):
    """Central configuration for the Specter platform.

    Attributes:
        app_name: Display name of the application.
        version: Current semantic version string.
        data_dir: Root directory for all persistent Specter data.
        evidence_dir: Directory where evidence artifacts are stored.
        report_dir: Directory where generated reports are stored.
        db_url: SQLAlchemy-compatible database URL.  When the URL contains a
            relative ``sqlite:///`` path it is resolved relative to *data_dir*.
        log_level: Python logging level name (``DEBUG``, ``INFO``, etc.).
        adb_path: Filesystem path (or bare command name) for the Android Debug
            Bridge binary.
        nmap_path: Filesystem path (or bare command name) for the Nmap scanner.
        require_scope_confirmation: When ``True``, the operator must confirm
            every target against the authorized scope before execution.
        authorized_targets: IP addresses, CIDR ranges, device serials, or
            hostnames that the current engagement is authorized to test.
    """

    model_config = SettingsConfigDict(
        env_prefix="SPECTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── identity ──────────────────────────────────────────────────────
    app_name: str = "Specter"
    version: str = "2.0.0a1"

    # ── paths ─────────────────────────────────────────────────────────
    data_dir: Path = Path.home() / ".specter"
    evidence_dir: Path | None = None
    report_dir: Path | None = None

    # ── database ──────────────────────────────────────────────────────
    db_url: str = "sqlite:///specter.db"

    # ── logging ───────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── external tools ────────────────────────────────────────────────
    adb_path: str = "adb"
    nmap_path: str = "nmap"

    # ── scope & authorization ─────────────────────────────────────────
    require_scope_confirmation: bool = True
    authorized_targets: list[str] = []

    # ── validators ────────────────────────────────────────────────────

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        """Ensure *log_level* is a recognised Python logging level name.

        Args:
            value: The raw log-level string provided by the caller / env.

        Returns:
            The uppercased, validated level name.

        Raises:
            ValueError: If the string does not map to a known level.
        """
        normalized = value.upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in valid_levels:
            msg = f"Invalid log_level {value!r}. Must be one of {valid_levels}"
            raise ValueError(msg)
        return normalized

    @model_validator(mode="after")
    def _resolve_paths(self) -> "SpecterConfig":
        """Derive evidence_dir/report_dir from data_dir and resolve sqlite path.

        Returns:
            The config instance with resolved paths.
        """
        if self.evidence_dir is None:
            self.evidence_dir = self.data_dir / "evidence"
        if self.report_dir is None:
            self.report_dir = self.data_dir / "reports"

        prefix = "sqlite:///"
        if self.db_url.startswith(prefix):
            relative_part = self.db_url[len(prefix):]
            db_path = Path(relative_part)
            if not db_path.is_absolute():
                resolved = self.data_dir / relative_part
                self.db_url = f"{prefix}{resolved}"
        return self

    # ── helpers ───────────────────────────────────────────────────────

    def ensure_dirs(self) -> None:
        """Create *data_dir*, *evidence_dir*, and *report_dir* if they do not exist.

        Directories are created with ``parents=True`` so intermediate path
        components are also created.
        """
        for directory in (self.data_dir, self.evidence_dir, self.report_dir):
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug("Ensured directory exists: %s", directory)

    @property
    def resolved_db_path(self) -> Path | None:
        """Return the resolved SQLite file path, or ``None`` for non-SQLite URLs.

        Returns:
            A :class:`~pathlib.Path` pointing to the database file when
            using SQLite, otherwise ``None``.
        """
        prefix = "sqlite:///"
        if self.db_url.startswith(prefix):
            return Path(self.db_url[len(prefix):])
        return None
