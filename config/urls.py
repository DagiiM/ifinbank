"""
URL configuration for iFin Bank Verification System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


def home_redirect(request):
    """Redirect home to verification dashboard."""
    if request.user.is_authenticated:
        return redirect('verification:dashboard')
    return redirect('accounts:login')


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Home redirect
    path('', home_redirect, name='home'),
    
    # Health checks (for load balancers / monitoring)
    path('health/', include('apps.core.health_urls')),
    
    # App URLs
    path('accounts/', include('apps.accounts.urls')),
    path('verification/', include('apps.verification.urls')),
    path('documents/', include('apps.documents.urls')),
    path('compliance/', include('apps.compliance.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])


# Admin site customization
admin.site.site_header = 'iFin Bank Verification'
admin.site.site_title = 'iFin Bank Admin'
admin.site.index_title = 'Administration'
