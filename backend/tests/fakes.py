from geocoding import GeocoderUnavailable, Place

CN_TOWER = Place(name="CN Tower", address="290 Bremner Boulevard, Toronto", lon=-79.3871, lat=43.6426)
UNION = Place(name="Union Station", address="65 Front Street West, Toronto", lon=-79.3806, lat=43.6453)


class FakeGeocoder:
    """Answers from a fixed list and records what it was asked."""

    calls: list[tuple[str, tuple, int]] = []
    fail = False

    def search(self, query, *, bbox, limit):
        FakeGeocoder.calls.append((query, bbox, limit))
        if FakeGeocoder.fail:
            raise GeocoderUnavailable("down")
        return [p for p in (CN_TOWER, UNION) if query in p.name.lower()][:limit]


class OtherGeocoder:
    def search(self, query, *, bbox, limit):
        return [Place(name="Somewhere else", address="", lon=0.0, lat=0.0)]
