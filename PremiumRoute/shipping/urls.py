from django.urls import path
from . import views

urlpatterns = [
    # Customer URLs
    path('create/', views.create_shipment, name='create_shipment'),
    path('list/', views.shipment_list, name='shipment_list'),
    path('<str:tracking_number>/', views.shipment_detail, name='shipment_detail'),
    path('rates/', views.shipping_rates, name='shipping_rates'),
    path('calculate-rate/', views.calculate_rate, name='calculate_rate'),
    
    # Admin URLs
    path('admin/list/', views.admin_shipment_list, name='admin_shipment_list'),
    path('admin/<str:tracking_number>/', views.admin_shipment_detail, name='admin_shipment_detail'),
    path('admin/<str:tracking_number>/update-status/', views.update_shipment_status, name='update_shipment_status'),
    path('admin/rates/', views.manage_shipping_rates, name='manage_shipping_rates'),
    path('admin/rates/<int:rate_id>/toggle/', views.toggle_shipping_rate, name='toggle_shipping_rate'),
]