"""Verification URL configuration."""
from django.urls import path
from . import views

app_name = 'verification'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Verification requests
    path('requests/', views.request_list, name='request_list'),
    path('requests/create/', views.request_create, name='request_create'),
    path('requests/<uuid:pk>/', views.request_detail, name='request_detail'),
    path('requests/<uuid:pk>/process/', views.request_process, name='request_process'),
    path('requests/<uuid:pk>/review/', views.request_review, name='request_review'),
    path('requests/<uuid:pk>/approve/', views.request_approve, name='request_approve'),
    path('requests/<uuid:pk>/reject/', views.request_reject, name='request_reject'),
    
    # API endpoints
    path('api/requests/', views.api_request_list, name='api_request_list'),
    path('api/requests/<uuid:pk>/', views.api_request_detail, name='api_request_detail'),
]
