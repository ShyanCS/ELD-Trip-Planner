"""
Trip URL routing.
"""

from django.urls import path

from .views import HealthView, TripPlanView

urlpatterns = [
    path('plan/', TripPlanView.as_view(), name='trip-plan'),
    path('health/', HealthView.as_view(), name='health'),
]
