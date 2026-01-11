from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from . import views

router = DefaultRouter()
router.register(r'shipments', views.ShipmentViewSet, basename='shipment')
router.register(r'consignments', views.ConsignmentViewSet, basename='consignment')
router.register(r'tracking', views.TrackingViewSet, basename='tracking')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')
router.register(r'shipping-rates', views.ShippingRateViewSet, basename='shipping-rate')
router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    
    # Authentication
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    
    # Shipping
    path('rates/calculate/', views.CalculateRateView.as_view(), name='calculate_rate'),
    path('track/<str:tracking_number>/', views.TrackShipmentView.as_view(), name='track_shipment'),
    
    # Webhooks
    path('webhook/tracking/', views.TrackingWebhookView.as_view(), name='tracking_webhook'),
    path('webhook/payment/stripe/', views.StripeWebhookView.as_view(), name='stripe_webhook'),
    
    # Dashboard
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard_stats'),
    path('dashboard/recent/', views.RecentActivityView.as_view(), name='recent_activity'),
    
    # Reports
    path('reports/shipments/', views.ShipmentReportView.as_view(), name='shipment_report'),
    path('reports/financial/', views.FinancialReportView.as_view(), name='financial_report'),
    
    # Public endpoints (no authentication required)
    path('public/track/<str:tracking_number>/', views.PublicTrackingView.as_view(), name='public_tracking'),
    path('public/rates/', views.PublicShippingRatesView.as_view(), name='public_rates'),
    path('public/service-status/', views.ServiceStatusView.as_view(), name='service_status'),
]