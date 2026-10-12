import io
import json
import urllib.error
from unittest import mock

import pytest

from geocoding import GeocoderUnavailable
from geocoding.photon import PhotonGeocoder, parse

BBOX = (-79.5, 43.6, -79.3, 43.7)


def feature(name=None, lon=-79.38, lat=43.65, **props):
    if name is not None:
        props["name"] = name
    return {"type": "Feature", "properties": props, "geometry": {"type": "Point", "coordinates": [lon, lat]}}


def test_parses_names_and_addresses():
    body = {"features": [feature("CN Tower", housenumber="290", street="Bremner Boulevard", locality="CityPlace", city="Toronto")]}

    [place] = parse(body, BBOX)

    assert place.name == "CN Tower"
    assert place.address == "290 Bremner Boulevard, CityPlace, Toronto"
    assert (place.lon, place.lat) == (-79.38, 43.65)


def test_uses_the_street_address_when_there_is_no_name():
    [place] = parse({"features": [feature(housenumber="65", street="Front Street West", city="Toronto")]}, BBOX)

    assert place.name == "65 Front Street West"
    assert place.address == "Toronto"


def test_skips_places_outside_the_box_and_malformed_features():
    body = {
        "features": [
            feature("Far away", lon=-80.5),
            {"geometry": {"coordinates": ["x", "y"]}},
            {"properties": {"name": "No geometry"}},
            feature("Not a number", lon=float("nan")),
            feature(""),
            {"properties": "not a dict", "geometry": {"type": "Point", "coordinates": [-79.38, 43.65]}},
            {"geometry": "not a dict"},
            feature("Kept"),
        ]
    }

    assert [p.name for p in parse(body, BBOX)] == ["Kept"]


def test_drops_duplicates():
    body = {"features": [feature("Tim Hortons", city="Toronto"), feature("Tim Hortons", city="Toronto", lon=-79.381)]}

    assert len(parse(body, BBOX)) == 1


@pytest.mark.parametrize("body", [[], {"features": "nope"}, "text"])
def test_unexpected_responses_are_errors(body):
    with pytest.raises(GeocoderUnavailable):
        parse(body, BBOX)


def test_sends_the_box_focus_and_user_agent():
    geocoder = PhotonGeocoder(base_url="https://photon.example/", user_agent="walker-test")
    response = io.BytesIO(json.dumps({"features": []}).encode())
    with mock.patch("urllib.request.urlopen", return_value=response) as urlopen:
        geocoder.search("cn tower", bbox=BBOX, limit=5)

    request = urlopen.call_args.args[0]
    assert request.full_url.startswith("https://photon.example/api/?")
    assert "q=cn+tower" in request.full_url
    assert "bbox=-79.5%2C43.6%2C-79.3%2C43.7" in request.full_url
    assert "lat=43.65" in request.full_url
    assert request.get_header("User-agent") == "walker-test"


@pytest.mark.parametrize(
    "failure",
    [urllib.error.URLError("no route"), TimeoutError(), urllib.error.HTTPError("u", 502, "bad", {}, None)],
)
def test_network_failures_become_unavailable(failure):
    geocoder = PhotonGeocoder(base_url="https://photon.example", user_agent="t")
    with mock.patch("urllib.request.urlopen", side_effect=failure), pytest.raises(GeocoderUnavailable):
        geocoder.search("cn", bbox=BBOX, limit=5)


def test_invalid_json_becomes_unavailable():
    geocoder = PhotonGeocoder(base_url="https://photon.example", user_agent="t")
    with mock.patch("urllib.request.urlopen", return_value=io.BytesIO(b"<html>")), pytest.raises(GeocoderUnavailable):
        geocoder.search("cn", bbox=BBOX, limit=5)
