"""Lead stitch: public name for I3's ALG1 entry.

I8 and the program contract look for ``resolve_place_geography`` at this module
path. Implementation stays in ``place_geography_resolver``.
"""

from app.services.place_geography_resolver import (
    PlaceGeographyOutcome,
    PlaceGeographySuccess,
    PlaceGeographyUnsupported,
    resolve_place_geography,
)

__all__ = [
    "PlaceGeographyOutcome",
    "PlaceGeographySuccess",
    "PlaceGeographyUnsupported",
    "resolve_place_geography",
]
