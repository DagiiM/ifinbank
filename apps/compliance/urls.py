"""Compliance URL configuration."""
from django.urls import path
from . import views

app_name = 'compliance'

urlpatterns = [
    path('policies/', views.policy_list, name='policy_list'),
    path('policies/<uuid:pk>/', views.policy_detail, name='policy_detail'),
    path('check/<uuid:request_id>/', views.run_compliance_check, name='check'),
]
