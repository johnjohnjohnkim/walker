"""Geocoding with Photon (https://photon.komoot.io), a free search engine for
OpenStreetMap data built for search-as-you-type.

The public instance is best-effort and asks for light use, so the backend
caches results and rate-limits callers (see routing/views.py).
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request

from .base import BBox, GeocoderUnavailable, Place


class PhotonGeocoder:
    def __init__(self, *, base_url: str, user_agent: str, timeout_s: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout_s = timeout_s

    def search(self, query: str, *, bbox: BBox, limit: int) -> list[Place]:
        west, south, east, north = bbox
        params = {
            "q": query,
            "limit": str(limit),
            "lang": "en",
            # Only places inside the map, ranked by closeness to its middle.
            "bbox": f"{west},{south},{east},{north}",
            "lon": str((west + east) / 2),
            "lat": str((south + north) / 2),
        }
        url = f"{self.base_url}/api/?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                body = json.load(response)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise GeocoderUnavailable(f"Photon request failed: {exc}") from exc
        return parse(body, bbox)


def parse(body: object, bbox: BBox) -> list[Place]:
    """Turn a Photon GeoJSON response into Places, skipping anything malformed
    or outside the box, and dropping repeats of the same name and address."""
    if not isinstance(body, dict) or not isinstance(body.get("features"), list):
        raise GeocoderUnavailable("Photon returned an unexpected response")

    west, south, east, north = bbox
    places: list[Place] = []
    seen: set[tuple[str, str]] = set()
    for feature in body["features"]:
        try:
            lon, lat = (float(c) for c in feature["geometry"]["coordinates"][:2])
            props = feature.get("properties") or {}
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if not isinstance(props, dict):
            continue
        if not (math.isfinite(lon) and math.isfinite(lat) and west <= lon <= east and south <= lat <= north):
            continue
        name, address = _describe(props)
        if not name or (name, address) in seen:
            continue
        seen.add((name, address))
        places.append(Place(name=name, address=address, lon=lon, lat=lat))
    return places


def _describe(props: dict) -> tuple[str, str]:
    street = " ".join(str(p) for p in (props.get("housenumber"), props.get("street")) if p)
    name = props.get("name") or street
    parts = [street if street != name else None, props.get("locality") or props.get("district"), props.get("city")]
    address = ", ".join(str(p) for p in parts if p)
    return str(name or ""), address
