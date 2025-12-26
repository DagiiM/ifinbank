"""
Health check URL configuration.
"""
from django.urls import path
from . import health

urlpatterns = [
    path('', health.health_check, name='health'),
    path('ready/', health.readiness_check, name='readiness'),
    path('live/', health.liveness_check, name='liveness'),
]
