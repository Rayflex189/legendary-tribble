from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

class ShippingRate(models.Model):
    """Shipping rates based on weight, dimensions, and destination"""
    
    ZONE_CHOICES = (
        ('local', 'Local'),
        ('national', 'National'),
        ('international', 'International'),
    )
    
    SERVICE_CHOICES = (
        ('standard', 'Standard Delivery'),
        ('express', 'Express Delivery'),
        ('same_day', 'Same Day Delivery'),
        ('overnight', 'Overnight Delivery'),
    )
    
    name = models.CharField(max_length=100)
    service_type = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    zone = models.CharField(max_length=50, choices=ZONE_CHOICES)
    min_weight = models.DecimalField(max_digits=10, decimal_places=2, help_text='Minimum weight in kg')
    max_weight = models.DecimalField(max_digits=10, decimal_places=2, help_text='Maximum weight in kg')
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    additional_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_days = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.service_type} ({self.zone})"
    
    class Meta:
        ordering = ['zone', 'service_type', 'min_weight']

class Shipment(models.Model):
    """Shipment model for managing shipping orders"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
        ('delayed', 'Delayed'),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    # Basic Information
    tracking_number = models.CharField(max_length=50, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shipments')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Sender Information
    sender_name = models.CharField(max_length=255)
    sender_email = models.EmailField()
    sender_phone = models.CharField(max_length=20)
    sender_address = models.TextField()
    sender_city = models.CharField(max_length=100)
    sender_state = models.CharField(max_length=100)
    sender_country = models.CharField(max_length=100)
    sender_postal_code = models.CharField(max_length=20)
    
    # Receiver Information
    receiver_name = models.CharField(max_length=255)
    receiver_email = models.EmailField()
    receiver_phone = models.CharField(max_length=20)
    receiver_address = models.TextField()
    receiver_city = models.CharField(max_length=100)
    receiver_state = models.CharField(max_length=100)
    receiver_country = models.CharField(max_length=100)
    receiver_postal_code = models.CharField(max_length=20)
    
    # Package Details
    package_description = models.TextField()
    weight = models.DecimalField(max_digits=10, decimal_places=2, help_text='Weight in kg')
    length = models.DecimalField(max_digits=10, decimal_places=2, help_text='Length in cm', blank=True, null=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, help_text='Width in cm', blank=True, null=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, help_text='Height in cm', blank=True, null=True)
    declared_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Declared value for insurance')
    
    # Shipping Details
    shipping_method = models.CharField(max_length=100)
    shipping_rate = models.ForeignKey(ShippingRate, on_delete=models.SET_NULL, null=True, blank=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)
    insurance_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates
    pickup_date = models.DateField(null=True, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateField(null=True, blank=True)
    
    # Additional Information
    special_instructions = models.TextField(blank=True)
    requires_signature = models.BooleanField(default=False)
    fragile = models.BooleanField(default=False)
    hazardous = models.BooleanField(default=False)
    temperature_controlled = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_shipments')
    
    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = self.generate_tracking_number()
        super().save(*args, **kwargs)
    
    def generate_tracking_number(self):
        return f"SH{str(uuid.uuid4().int)[:10].upper()}"
    
    def __str__(self):
        return f"{self.tracking_number} - {self.receiver_name}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tracking_number']),
            models.Index(fields=['status']),
            models.Index(fields=['user']),
        ]

class ShipmentHistory(models.Model):
    """Track shipment status changes"""
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=50)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Shipment Histories'

class Package(models.Model):
    """Individual packages within a shipment"""
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='packages')
    package_number = models.CharField(max_length=50)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    width = models.DecimalField(max_digits=10, decimal_places=2)
    height = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.package_number} - {self.shipment.tracking_number}"
    
    @property
    def volume(self):
        return self.length * self.width * self.height
    
    class Meta:
        ordering = ['package_number']