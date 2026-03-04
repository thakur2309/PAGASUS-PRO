"""Scope enforcement and authorization decorators.

This module provides two decorators and a management class that together
ensure every offensive action is validated against the authorized engagement
scope before execution.

* :func:`require_scope` — aborts the decorated function when the target
  argument falls outside the :class:`~specter.core.context.OperationContext`
  scope.
* :func:`require_approval` — prompts the operator for interactive
  confirmation via a Rich console before the decorated function runs.
* :class:`ScopeEnforcer` — stateful manager that wraps an
  :class:`~specter.core.context.OperationContext` and exposes a convenient
  validation API.

Example::

    from specter.core.authorization import require_scope, require_approval
    from specter.core.context import OperationContext

    @require_scope(target_param="target")
    def scan_host(target: str, *, ctx: OperationContext) -> dict:
        ...

    @require_approval(action="Launch exploit against target")
    def run_exploit(target: str, *, ctx: OperationContext) -> dict:
        ...
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from rich.console import Console
from rich.prompt import Confirm

from specter.core.context import OperationContext
from specter.core.exceptions import AuthorizationRequired, ScopeViolation

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

_console = Console(stderr=True)


# ── decorators ────────────────────────────────────────────────────────


def require_scope(target_param: str = "target") -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that validates the target against the operation scope.

    The decorated function **must** receive an ``OperationContext`` as either a
    keyword argument named ``ctx`` or as the first positional argument after
    ``self`` (for methods).

    Args:
        target_param: Name of the parameter that contains the target
            identifier to validate.  Defaults to ``"target"``.

    Returns:
        A decorator that wraps the original function with a scope check.

    Raises:
        ScopeViolation: If the resolved target is not in scope.
        TypeError: If the ``ctx`` or *target_param* cannot be resolved from
            the call arguments.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments = bound.arguments

            # Resolve OperationContext.
            ctx = _resolve_argument(arguments, "ctx", OperationContext)

            # Resolve target string.
            target = arguments.get(target_param)
            if target is None:
                msg = (
                    f"@require_scope: parameter {target_param!r} not found in "
                    f"call to {fn.__qualname__}()"
                )
                raise TypeError(msg)

            logger.debug(
                "Scope check: target=%r against scope=%r",
                target,
                ctx.scope,
            )

            if not ctx.is_target_in_scope(str(target)):
                raise ScopeViolation(str(target), ctx.scope)

            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def require_approval(action: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that prompts the operator for confirmation before execution.

    Uses a Rich interactive prompt on *stderr*.

    Args:
        action: Human-readable description of the action requiring approval
            (shown in the prompt).

    Returns:
        A decorator that wraps the original function with an approval gate.

    Raises:
        AuthorizationRequired: If the operator declines.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments = bound.arguments

            # Try to get context for display, but don't fail if absent.
            ctx: OperationContext | None = None
            try:
                ctx = _resolve_argument(arguments, "ctx", OperationContext)
            except TypeError:
                pass

            _console.print(
                f"\n[bold yellow]APPROVAL REQUIRED[/bold yellow]\n"
                f"  Action : {action}\n"
                f"  Function : {fn.__qualname__}\n"
                + (
                    f"  Operator : {ctx.operator}\n"
                    f"  Auth Ref : {ctx.authorization_reference}\n"
                    if ctx
                    else ""
                )
            )

            confirmed = Confirm.ask(
                "[bold]Do you approve this action?[/bold]",
                default=False,
                console=_console,
            )
            if not confirmed:
                logger.warning("Operator declined approval for: %s", action)
                raise AuthorizationRequired(action)

            logger.info("Operator approved: %s", action)
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


# ── ScopeEnforcer ─────────────────────────────────────────────────────


class ScopeEnforcer:
    """Stateful scope manager wrapping an :class:`OperationContext`.

    Provides a convenient, object-oriented API for validating targets and
    managing the authorised scope at runtime.

    Args:
        ctx: The operation context whose scope will be enforced.
    """

    def __init__(self, ctx: OperationContext) -> None:
        self._ctx = ctx
        logger.debug(
            "ScopeEnforcer initialised with %d scope entries",
            len(ctx.scope),
        )

    # ── properties ────────────────────────────────────────────────────

    @property
    def context(self) -> OperationContext:
        """Return the underlying :class:`OperationContext`.

        Returns:
            The operation context this enforcer was created with.
        """
        return self._ctx

    @property
    def scope(self) -> list[str]:
        """Return a copy of the current authorized-target list.

        Returns:
            A new list containing the scope entries.
        """
        return list(self._ctx.scope)

    # ── validation ────────────────────────────────────────────────────

    def is_allowed(self, target: str) -> bool:
        """Check whether *target* is within the authorized scope.

        Args:
            target: The identifier to validate.

        Returns:
            ``True`` if the target is in scope, ``False`` otherwise.
        """
        return self._ctx.is_target_in_scope(target)

    def validate(self, target: str) -> None:
        """Assert that *target* is in scope; raise on failure.

        Args:
            target: The identifier to validate.

        Raises:
            ScopeViolation: When *target* is not authorized.
        """
        self._ctx.assert_in_scope(target)

    def validate_many(self, targets: list[str]) -> list[str]:
        """Validate multiple targets and return the list of violations.

        Unlike :meth:`validate`, this method does **not** raise an exception.
        It returns all targets that failed the scope check so the caller can
        report them in bulk.

        Args:
            targets: Identifiers to validate.

        Returns:
            A list of targets that are **not** in scope.  An empty list means
            all targets passed.
        """
        return [t for t in targets if not self._ctx.is_target_in_scope(t)]

    # ── scope mutation ────────────────────────────────────────────────

    def add_target(self, target: str) -> None:
        """Append *target* to the authorized scope.

        No-op if the target is already present (case-insensitive comparison).

        Args:
            target: New target entry to authorize.
        """
        normalised = target.strip().lower()
        existing = {s.strip().lower() for s in self._ctx.scope}
        if normalised not in existing:
            self._ctx.scope.append(target.strip())
            logger.info("Target added to scope: %s", target)

    def remove_target(self, target: str) -> bool:
        """Remove *target* from the authorized scope.

        Args:
            target: The entry to remove (case-insensitive match).

        Returns:
            ``True`` if the target was found and removed, ``False`` if it was
            not present.
        """
        normalised = target.strip().lower()
        for i, entry in enumerate(self._ctx.scope):
            if entry.strip().lower() == normalised:
                self._ctx.scope.pop(i)
                logger.info("Target removed from scope: %s", target)
                return True
        return False


# ── internal helpers ──────────────────────────────────────────────────


def _resolve_argument(arguments: dict[str, Any], name: str, expected_type: type) -> Any:
    """Look up *name* in bound call arguments and verify its type.

    Args:
        arguments: Mapping produced by ``Signature.bind().arguments``.
        name: Parameter name to look for.
        expected_type: The type the resolved value must be an instance of.

    Returns:
        The resolved argument value.

    Raises:
        TypeError: When the argument is missing or has the wrong type.
    """
    value = arguments.get(name)
    if value is None:
        # Also check for the value buried inside **kwargs.
        for v in arguments.values():
            if isinstance(v, dict):
                value = v.get(name)
                if value is not None:
                    break
            if isinstance(v, expected_type):
                value = v
                break

    if value is None:
        msg = f"Required argument {name!r} ({expected_type.__name__}) not found in call arguments"
        raise TypeError(msg)

    if not isinstance(value, expected_type):
        msg = (
            f"Argument {name!r} must be {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )
        raise TypeError(msg)

    return value
