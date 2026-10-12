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
    "central": Area(
        name="central",
        description="Central Toronto: the Humber River to Victoria Park Ave, the lake to Lawrence Ave.",
        bbox=(-79.4900, 43.6200, -79.2900, 43.7300),
    ),
    "toronto": Area(
        name="toronto",
        description=(
            "A box around all of Toronto (Etobicoke to Scarborough) and Vaughan, from the lake to Major "
            "Mackenzie Dr. Being a rectangle, it also takes in parts of Mississauga (with Pearson), "
            "Markham, Richmond Hill and Pickering."
        ),
        bbox=(-79.6400, 43.5800, -79.1150, 43.8700),
    ),
}
