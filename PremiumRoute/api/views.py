from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
import json

from shipping.models import Shipment, ShippingRate, ShipmentHistory
from consignment.models import Consignment, ConsignmentHistory
from payments.models import Payment, Invoice
from accounts.models import User, UserProfile
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserProfileSerializer,
    ShipmentSerializer, ShipmentCreateSerializer, ShipmentStatusSerializer,
    ShippingRateSerializer, ConsignmentSerializer, ConsignmentCreateSerializer,
    PaymentSerializer, InvoiceSerializer, TrackingSerializer,
    DashboardStatsSerializer, ShipmentReportSerializer
)
from .permissions import IsOwner, IsStaffOrReadOnly, IsAdminOrReadOnly

# User Views
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['email', 'date_joined', 'last_login']

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user's profile"""
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update current user's profile"""
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'user': UserSerializer(user).data,
                'message': 'User registered successfully'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Shipment Views
class ShipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'shipping_method']
    search_fields = ['tracking_number', 'receiver_name', 'sender_name', 'receiver_phone']
    ordering_fields = ['created_at', 'estimated_delivery', 'total_cost']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'staff']:
            return Shipment.objects.all()
        return Shipment.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ShipmentCreateSerializer
        elif self.action == 'update_status':
            return ShipmentStatusSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update shipment status"""
        shipment = self.get_object()
        serializer = self.get_serializer(shipment, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        old_status = shipment.status
        shipment = serializer.save()
        
        # Create history entry
        ShipmentHistory.objects.create(
            shipment=shipment,
            status=shipment.status,
            location=request.data.get('location', ''),
            description=request.data.get('description', 'Status updated via API'),
            created_by=request.user
        )
        
        return Response({
            'tracking_number': shipment.tracking_number,
            'old_status': old_status,
            'new_status': shipment.status,
            'message': 'Status updated successfully'
        })
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get shipment history"""
        shipment = self.get_object()
        history = shipment.history.all().order_by('-created_at')
        serializer = TrackingSerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def generate_label(self, request, pk=None):
        """Generate shipping label (PDF)"""
        shipment = self.get_object()
        # In production, this would generate and return a PDF
        return Response({
            'tracking_number': shipment.tracking_number,
            'label_url': f'/api/shipments/{shipment.id}/label.pdf',
            'message': 'Label generation endpoint'
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get shipment statistics for current user"""
        user = request.user
        queryset = self.get_queryset()
        
        total = queryset.count()
        pending = queryset.filter(status='pending').count()
        in_transit = queryset.filter(status='in_transit').count()
        delivered = queryset.filter(status='delivered').count()
        total_spent = queryset.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        
        return Response({
            'total_shipments': total,
            'pending_shipments': pending,
            'in_transit_shipments': in_transit,
            'delivered_shipments': delivered,
            'total_spent': total_spent,
            'average_cost': total_spent / total if total > 0 else 0
        })

# Consignment Views
class ConsignmentViewSet(viewsets.ModelViewSet):
    serializer_class = ConsignmentSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'consignment_type', 'customs_cleared']
    search_fields = ['consignment_number', 'consignee_name', 'shipper_name']
    ordering_fields = ['created_at', 'arrival_date', 'total_charges']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'staff']:
            return Consignment.objects.all()
        return Consignment.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ConsignmentCreateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a consignment (admin only)"""
        consignment = self.get_object()
        if not request.user.user_type in ['admin', 'staff']:
            return Response(
                {'error': 'Only admin or staff can approve consignments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        consignment.status = 'approved'
        consignment.approved_by = request.user
        consignment.approved_at = timezone.now()
        consignment.save()
        
        ConsignmentHistory.objects.create(
            consignment=consignment,
            status='approved',
            description='Consignment approved via API',
            created_by=request.user
        )
        
        return Response({
            'consignment_number': consignment.consignment_number,
            'status': consignment.status,
            'approved_by': request.user.email,
            'approved_at': consignment.approved_at
        })
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Get consignment documents list"""
        consignment = self.get_object()
        documents = []
        
        if consignment.commercial_invoice:
            documents.append({
                'name': 'Commercial Invoice',
                'url': consignment.commercial_invoice.url,
                'size': consignment.commercial_invoice.size
            })
        if consignment.packing_list:
            documents.append({
                'name': 'Packing List',
                'url': consignment.packing_list.url,
                'size': consignment.packing_list.size
            })
        
        return Response(documents)

# Shipping Rate Views
class ShippingRateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShippingRate.objects.filter(is_active=True)
    serializer_class = ShippingRateSerializer
    permission_classes = [IsAuthenticated | AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['service_type', 'zone']
    search_fields = ['name', 'description']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]

# Payment Views
class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method']
    ordering_fields = ['created_at', 'amount']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'staff']:
            return Payment.objects.all()
        return Payment.objects.filter(user=user)
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process a payment"""
        payment = self.get_object()
        
        # In production, this would integrate with payment gateway
        payment.status = 'processing'
        payment.save()
        
        return Response({
            'payment_id': payment.payment_id,
            'status': payment.status,
            'message': 'Payment processing started'
        })

# Invoice Views
class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['issue_date', 'total_amount']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'staff']:
            return Invoice.objects.all()
        return Invoice.objects.filter(user=user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download invoice PDF"""
        invoice = self.get_object()
        # In production, this would generate and return a PDF
        return Response({
            'invoice_number': invoice.invoice_number,
            'download_url': f'/api/invoices/{invoice.id}/download.pdf',
            'message': 'Invoice download endpoint'
        })

# Tracking Views
class TrackingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Shipment.objects.all()
    serializer_class = TrackingSerializer
    permission_classes = [AllowAny]
    lookup_field = 'tracking_number'
    lookup_url_kwarg = 'tracking_number'
    
    def get_object(self):
        tracking_number = self.kwargs.get('tracking_number')
        
        # Try to find shipment
        shipment = Shipment.objects.filter(tracking_number=tracking_number).first()
        if shipment:
            return shipment
        
        # Try to find consignment
        consignment = Consignment.objects.filter(consignment_number=tracking_number).first()
        if consignment:
            return consignment
        
        raise Http404("Tracking number not found")
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if isinstance(instance, Shipment):
            history = instance.history.all().order_by('-created_at')
            data = {
                'type': 'shipment',
                'tracking_number': instance.tracking_number,
                'status': instance.status,
                'sender': instance.sender_name,
                'receiver': instance.receiver_name,
                'origin': f"{instance.sender_city}, {instance.sender_country}",
                'destination': f"{instance.receiver_city}, {instance.receiver_country}",
                'estimated_delivery': instance.estimated_delivery,
                'actual_delivery': instance.actual_delivery,
                'history': TrackingSerializer(history, many=True).data
            }
        else:
            history = instance.history.all().order_by('-created_at')
            data = {
                'type': 'consignment',
                'tracking_number': instance.consignment_number,
                'status': instance.status,
                'shipper': instance.shipper_name,
                'consignee': instance.consignee_name,
                'origin': instance.origin_port,
                'destination': instance.destination_port,
                'estimated_arrival': instance.arrival_date,
                'vessel_flight_no': instance.vessel_flight_no,
                'history': TrackingSerializer(history, many=True).data
            }
        
        return Response(data)

# Calculate Rate View
class CalculateRateView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            data = request.data
            
            # Extract parameters
            weight = float(data.get('weight', 0))
            length = float(data.get('length', 0))
            width = float(data.get('width', 0))
            height = float(data.get('height', 0))
            from_country = data.get('from_country', 'US')
            to_country = data.get('to_country', 'US')
            service_type = data.get('service_type', 'standard')
            declared_value = float(data.get('declared_value', 0))
            
            # Calculate base rate (simplified)
            base_rate = 10.0  # Base rate
            weight_rate = weight * 2.0  # $2 per kg
            distance_multiplier = 1.0
            
            # Distance multiplier
            if from_country != to_country:
                distance_multiplier = 1.5  # International shipping
            
            # Service type multiplier
            service_multipliers = {
                'standard': 1.0,
                'express': 1.5,
                'overnight': 2.0,
                'same_day': 2.5,
            }
            service_multiplier = service_multipliers.get(service_type, 1.0)
            
            # Calculate total
            total = (base_rate + weight_rate) * distance_multiplier * service_multiplier
            
            # Add insurance if declared value > 0
            insurance = declared_value * 0.01 if declared_value > 0 else 0
            
            return Response({
                'success': True,
                'base_rate': base_rate,
                'weight_rate': weight_rate,
                'distance_multiplier': distance_multiplier,
                'service_multiplier': service_multiplier,
                'insurance': insurance,
                'total': total + insurance,
                'currency': 'USD',
                'estimated_days': '3-5 business days' if service_type == 'standard' else '1-2 business days'
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

# Track Shipment View
class TrackShipmentView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, tracking_number):
        try:
            # Try shipment first
            shipment = Shipment.objects.filter(tracking_number=tracking_number).first()
            if shipment:
                history = shipment.history.all().order_by('-created_at')
                
                return Response({
                    'success': True,
                    'type': 'shipment',
                    'tracking_number': shipment.tracking_number,
                    'status': shipment.status,
                    'sender': shipment.sender_name,
                    'receiver': shipment.receiver_name,
                    'origin': f"{shipment.sender_city}, {shipment.sender_country}",
                    'destination': f"{shipment.receiver_city}, {shipment.receiver_country}",
                    'estimated_delivery': shipment.estimated_delivery,
                    'actual_delivery': shipment.actual_delivery,
                    'history': [
                        {
                            'status': h.status,
                            'location': h.location,
                            'description': h.description,
                            'timestamp': h.created_at
                        }
                        for h in history
                    ]
                })
            
            # Try consignment
            consignment = Consignment.objects.filter(consignment_number=tracking_number).first()
            if consignment:
                history = consignment.history.all().order_by('-created_at')
                
                return Response({
                    'success': True,
                    'type': 'consignment',
                    'tracking_number': consignment.consignment_number,
                    'status': consignment.status,
                    'shipper': consignment.shipper_name,
                    'consignee': consignment.consignee_name,
                    'origin': consignment.origin_port,
                    'destination': consignment.destination_port,
                    'estimated_arrival': consignment.arrival_date,
                    'vessel_flight_no': consignment.vessel_flight_no,
                    'history': [
                        {
                            'status': h.status,
                            'location': h.location,
                            'description': h.description,
                            'timestamp': h.created_at
                        }
                        for h in history
                    ]
                })
            
            return Response({
                'success': False,
                'error': 'Tracking number not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

# Webhook Views
class TrackingWebhookView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            data = request.data
            tracking_number = data.get('tracking_number')
            status = data.get('status')
            location = data.get('location', '')
            description = data.get('description', '')
            
            # Validate webhook secret (in production)
            # webhook_secret = request.headers.get('X-Webhook-Secret')
            # if webhook_secret != settings.TRACKING_WEBHOOK_SECRET:
            #     return Response({'error': 'Invalid webhook secret'}, status=403)
            
            # Update shipment
            shipment = Shipment.objects.filter(tracking_number=tracking_number).first()
            if shipment:
                shipment.status = status
                shipment.save()
                
                ShipmentHistory.objects.create(
                    shipment=shipment,
                    status=status,
                    location=location,
                    description=description
                )
                
                return Response({
                    'success': True,
                    'message': f'Shipment {tracking_number} updated to {status}'
                })
            
            # Update consignment
            consignment = Consignment.objects.filter(consignment_number=tracking_number).first()
            if consignment:
                consignment.status = status
                consignment.save()
                
                ConsignmentHistory.objects.create(
                    consignment=consignment,
                    status=status,
                    location=location,
                    description=description
                )
                
                return Response({
                    'success': True,
                    'message': f'Consignment {tracking_number} updated to {status}'
                })
            
            return Response({
                'success': False,
                'error': 'Tracking number not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class StripeWebhookView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        # This would handle Stripe webhooks in production
        return Response({
            'success': True,
            'message': 'Stripe webhook endpoint'
        })

# Dashboard Views
class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.user_type in ['admin', 'staff']:
            # Admin dashboard stats
            total_shipments = Shipment.objects.count()
            total_consignments = Consignment.objects.count()
            total_users = User.objects.count()
            total_revenue = Shipment.objects.filter(payment_status='paid').aggregate(
                Sum('total_cost')
            )['total_cost__sum'] or 0
            
            # Recent shipments
            recent_shipments = Shipment.objects.order_by('-created_at')[:5]
            
            return Response({
                'total_shipments': total_shipments,
                'total_consignments': total_consignments,
                'total_users': total_users,
                'total_revenue': total_revenue,
                'recent_shipments': ShipmentSerializer(recent_shipments, many=True).data
            })
        else:
            # Customer dashboard stats
            shipments = Shipment.objects.filter(user=user)
            total_shipments = shipments.count()
            pending = shipments.filter(status='pending').count()
            in_transit = shipments.filter(status='in_transit').count()
            delivered = shipments.filter(status='delivered').count()
            total_spent = shipments.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
            
            # Recent shipments
            recent_shipments = shipments.order_by('-created_at')[:5]
            
            return Response({
                'total_shipments': total_shipments,
                'pending_shipments': pending,
                'in_transit_shipments': in_transit,
                'delivered_shipments': delivered,
                'total_spent': total_spent,
                'recent_shipments': ShipmentSerializer(recent_shipments, many=True).data
            })

class RecentActivityView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        limit = int(request.query_params.get('limit', 10))
        
        if user.user_type in ['admin', 'staff']:
            # Get recent shipments and consignments
            recent_shipments = Shipment.objects.order_by('-created_at')[:limit]
            recent_consignments = Consignment.objects.order_by('-created_at')[:limit]
        else:
            # Get user's recent shipments and consignments
            recent_shipments = Shipment.objects.filter(user=user).order_by('-created_at')[:limit]
            recent_consignments = Consignment.objects.filter(user=user).order_by('-created_at')[:limit]
        
        return Response({
            'shipments': ShipmentSerializer(recent_shipments, many=True).data,
            'consignments': ConsignmentSerializer(recent_consignments, many=True).data
        })

# Report Views
class ShipmentReportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get date range from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if user.user_type in ['admin', 'staff']:
            queryset = Shipment.objects.all()
        else:
            queryset = Shipment.objects.filter(user=user)
        
        # Apply date filters
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Generate report data
        total = queryset.count()
        total_revenue = queryset.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        
        # Status distribution
        status_distribution = queryset.values('status').annotate(
            count=Count('id'),
            revenue=Sum('total_cost')
        )
        
        # Monthly trend
        monthly_data = queryset.extra(
            {'month': "strftime('%Y-%m', created_at)"}
        ).values('month').annotate(
            count=Count('id'),
            revenue=Sum('total_cost')
        ).order_by('month')
        
        return Response({
            'total_shipments': total,
            'total_revenue': total_revenue,
            'average_value': total_revenue / total if total > 0 else 0,
            'status_distribution': list(status_distribution),
            'monthly_trend': list(monthly_data)
        })

class FinancialReportView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Get date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Payment data
        payments = Payment.objects.filter(status='completed')
        if start_date:
            payments = payments.filter(created_at__date__gte=start_date)
        if end_date:
            payments = payments.filter(created_at__date__lte=end_date)
        
        total_revenue = payments.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Payment method distribution
        payment_methods = payments.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount')
        )
        
        # Monthly revenue
        monthly_revenue = payments.extra(
            {'month': "strftime('%Y-%m', created_at)"}
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        return Response({
            'total_revenue': total_revenue,
            'payment_methods': list(payment_methods),
            'monthly_revenue': list(monthly_revenue),
            'average_payment': total_revenue / payments.count() if payments.count() > 0 else 0
        })

# Public Views (No Authentication Required)
class PublicTrackingView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, tracking_number):
        # Same as TrackShipmentView but with AllowAny permission
        return TrackShipmentView().get(request, tracking_number)

class PublicShippingRatesView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        rates = ShippingRate.objects.filter(is_active=True)
        serializer = ShippingRateSerializer(rates, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Allow public rate calculation
        return CalculateRateView().post(request)

class ServiceStatusView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Check if services are running
        try:
            # Test database connection
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            return Response({
                'status': 'operational',
                'database': 'connected',
                'timestamp': timezone.now(),
                'version': '1.0.0',
                'services': ['api', 'tracking', 'payments', 'notifications']
            })
        except Exception as e:
            return Response({
                'status': 'degraded',
                'database': 'disconnected',
                'error': str(e),
                'timestamp': timezone.now()
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)