from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Home
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    
    # Accounts
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    
    # Shipping
    path('shipping/', include('shipping.urls')),
    
    # Consignment
    path('consignment/', include('consignment.urls')),
    
    # Tracking
    path('track/', include('tracking.urls')),
    
    # Payments
    path('payments/', include('payments.urls')),
    
    # Reports
    path('reports/', include('reports.urls')),
    
    # API
    path('api/', include('api.urls')),

    path('api/', include('api.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom admin site configuration
admin.site.site_header = 'Consignment & Shipping System Admin'
admin.site.site_title = 'Shipping System'
admin.site.index_title = 'Dashboard'