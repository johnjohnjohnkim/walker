from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

# (west, south, east, north) in degrees.
BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class Place:
    name: str
    # Where it is, for telling apart places with the same name: "290 Bremner
    # Boulevard, Toronto".
    address: str
    lon: float
    lat: float

    def to_json(self) -> dict:
        return asdict(self)


class GeocoderUnavailable(RuntimeError):
    """The provider could not be reached or returned something unusable."""


class Geocoder(Protocol):
    def search(self, query: str, *, bbox: BBox, limit: int) -> list[Place]:
        """Places matching `query` inside `bbox`, best first."""
        ...
