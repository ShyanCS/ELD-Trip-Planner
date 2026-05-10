"""
Trip views — POST endpoint that orchestrates the full trip planning pipeline.

Pipeline:  Request → Validate → Geocode → Route → HOS Calculate → Response
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import TripPlanSerializer
from .geocoder import geocode, get_route, get_intermediate_point, clear_cache
from .hos_calculator import calculate_trip

logger = logging.getLogger(__name__)


class TripPlanView(APIView):
    """
    POST /api/trip/plan/

    Accepts trip inputs, returns route + HOS-compliant daily logs.

    Request body:
        {
            "current_location": "Chicago, IL",
            "pickup_location": "Kansas City, MO",
            "dropoff_location": "Los Angeles, CA",
            "current_cycle_used": 20,
            "start_date": "2026-05-07"  (optional)
        }

    Response:
        {
            "route": {
                "total_distance_miles": 2110,
                "total_duration_hours": 38.4,
                "geometry": { GeoJSON LineString },
                "waypoints": [ { type, name, lat, lon, miles_from_start } ]
            },
            "daily_logs": [ ... ],
            "stop_events": [ ... ]
        }
    """

    def post(self, request):
        # ── Step 1: Validate input ──
        serializer = TripPlanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            # Clear geocode cache between requests
            clear_cache()

            # ── Step 2: Geocode locations ──
            current_geo = geocode(data['current_location'])
            pickup_geo = geocode(data['pickup_location'])
            dropoff_geo = geocode(data['dropoff_location'])

            # ── Step 3: Get routes ──
            # Route 1: Current → Pickup
            route_to_pickup = get_route([
                [current_geo['lon'], current_geo['lat']],
                [pickup_geo['lon'], pickup_geo['lat']],
            ])

            # Route 2: Pickup → Dropoff
            route_to_dropoff = get_route([
                [pickup_geo['lon'], pickup_geo['lat']],
                [dropoff_geo['lon'], dropoff_geo['lat']],
            ])

            # Combine geometries into one for the full route polyline
            full_geometry = _merge_geometries(
                route_to_pickup['geometry'],
                route_to_dropoff['geometry'],
            )

            total_distance = route_to_pickup['distance_miles'] + route_to_dropoff['distance_miles']
            total_duration = route_to_pickup['duration_hours'] + route_to_dropoff['duration_hours']

            # ── Step 4: Run HOS Calculator ──
            segments = [
                {
                    'distance_miles': route_to_pickup['distance_miles'],
                    'from_location': current_geo['name'],
                    'to_location': pickup_geo['name'],
                },
                {
                    'distance_miles': route_to_dropoff['distance_miles'],
                    'from_location': pickup_geo['name'],
                    'to_location': dropoff_geo['name'],
                },
            ]

            start_date = data.get('start_date')
            start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None

            hos_result = calculate_trip(
                segments=segments,
                current_cycle_used=data['current_cycle_used'],
                start_date=start_date_str,
            )

            # ── Step 5: Build waypoints ──
            waypoints = _build_waypoints(
                current_geo=current_geo,
                pickup_geo=pickup_geo,
                dropoff_geo=dropoff_geo,
                stop_events=hos_result['stop_events'],
                full_geometry=full_geometry,
            )

            # ── Step 6: Build response ──
            response_data = {
                'route': {
                    'total_distance_miles': round(total_distance, 1),
                    'total_duration_hours': round(total_duration, 2),
                    'geometry': full_geometry,
                    'waypoints': waypoints,
                },
                'daily_logs': hos_result['daily_logs'],
                'stop_events': hos_result['stop_events'],
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            # Geocoding or routing errors
            logger.warning(f"Trip planning failed (ValueError): {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            # Unexpected errors
            logger.error(f"Trip planning failed (unexpected): {e}", exc_info=True)
            return Response(
                {'error': 'An unexpected error occurred. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def _merge_geometries(geom1, geom2):
    """
    Merge two GeoJSON LineString geometries into one continuous line.
    Removes the duplicate junction point.
    """
    coords1 = geom1.get('coordinates', [])
    coords2 = geom2.get('coordinates', [])

    # Skip the first point of geom2 to avoid duplicate at junction
    if coords2:
        merged = coords1 + coords2[1:]
    else:
        merged = coords1

    return {
        'type': 'LineString',
        'coordinates': merged,
    }


def _build_waypoints(current_geo, pickup_geo, dropoff_geo, stop_events, full_geometry):
    """
    Build the ordered list of map waypoints from fixed locations + stop events.

    Each waypoint: { type, name, lat, lon, miles_from_start }
    """
    waypoints = []

    # Start waypoint
    waypoints.append({
        'type': 'start',
        'name': current_geo['name'],
        'lat': current_geo['lat'],
        'lon': current_geo['lon'],
        'miles_from_start': 0,
    })

    # Process stop events (fuel and rest stops) — resolve geographic positions
    for stop in stop_events:
        try:
            point = get_intermediate_point(full_geometry, stop['total_miles_at_stop'])
            waypoints.append({
                'type': stop['type'],
                'name': point['name'],
                'lat': point['lat'],
                'lon': point['lon'],
                'miles_from_start': stop['total_miles_at_stop'],
            })
        except Exception as e:
            logger.warning(f"Could not place stop waypoint at mile {stop['total_miles_at_stop']}: {e}")
            # Skip this waypoint if geo-placement fails

    # Pickup waypoint
    waypoints.append({
        'type': 'pickup',
        'name': pickup_geo['name'],
        'lat': pickup_geo['lat'],
        'lon': pickup_geo['lon'],
        'miles_from_start': None,  # Will be calculated client-side if needed
    })

    # Dropoff waypoint
    waypoints.append({
        'type': 'dropoff',
        'name': dropoff_geo['name'],
        'lat': dropoff_geo['lat'],
        'lon': dropoff_geo['lon'],
        'miles_from_start': None,
    })

    # Sort by miles_from_start (None values go to end)
    waypoints.sort(key=lambda w: (w['miles_from_start'] is None, w['miles_from_start'] or 0))

    return waypoints
