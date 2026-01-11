from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import User, UserProfile, AuditLog
from .forms import (
    UserRegistrationForm, 
    UserLoginForm, 
    UserProfileForm, 
    ExtendedProfileForm,
    PasswordChangeFormCustom
)
from .decorators import unauthenticated_user, allowed_users, admin_only

@unauthenticated_user
def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action='create',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'action': 'User registration'}
            )
            
            messages.success(request, 'Registration successful! Welcome to our shipping platform.')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

@unauthenticated_user
def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                login(request, user)
                
                # Create audit log
                AuditLog.objects.create(
                    user=user,
                    action='login',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={'action': 'User login'}
                )
                
                messages.success(request, f'Welcome back, {user.first_name}!')
                
                # Redirect based on user type
                if user.user_type == 'admin':
                    return redirect('admin_dashboard')
                elif user.user_type == 'staff':
                    return redirect('staff_dashboard')
                else:
                    return redirect('dashboard')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    # Create audit log before logout
    AuditLog.objects.create(
        user=request.user,
        action='logout',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        details={'action': 'User logout'}
    )
    
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def dashboard_view(request):
    context = {}
    
    if request.user.user_type == 'customer':
        # Customer dashboard
        from shipping.models import Shipment
        from consignment.models import Consignment
        
        shipments = Shipment.objects.filter(user=request.user).order_by('-created_at')[:5]
        consignments = Consignment.objects.filter(user=request.user).order_by('-created_at')[:5]
        
        context.update({
            'shipments': shipments,
            'consignments': consignments,
            'total_shipments': Shipment.objects.filter(user=request.user).count(),
            'pending_shipments': Shipment.objects.filter(user=request.user, status='pending').count(),
        })
    
    return render(request, 'accounts/dashboard.html', context)

@login_required
def profile_view(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=user)
        profile_form = ExtendedProfileForm(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action='profile_update',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'action': 'Profile updated'}
            )
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        user_form = UserProfileForm(instance=user)
        profile_form = ExtendedProfileForm(instance=profile)
    
    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeFormCustom(request.user, request.POST)
        if form.is_valid():
            user = request.user
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            update_session_auth_hash(request, user)
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action='password_change',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'action': 'Password changed'}
            )
            
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
    else:
        form = PasswordChangeFormCustom(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

# Admin views
@login_required
@admin_only
def admin_dashboard_view(request):
    from django.db.models import Count
    from shipping.models import Shipment
    from consignment.models import Consignment
    
    # Statistics
    total_users = User.objects.count()
    total_shipments = Shipment.objects.count()
    total_consignments = Consignment.objects.count()
    
    # Recent activities
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_shipments = Shipment.objects.order_by('-created_at')[:10]
    recent_audit_logs = AuditLog.objects.order_by('-timestamp')[:20]
    
    # User statistics by type
    user_stats = User.objects.values('user_type').annotate(count=Count('user_type'))
    
    context = {
        'total_users': total_users,
        'total_shipments': total_shipments,
        'total_consignments': total_consignments,
        'recent_users': recent_users,
        'recent_shipments': recent_shipments,
        'recent_audit_logs': recent_audit_logs,
        'user_stats': user_stats,
    }
    
    return render(request, 'accounts/admin_dashboard.html', context)

@login_required
@admin_only
def user_management_view(request):
    users = User.objects.all().order_by('-date_joined')
    
    # Search and filter
    search_query = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')
    
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    if user_type:
        users = users.filter(user_type=user_type)
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/user_management.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'user_type': user_type,
    })

@login_required
@admin_only
def user_detail_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(UserProfile, user=user)
    
    # Get user activities
    activities = AuditLog.objects.filter(user=user).order_by('-timestamp')[:50]
    
    # Get user shipments and consignments
    from shipping.models import Shipment
    from consignment.models import Consignment
    
    shipments = Shipment.objects.filter(user=user).order_by('-created_at')[:10]
    consignments = Consignment.objects.filter(user=user).order_by('-created_at')[:10]
    
    if request.method == 'POST':
        # Handle user status update
        if 'toggle_active' in request.POST:
            user.is_active = not user.is_active
            user.save()
            messages.success(request, f'User {"activated" if user.is_active else "deactivated"} successfully!')
            return redirect('user_detail', user_id=user_id)
        
        # Handle user type update
        elif 'user_type' in request.POST:
            user.user_type = request.POST['user_type']
            user.save()
            messages.success(request, 'User type updated successfully!')
            return redirect('user_detail', user_id=user_id)
    
    return render(request, 'accounts/user_detail.html', {
        'user': user,
        'profile': profile,
        'activities': activities,
        'shipments': shipments,
        'consignments': consignments,
    })

@login_required
@admin_only
def audit_logs_view(request):
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    # Filtering
    user_id = request.GET.get('user_id')
    action = request.GET.get('action')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action:
        logs = logs.filter(action=action)
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/audit_logs.html', {
        'page_obj': page_obj,
    })