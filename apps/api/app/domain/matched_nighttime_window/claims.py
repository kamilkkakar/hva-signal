"""Claim gates for matched-window nighttime TCM evidence.

This package is not Signal A. It does not emit q_A, climate trends,
health impact, or an intervention effect.
"""

from __future__ import annotations

from collections.abc import Iterable

WINDOW_LABEL = "MATCHED SUMMER NIGHTTIME WINDOW"
WINDOW_DATES = "30 Jun–30 Jul"
HOUR_LOCAL = "03:00"
TIMEZONE = "America/Phoenix"
TEMPERATURE_QUANTITY = "tcm_zone_mean"
SOURCE_FAMILY = "fortyguard"
SOURCE_MODE = "replay"
CONTRACT_ID = "hva-signal-matched-summer-nighttime-window-v1"
N_EXPECTED_NIGHTS = 31
REFERENCE_YEARS = (2022, 2023, 2024)

FORBIDDEN_CLAIM_TOKENS: tuple[str, ...] = (
    "summer trend",
    "climate trend",
    "annual trend",
    "heatdose",
    "afterheat",
    "recovery",
    "probability",
    "health impact",
    "heat impact",
    "climate impact",
    "persistence index",
    "intervention effect",
    "intervention impact",
    "health danger",
    "heat danger",
    "full summer",
    "jja",
)

AUTHORIZED_DENIAL_SUBSTRINGS: tuple[str, ...] = (
    "not a climate trend",
    "not an annual trend",
    "not a summer trend",
    "not heatdose",
    "not afterheat",
    "not recovery",
    "not a probability",
    "not a health impact",
    "not an intervention effect",
    "not a persistence index",
    "not jja",
    "not full summer",
    "not signal a",
    "does not compute q_a",
)


class ForbiddenClaimError(ValueError):
    """A sentence uses a forbidden longitudinal claim token."""


def normalize_claim_text(text: str) -> str:
    return " ".join(text.lower().split())


def claim_violations(text: str) -> list[str]:
    remainder = normalize_claim_text(text)
    for denial in sorted(AUTHORIZED_DENIAL_SUBSTRINGS, key=len, reverse=True):
        remainder = remainder.replace(denial, " ")
    remainder = " ".join(remainder.split())
    return [token for token in FORBIDDEN_CLAIM_TOKENS if token in remainder]


def assert_claim_allowed(text: str) -> str:
    hits = claim_violations(text)
    if hits:
        raise ForbiddenClaimError(
            f"forbidden matched-window claim tokens {hits} in {text!r}"
        )
    return text


def assert_no_forbidden_tokens(texts: Iterable[str]) -> None:
    for text in texts:
        assert_claim_allowed(text)


def window_period_clause() -> str:
    return (
        f"{WINDOW_LABEL} ({WINDOW_DATES}, {HOUR_LOCAL} {TIMEZONE})"
    )
