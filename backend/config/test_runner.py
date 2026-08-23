"""
Offline test runner — hard guarantee that the suite never touches the network.

``OfflineTestRunner`` patches ``socket.socket.connect`` and
``socket.getaddrinfo`` for the duration of the run. Any attempt to open a
TCP connection to (or resolve a hostname other than) a loopback address
raises ``RuntimeError``, so a forgotten mock fails loudly instead of
silently depending on live external services such as api.openrouteservice.org.

Loopback traffic stays allowed: local dev servers, debuggers, and the
SQLite test database are unaffected.

Enable via settings.py:

    TEST_RUNNER = "config.test_runner.OfflineTestRunner"
"""

import ipaddress
import socket
from contextlib import contextmanager
from unittest import mock

from django.test.runner import DiscoverRunner

_LOOPBACK_HOSTNAMES = {"localhost", "::1", "0.0.0.0"}
_UNRESOLVED_ALLOWED = {None, "", "0.0.0.0"}


class NetworkBlocked(RuntimeError):
    """Raised when tests attempt an outbound network operation."""


def _is_loopback(host) -> bool:
    """Return True if *host* is a loopback address or local hostname."""
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if not isinstance(host, str) or host in _UNRESOLVED_ALLOWED:
        return True  # Unix sockets / empty hosts are not outbound network
    if host.lower() in _LOOPBACK_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return host.lower() == socket.gethostname().lower()


def _guarded_connect(real_connect):
    def connect(sock, address):
        host = address[0] if isinstance(address, tuple) else None
        if not _is_loopback(host):
            raise NetworkBlocked(
                f"Outbound network is blocked during tests "
                f"(attempted connection to {host!r}). "
                f"Mock external HTTP calls with the responses library."
            )
        return real_connect(sock, address)

    return connect


def _guarded_getaddrinfo(real_getaddrinfo):
    def getaddrinfo(host, *args, **kwargs):
        if not _is_loopback(host) and args and args[0]:
            raise NetworkBlocked(
                f"Outbound DNS is blocked during tests "
                f"(attempted to resolve {host!r}). "
                f"Mock external HTTP calls with the responses library."
            )
        return real_getaddrinfo(host, *args, **kwargs)

    return getaddrinfo


@contextmanager
def _block_network():
    with (
        mock.patch.object(socket.socket, "connect", _guarded_connect(socket.socket.connect)),
        mock.patch.object(socket, "getaddrinfo", _guarded_getaddrinfo(socket.getaddrinfo)),
    ):
        yield


class OfflineTestRunner(DiscoverRunner):
    """DiscoverRunner that forbids outbound network access while tests run."""

    def run_suite(self, suite, **kwargs):
        with _block_network():
            return super().run_suite(suite, **kwargs)
