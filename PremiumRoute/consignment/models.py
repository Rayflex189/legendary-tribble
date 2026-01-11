from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Consignment(models.Model):
    """Consignment model for managing bulk shipments"""
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    )
    
    TYPE_CHOICES = (
        ('import', 'Import'),
        ('export', 'Export'),
        ('domestic', 'Domestic'),
    )
    
    # Basic Information
    consignment_number = models.CharField(max_length=50, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consignments')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    consignment_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    
    # Shipper Information
    shipper_name = models.CharField(max_length=255)
    shipper_address = models.TextField()
    shipper_contact = models.CharField(max_length=100)
    shipper_email = models.EmailField()
    shipper_phone = models.CharField(max_length=20)
    
    # Consignee Information
    consignee_name = models.CharField(max_length=255)
    consignee_address = models.TextField()
    consignee_contact = models.CharField(max_length=100)
    consignee_email = models.EmailField()
    consignee_phone = models.CharField(max_length=20)
    
    # Shipment Details
    origin_port = models.CharField(max_length=100)
    destination_port = models.CharField(max_length=100)
    vessel_flight_no = models.CharField(max_length=100, blank=True)
    departure_date = models.DateField(null=True, blank=True)
    arrival_date = models.DateField(null=True, blank=True)
    
    # Cargo Details
    description_of_goods = models.TextField()
    number_of_packages = models.IntegerField()
    total_weight = models.DecimalField(max_digits=10, decimal_places=2, help_text='Weight in kg')
    total_volume = models.DecimalField(max_digits=10, decimal_places=2, help_text='Volume in cubic meters')
    goods_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Container Information
    container_number = models.CharField(max_length=50, blank=True)
    container_size = models.CharField(max_length=50, blank=True)
    container_type = models.CharField(max_length=50, blank=True)
    seal_number = models.CharField(max_length=50, blank=True)
    
    # Documents
    bill_of_lading = models.CharField(max_length=100, blank=True)
    commercial_invoice = models.FileField(upload_to='consignment/documents/', blank=True, null=True)
    packing_list = models.FileField(upload_to='consignment/documents/', blank=True, null=True)
    certificate_of_origin = models.FileField(upload_to='consignment/documents/', blank=True, null=True)
    insurance_certificate = models.FileField(upload_to='consignment/documents/', blank=True, null=True)
    
    # Financial Information
    freight_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    handling_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    insurance_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    customs_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Additional Information
    special_instructions = models.TextField(blank=True)
    hazardous_materials = models.BooleanField(default=False)
    temperature_control = models.BooleanField(default=False)
    customs_cleared = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_consignments')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.consignment_number:
            self.consignment_number = self.generate_consignment_number()
        
        # Calculate total charges
        self.total_charges = (
            self.freight_charges +
            self.handling_charges +
            self.insurance_charges +
            self.customs_charges +
            self.other_charges
        )
        
        super().save(*args, **kwargs)
    
    def generate_consignment_number(self):
        return f"CN{str(uuid.uuid4().int)[:12].upper()}"
    
    def __str__(self):
        return f"{self.consignment_number} - {self.consignee_name}"
    
    class Meta:
        ordering = ['-created_at']

class ConsignmentItem(models.Model):
    """Individual items within a consignment"""
    consignment = models.ForeignKey(Consignment, on_delete=models.CASCADE, related_name='items')
    item_description = models.TextField()
    quantity = models.IntegerField()
    unit = models.CharField(max_length=50)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.DecimalField(max_digits=10, decimal_places=2)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    hs_code = models.CharField(max_length=20, blank=True)
    country_of_origin = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.item_description[:50]} - {self.quantity} {self.unit}"
    
    class Meta:
        ordering = ['id']

class ConsignmentHistory(models.Model):
    """Track consignment status changes"""
    consignment = models.ForeignKey(Consignment, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=50)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    document = models.FileField(upload_to='consignment/history/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.consignment.consignment_number} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Consignment Histories'

class CustomsDeclaration(models.Model):
    """Customs declaration for consignments"""
    consignment = models.OneToOneField(Consignment, on_delete=models.CASCADE, related_name='customs_declaration')
    declaration_number = models.CharField(max_length=100, unique=True)
    declared_value = models.DecimalField(max_digits=15, decimal_places=2)
    duty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    clearance_date = models.DateField(null=True, blank=True)
    clearance_status = models.CharField(max_length=50, default='pending')
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Customs Declaration: {self.declaration_number}"