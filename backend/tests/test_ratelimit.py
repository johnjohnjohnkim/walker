from django.test import RequestFactory

from routing.ratelimit import client_of


def request(remote="10.0.0.1", forwarded=None):
    headers = {"REMOTE_ADDR": remote}
    if forwarded is not None:
        headers["HTTP_X_FORWARDED_FOR"] = forwarded
    return RequestFactory().get("/", **headers)


def test_uses_the_direct_address_without_a_proxy(settings):
    settings.WALKER_BEHIND_PROXY = False

    # A visitor can send any X-Forwarded-For; without a proxy it's ignored.
    assert client_of(request(remote="203.0.113.5", forwarded="1.2.3.4")) == "203.0.113.5"


def test_uses_the_address_the_proxy_added(settings):
    settings.WALKER_BEHIND_PROXY = True

    # The proxy (Caddy) appends the real visitor; anything before is the visitor's claim.
    assert client_of(request(remote="172.18.0.3", forwarded="6.6.6.6, 198.51.100.7")) == "198.51.100.7"


def test_falls_back_when_the_proxy_header_is_missing(settings):
    settings.WALKER_BEHIND_PROXY = True

    assert client_of(request(remote="172.18.0.3")) == "172.18.0.3"
