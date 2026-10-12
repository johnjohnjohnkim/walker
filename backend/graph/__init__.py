"""The walkable street graph: storage, loading and spatial lookup.

Nothing in this package imports Django, so it can be used and tested on its own.
"""

from .graph import WalkGraph

__all__ = ["WalkGraph"]
