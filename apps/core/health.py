"""
Health check views for monitoring.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import time


def health_check(request):
    """
    Health check endpoint for load balancers and monitoring.
    
    Returns:
        200 - All systems healthy
        503 - One or more systems unhealthy
    """
    health = {
        'status': 'healthy',
        'timestamp': time.time(),
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        health['checks']['database'] = {'status': 'healthy'}
    except Exception as e:
        health['checks']['database'] = {'status': 'unhealthy', 'error': str(e)}
        health['status'] = 'unhealthy'
    
    # Cache check (if configured)
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['checks']['cache'] = {'status': 'healthy'}
        else:
            health['checks']['cache'] = {'status': 'unhealthy', 'error': 'Cache read failed'}
            health['status'] = 'unhealthy'
    except Exception as e:
        health['checks']['cache'] = {'status': 'unavailable', 'error': str(e)}
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)


def readiness_check(request):
    """
    Readiness check for Kubernetes/container orchestration.
    
    Checks if the application is ready to receive traffic.
    """
    ready = True
    checks = {}
    
    # Database ready
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = True
    except Exception:
        checks['database'] = False
        ready = False
    
    return JsonResponse({
        'ready': ready,
        'checks': checks
    }, status=200 if ready else 503)


def liveness_check(request):
    """
    Liveness check for Kubernetes/container orchestration.
    
    Simple check to verify the application process is running.
    """
    return JsonResponse({'alive': True})
