from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
import json
from .models import Shipment, ShippingRate, ShipmentHistory, Package
from .forms import ShipmentForm, ShippingRateForm, PackageForm
from .utils import calculate_shipping_cost

@login_required
def create_shipment(request):
    if request.method == 'POST':
        form = ShipmentForm(request.POST)
        if form.is_valid():
            shipment = form.save(commit=False)
            shipment.user = request.user
            shipment.created_by = request.user
            
            # Calculate shipping cost
            shipping_cost = calculate_shipping_cost(
                shipment.weight,
                shipment.shipping_method,
                shipment.sender_country,
                shipment.receiver_country
            )
            shipment.shipping_cost = shipping_cost
            
            # Calculate total cost
            shipment.total_cost = shipping_cost + shipment.insurance_cost + shipment.tax
            
            shipment.save()
            
            # Create initial history
            ShipmentHistory.objects.create(
                shipment=shipment,
                status='pending',
                description='Shipment created successfully'
            )
            
            messages.success(request, f'Shipment created successfully! Tracking Number: {shipment.tracking_number}')
            return redirect('shipment_detail', tracking_number=shipment.tracking_number)
    else:
        form = ShipmentForm()
    
    return render(request, 'shipping/create_shipment.html', {'form': form})

@login_required
def shipment_list(request):
    shipments = Shipment.objects.filter(user=request.user).order_by('-created_at')
    
    # Filtering
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if status:
        shipments = shipments.filter(status=status)
    
    if search:
        shipments = shipments.filter(
            Q(tracking_number__icontains=search) |
            Q(receiver_name__icontains=search) |
            Q(sender_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(shipments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'shipping/shipment_list.html', {
        'page_obj': page_obj,
        'status': status,
        'search': search,
    })

@login_required
def shipment_detail(request, tracking_number):
    shipment = get_object_or_404(Shipment, tracking_number=tracking_number, user=request.user)
    packages = shipment.packages.all()
    history = shipment.history.all().order_by('-created_at')
    
    return render(request, 'shipping/shipment_detail.html', {
        'shipment': shipment,
        'packages': packages,
        'history': history,
    })

@login_required
def update_shipment_status(request, tracking_number):
    shipment = get_object_or_404(Shipment, tracking_number=tracking_number)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        location = request.POST.get('location', '')
        description = request.POST.get('description', '')
        
        if new_status and new_status != shipment.status:
            shipment.status = new_status
            shipment.save()
            
            # Create history entry
            ShipmentHistory.objects.create(
                shipment=shipment,
                status=new_status,
                location=location,
                description=description,
                created_by=request.user
            )
            
            messages.success(request, f'Shipment status updated to {new_status}')
    
    return redirect('shipment_detail', tracking_number=tracking_number)

@login_required
def shipping_rates(request):
    rates = ShippingRate.objects.filter(is_active=True)
    
    # Filter by service type and zone
    service_type = request.GET.get('service_type')
    zone = request.GET.get('zone')
    
    if service_type:
        rates = rates.filter(service_type=service_type)
    if zone:
        rates = rates.filter(zone=zone)
    
    return render(request, 'shipping/shipping_rates.html', {
        'rates': rates,
    })

@login_required
def calculate_rate(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            weight = float(data.get('weight', 0))
            service_type = data.get('service_type', 'standard')
            from_country = data.get('from_country', '')
            to_country = data.get('to_country', '')
            
            rate = calculate_shipping_cost(weight, service_type, from_country, to_country)
            
            return JsonResponse({
                'success': True,
                'rate': str(rate),
                'currency': 'USD'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# Admin views for shipping management
@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def admin_shipment_list(request):
    shipments = Shipment.objects.all().order_by('-created_at')
    
    # Advanced filtering
    status = request.GET.get('status')
    payment_status = request.GET.get('payment_status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')
    
    if status:
        shipments = shipments.filter(status=status)
    if payment_status:
        shipments = shipments.filter(payment_status=payment_status)
    if date_from:
        shipments = shipments.filter(created_at__date__gte=date_from)
    if date_to:
        shipments = shipments.filter(created_at__date__lte=date_to)
    if search:
        shipments = shipments.filter(
            Q(tracking_number__icontains=search) |
            Q(receiver_name__icontains=search) |
            Q(sender_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Statistics
    total_shipments = shipments.count()
    total_revenue = shipments.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    
    # Pagination
    paginator = Paginator(shipments, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'shipping/admin_shipment_list.html', {
        'page_obj': page_obj,
        'total_shipments': total_shipments,
        'total_revenue': total_revenue,
        'filters': {
            'status': status,
            'payment_status': payment_status,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    })

@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def admin_shipment_detail(request, tracking_number):
    shipment = get_object_or_404(Shipment, tracking_number=tracking_number)
    packages = shipment.packages.all()
    history = shipment.history.all().order_by('-created_at')
    
    return render(request, 'shipping/admin_shipment_detail.html', {
        'shipment': shipment,
        'packages': packages,
        'history': history,
    })

@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def manage_shipping_rates(request):
    rates = ShippingRate.objects.all().order_by('zone', 'service_type')
    
    if request.method == 'POST':
        form = ShippingRateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Shipping rate added successfully!')
            return redirect('manage_shipping_rates')
    else:
        form = ShippingRateForm()
    
    return render(request, 'shipping/manage_rates.html', {
        'rates': rates,
        'form': form,
    })

@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
@require_POST
def toggle_shipping_rate(request, rate_id):
    rate = get_object_or_404(ShippingRate, id=rate_id)
    rate.is_active = not rate.is_active
    rate.save()
    
    return JsonResponse({
        'success': True,
        'is_active': rate.is_active
    })