"""Operational context for a Specter engagement.

Every penetration-testing session is wrapped in an :class:`OperationContext`
that captures *who* is operating, *what* is authorised, and *when* the session
began.  The context travels through the call stack so that scope checks,
evidence collection, and audit logging always have access to authoritative
metadata.

Example::

    from specter.core.context import OperationContext

    ctx = OperationContext(
        operator="analyst@redteam.local",
        target_description="ACME Corp internal pentest",
        authorization_reference="SOW-2024-001",
        scope=["192.168.1.0/24", "DEVICE-ABC123"],
    )
    assert ctx.is_target_in_scope("192.168.1.42")
"""

from __future__ import annotations

import ipaddress
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from specter.core.exceptions import AuthorizationRequired, ScopeViolation

console = Console(stderr=True)


@dataclass
class OperationContext:
    """Metadata envelope for a single engagement session.

    Attributes:
        operation_id: Unique identifier for this operation (auto-generated).
        operator: Identity of the human operator (email, username, etc.).
        target_description: Free-text summary of the engagement target.
        authorization_reference: Reference to the Statement of Work, contract,
            or other authorizing document (e.g. ``"SOW-2024-001"``).
        scope: List of authorized targets — IP addresses, CIDR ranges, device
            serial numbers, or hostnames.
        started_at: UTC timestamp when the operation began.
        evidence_path: Optional filesystem path where evidence artifacts for
            this operation should be stored.
    """

    operator: str
    target_description: str
    authorization_reference: str
    scope: list[str] = field(default_factory=list)
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    evidence_path: Path | None = None

    # ── scope helpers ─────────────────────────────────────────────────

    def is_target_in_scope(self, target: str) -> bool:
        """Check whether *target* falls within the authorized scope.

        The method supports three matching strategies applied in order:

        1. **Exact match** — the target string equals a scope entry verbatim
           (case-insensitive).
        2. **CIDR containment** — if *target* parses as an IP address and a
           scope entry parses as a network, the address is checked for
           membership.
        3. **IP-to-IP** — both *target* and a scope entry parse as individual
           IP addresses and are numerically equal.

        Args:
            target: The IP address, hostname, device serial, or other
                identifier to validate.

        Returns:
            ``True`` if *target* is authorized, ``False`` otherwise.
        """
        target_lower = target.strip().lower()

        for entry in self.scope:
            entry_lower = entry.strip().lower()

            # 1. Exact / case-insensitive match (serial numbers, hostnames).
            if target_lower == entry_lower:
                return True

            # 2. CIDR containment.
            try:
                target_ip = ipaddress.ip_address(target_lower)
                network = ipaddress.ip_network(entry_lower, strict=False)
                if target_ip in network:
                    return True
            except ValueError:
                pass

            # 3. IP-to-IP equality (covers mixed v4/v6 string formats).
            try:
                if ipaddress.ip_address(target_lower) == ipaddress.ip_address(entry_lower):
                    return True
            except ValueError:
                pass

        return False

    def assert_in_scope(self, target: str) -> None:
        """Raise :class:`ScopeViolation` if *target* is not in scope.

        This is the *strict* counterpart of :meth:`is_target_in_scope` — use
        it at gate-check points where out-of-scope targets must abort the
        operation.

        Args:
            target: Identifier to validate.

        Raises:
            ScopeViolation: When *target* is not contained in the scope list.
        """
        if not self.is_target_in_scope(target):
            raise ScopeViolation(target, self.scope)

    # ── authorization prompt ──────────────────────────────────────────

    def require_authorization(self, action: str | None = None) -> None:
        """Prompt the operator to confirm they are authorized to proceed.

        Uses a :pypi:`rich` interactive prompt on *stderr* so that it works
        even when *stdout* is being piped.

        Args:
            action: Optional description of the specific action requiring
                confirmation.  When omitted a generic confirmation is shown.

        Raises:
            AuthorizationRequired: If the operator declines.
        """
        action_desc = action or f"operation {self.operation_id}"
        console.print(
            f"\n[bold yellow]AUTHORIZATION CHECK[/bold yellow]\n"
            f"  Operator   : {self.operator}\n"
            f"  Operation  : {self.operation_id}\n"
            f"  Auth Ref   : {self.authorization_reference}\n"
            f"  Action     : {action_desc}\n"
        )
        confirmed = Confirm.ask(
            "[bold]Do you confirm you are authorized to proceed?[/bold]",
            default=False,
            console=console,
        )
        if not confirmed:
            raise AuthorizationRequired(action_desc)
