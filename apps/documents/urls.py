"""Documents URL configuration."""
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('upload/', views.document_upload, name='upload'),
    path('<uuid:pk>/', views.document_detail, name='detail'),
    path('<uuid:pk>/process/', views.document_process, name='process'),
    path('<uuid:pk>/view/', views.document_view, name='view'),
    path('<uuid:pk>/extraction/', views.document_extraction, name='extraction'),
]
