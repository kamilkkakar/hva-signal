"""Server-side loader for LIVE-I retry/timeout budgets.

Workers import this module — never a client request — to obtain the operator
budget. Does not call vendors. Does not read client payloads as budget source.
"""

from __future__ import annotations

from app.domain.retry_timeout_policy import (
    PolicyContext,
    PolicyDecision,
    RetryTimeoutBudget,
    decide_retry_timeout,
    default_retry_timeout_budget,
    operator_budget_from_environ,
    reject_client_retry_controls,
)


def server_retry_timeout_budget() -> RetryTimeoutBudget:
    """Operator/server budget only. Client bodies never reach this function."""
    return operator_budget_from_environ()


def evaluate_retry_timeout(
    ctx: PolicyContext,
    budget: RetryTimeoutBudget | None = None,
) -> PolicyDecision:
    """Evaluate policy with the server budget unless a test injects one."""
    return decide_retry_timeout(ctx, budget or server_retry_timeout_budget())


__all__ = [
    "PolicyContext",
    "PolicyDecision",
    "RetryTimeoutBudget",
    "decide_retry_timeout",
    "default_retry_timeout_budget",
    "evaluate_retry_timeout",
    "operator_budget_from_environ",
    "reject_client_retry_controls",
    "server_retry_timeout_budget",
]
