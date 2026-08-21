"""
Trip URL routing.
"""

from django.urls import path

from .views import HealthView, MetricsView, TripPlanView, VersionView

urlpatterns = [
    path('plan/', TripPlanView.as_view(), name='trip-plan'),
    path('health/', HealthView.as_view(), name='health'),
    path('metrics/', MetricsView.as_view(), name='metrics'),
    path('version/', VersionView.as_view(), name='version'),
]
