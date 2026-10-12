"""Turning place names into coordinates, behind a provider-neutral interface.

The rest of the app only sees `Geocoder.search()` returning `Place`s, so the
provider (Photon today, maybe MapTiler later) is chosen in settings.
"""

from .base import Geocoder, GeocoderUnavailable, Place

__all__ = ["Geocoder", "GeocoderUnavailable", "Place"]
