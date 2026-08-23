"""
Typed exceptions for the trip planning pipeline.

Every failure surfaced by POST /api/trip/plan/ maps to a TripPlanError
carrying a machine-readable ``code``, a human-readable ``message``, and
optional structured ``details``. Views serialize these via
``TripPlanError.to_dict()`` into the API's structured error schema:

    {
        "error": {
            "code": "GEOCODE_FAILED",
            "message": "Could not find location: 'Nowhere'. ...",
            "details": {"location": "Nowhere"}
        }
    }
"""

import requests


class TripPlanError(Exception):
    """Base class for all trip-planning pipeline failures."""

    code = "TRIP_PLAN_FAILED"
    http_status = 400

    def __init__(self, message, *, details=None, code=None):
        super().__init__(message)
        self.message = message
        self.details = details
        if code is not None:
            self.code = code

    def to_dict(self):
        """Serialize to the structured API error schema."""
        payload = {"code": self.code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return payload

    def __str__(self):
        return f"[{self.code}] {self.message}"


class GeocodeError(TripPlanError):
    """A location could not be resolved to coordinates."""

    code = "GEOCODE_FAILED"


class RouteError(TripPlanError):
    """A driving route could not be calculated."""

    code = "ROUTE_FAILED"


class HOSCalculationError(TripPlanError):
    """The trip cannot be completed within FMCSA hours-of-service limits."""

    code = "HOS_FAILED"


class UpstreamServiceError(TripPlanError):
    """The OpenRouteService API is unreachable or returned a server error."""

    code = "UPSTREAM_UNAVAILABLE"
    http_status = 503

    @classmethod
    def from_request_exception(cls, exc: requests.RequestException) -> "UpstreamServiceError":
        return cls("Routing service unavailable. Please try again shortly.", details={"cause": type(exc).__name__})
