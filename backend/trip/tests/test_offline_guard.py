"""
Tests for the offline test runner guard itself.

These run inside OfflineTestRunner.run_suite, so the network block is
active — proving that outbound operations raise NetworkBlocked.
"""

import socket

import responses
from django.test import TestCase
from rest_framework.test import APIClient

from config.test_runner import NetworkBlocked


class OfflineGuardTests(TestCase):
    """The suite must fail loudly on any unmocked outbound network use."""

    def test_outbound_tcp_connect_is_blocked(self):
        with self.assertRaises(NetworkBlocked):
            socket.create_connection(("api.openrouteservice.org", 443), timeout=1)

    def test_outbound_dns_resolution_is_blocked(self):
        with self.assertRaises(NetworkBlocked):
            socket.getaddrinfo("example.com", 443)

    def test_loopback_connections_are_allowed(self):
        # Bind an ephemeral port on loopback and connect to it.
        import threading

        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        t = threading.Thread(target=server.accept, daemon=True)
        t.start()
        client = socket.create_connection(("127.0.0.1", port), timeout=2)
        client.close()
        server.close()

    @responses.activate
    def test_mocked_ors_call_still_works_under_guard(self):
        """responses-mocked calls never touch real sockets."""
        responses.add(
            responses.GET,
            "https://api.openrouteservice.org/geocode/search",
            json={"features": []},
            status=200,
        )
        import requests

        response = requests.get(
            "https://api.openrouteservice.org/geocode/search", params={"text": "x"}
        )
        self.assertEqual(response.status_code, 200)

    def test_unmocked_http_request_fails(self):
        """A real (unmocked) requests.get cannot reach the network."""
        import requests

        with self.assertRaises(Exception):
            requests.get("https://api.openrouteservice.org/geocode/search", timeout=1)


class ApiStillReachableUnderGuard(TestCase):
    """Django test client is unaffected by the socket guard."""

    def test_health_endpoint_works(self):
        client = APIClient()
        response = client.get("/api/trip/health/")
        self.assertEqual(response.status_code, 200)
