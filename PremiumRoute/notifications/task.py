from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_shipment_created_email(shipment_id):
    """Send email when shipment is created"""
    from shipping.models import Shipment
    
    try:
        shipment = Shipment.objects.get(id=shipment_id)
        
        subject = f"Shipment Created - Tracking Number: {shipment.tracking_number}"
        context = {
            'shipment': shipment,
            'user': shipment.user,
        }
        
        # HTML content
        html_content = render_to_string('emails/shipment_created.html', context)
        
        # Plain text content
        text_content = render_to_string('emails/shipment_created.txt', context)
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[shipment.user.email, shipment.sender_email, shipment.receiver_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"Shipment created email sent for {shipment.tracking_number}")
        
    except Exception as e:
        logger.error(f"Error sending shipment created email: {str(e)}")

@shared_task
def send_status_update_email(shipment_id, old_status, new_status):
    """Send email when shipment status changes"""
    from shipping.models import Shipment
    
    try:
        shipment = Shipment.objects.get(id=shipment_id)
        
        subject = f"Shipment Status Update - {shipment.tracking_number}"
        context = {
            'shipment': shipment,
            'old_status': old_status,
            'new_status': new_status,
        }
        
        html_content = render_to_string('emails/status_update.html', context)
        text_content = render_to_string('emails/status_update.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[shipment.user.email, shipment.receiver_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"Status update email sent for {shipment.tracking_number}")
        
    except Exception as e:
        logger.error(f"Error sending status update email: {str(e)}")

@shared_task
def send_sms_notification(phone_number, message):
    """Send SMS notification"""
    try:
        # Configure Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        logger.info(f"SMS sent to {phone_number}: {message.sid}")
        
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")

@shared_task
def send_daily_summary():
    """Send daily summary to admin"""
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Sum
    from shipping.models import Shipment
    
    User = get_user_model()
    
    try:
        # Get admin users
        admin_users = User.objects.filter(user_type='admin', is_active=True)
        
        # Get statistics for the day
        from datetime import date, timedelta
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        shipments_today = Shipment.objects.filter(created_at__date=today).count()
        shipments_yesterday = Shipment.objects.filter(created_at__date=yesterday).count()
        
        revenue_today = Shipment.objects.filter(
            created_at__date=today, 
            payment_status='paid'
        ).aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        
        # Calculate percentage change
        if shipments_yesterday > 0:
            shipment_change = ((shipments_today - shipments_yesterday) / shipments_yesterday) * 100
        else:
            shipment_change = 100 if shipments_today > 0 else 0
        
        context = {
            'date': today,
            'shipments_today': shipments_today,
            'shipments_yesterday': shipments_yesterday,
            'shipment_change': shipment_change,
            'revenue_today': revenue_today,
            'pending_shipments': Shipment.objects.filter(status='pending').count(),
            'in_transit_shipments': Shipment.objects.filter(status='in_transit').count(),
        }
        
        html_content = render_to_string('emails/daily_summary.html', context)
        text_content = render_to_string('emails/daily_summary.txt', context)
        
        # Send to all admin users
        for admin in admin_users:
            email = EmailMultiAlternatives(
                subject=f"Daily Summary Report - {today}",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[admin.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
        
        logger.info("Daily summary emails sent to admin users")
        
    except Exception as e:
        logger.error(f"Error sending daily summary: {str(e)}")