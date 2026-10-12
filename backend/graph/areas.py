"""Named map areas the graph can be built for.

Each box is (west, south, east, north) in degrees, the order OSMnx expects.
"""

from typing import NamedTuple


class Area(NamedTuple):
    name: str
    description: str
    bbox: tuple[float, float, float, float]


AREAS: dict[str, Area] = {
    "downtown": Area(
        name="downtown",
        description="Downtown Toronto: Bathurst St to the Don River, the waterfront to Bloor St.",
        bbox=(-79.4120, 43.6330, -79.3470, 43.6720),
    ),
}
