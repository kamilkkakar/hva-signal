"""Read-only observed-instant assembler. Tracked fixtures only.

Does not call FortyGuard. Does not read workforce/. Does not compute q_A.
"""

from __future__ import annotations

from app.domain.observed_thermal_instants import (
    ObservedThermalSequence,
    assemble_observed_thermal_sequence,
)


def load_observed_thermal_sequence(
    geoid: str, *, area_id: str = "phoenix-demo"
) -> ObservedThermalSequence:
    return assemble_observed_thermal_sequence(geoid, area_id=area_id)
