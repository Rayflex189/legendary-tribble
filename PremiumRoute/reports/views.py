from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json
from shipping.models import Shipment
from consignment.models import Consignment
from payments.models import Payment
from accounts.models import User

@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def dashboard_reports(request):
    """Main reports dashboard"""
    
    # Date ranges
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    last_year = today - timedelta(days=365)
    
    # Shipment statistics
    shipments_today = Shipment.objects.filter(created_at__date=today).count()
    shipments_week = Shipment.objects.filter(created_at__date__gte=last_week).count()
    shipments_month = Shipment.objects.filter(created_at__date__gte=last_month).count()
    shipments_year = Shipment.objects.filter(created_at__date__gte=last_year).count()
    
    # Revenue statistics
    revenue_today = Shipment.objects.filter(
        created_at__date=today, 
        payment_status='paid'
    ).aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    
    revenue_month = Shipment.objects.filter(
        created_at__date__gte=last_month, 
        payment_status='paid'
    ).aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    
    revenue_year = Shipment.objects.filter(
        created_at__date__gte=last_year, 
        payment_status='paid'
    ).aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    
    # Status distribution
    status_distribution = Shipment.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Top customers
    top_customers = User.objects.filter(
        shipments__isnull=False
    ).annotate(
        shipment_count=Count('shipments'),
        total_spent=Sum('shipments__total_cost')
    ).order_by('-total_spent')[:10]
    
    # Recent activities
    recent_shipments = Shipment.objects.select_related('user').order_by('-created_at')[:10]
    
    context = {
        'shipments_today': shipments_today,
        'shipments_week': shipments_week,
        'shipments_month': shipments_month,
        'shipments_year': shipments_year,
        'revenue_today': revenue_today,
        'revenue_month': revenue_month,
        'revenue_year': revenue_year,
        'status_distribution': status_distribution,
        'top_customers': top_customers,
        'recent_shipments': recent_shipments,
    }
    
    return render(request, 'reports/dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def shipment_reports(request):
    """Detailed shipment reports"""
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    payment_status = request.GET.get('payment_status')
    
    # Base queryset
    shipments = Shipment.objects.all()
    
    # Apply filters
    if start_date:
        shipments = shipments.filter(created_at__date__gte=start_date)
    if end_date:
        shipments = shipments.filter(created_at__date__lte=end_date)
    if status:
        shipments = shipments.filter(status=status)
    if payment_status:
        shipments = shipments.filter(payment_status=payment_status)
    
    # Calculate statistics
    total_shipments = shipments.count()
    total_revenue = shipments.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    avg_shipment_value = shipments.aggregate(Avg('total_cost'))['total_cost__avg'] or 0
    
    # Group by date for chart
    shipments_by_date = shipments.extra(
        {'created_date': "date(created_at)"}
    ).values('created_date').annotate(
        count=Count('id'),
        revenue=Sum('total_cost')
    ).order_by('created_date')
    
    # Prepare chart data
    dates = [item['created_date'].strftime('%Y-%m-%d') for item in shipments_by_date]
    counts = [item['count'] for item in shipments_by_date]
    revenues = [float(item['revenue']) for item in shipments_by_date]
    
    context = {
        'total_shipments': total_shipments,
        'total_revenue': total_revenue,
        'avg_shipment_value': avg_shipment_value,
        'dates_json': json.dumps(dates),
        'counts_json': json.dumps(counts),
        'revenues_json': json.dumps(revenues),
        'shipments': shipments[:100],  # Limit for display
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'status': status,
            'payment_status': payment_status,
        }
    }
    
    return render(request, 'reports/shipment_reports.html', context)

@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def financial_reports(request):
    """Financial reports"""
    
    # Get payments data
    payments = Payment.objects.filter(status='completed')
    
    # Monthly revenue
    monthly_revenue = payments.extra(
        {'month': "date_trunc('month', created_at)"}
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    # Payment method distribution
    payment_methods = payments.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    # Prepare chart data
    months = [item['month'].strftime('%Y-%m') for item in monthly_revenue]
    revenues = [float(item['total']) for item in monthly_revenue]
    
    context = {
        'monthly_revenue': monthly_revenue,
        'payment_methods': payment_methods,
        'months_json': json.dumps(months),
        'revenues_json': json.dumps(revenues),
        'total_revenue': payments.aggregate(Sum('amount'))['amount__sum'] or 0,
        'avg_payment': payments.aggregate(Avg('amount'))['amount__avg'] or 0,
    }
    
    return render(request, 'reports/financial_reports.html', context)

@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def export_reports(request, report_type):
    """Export reports in various formats"""
    
    if report_type == 'shipments':
        # Export shipments report
        pass
    elif report_type == 'financial':
        # Export financial report
        pass
    elif report_type == 'customers':
        # Export customers report
        pass
    
    # This would typically generate PDF, Excel, or CSV files
    return HttpResponse("Export functionality to be implemented")