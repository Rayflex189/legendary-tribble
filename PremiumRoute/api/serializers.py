from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from shipping.models import Shipment, ShippingRate, ShipmentHistory
from consignment.models import Consignment, ConsignmentHistory
from payments.models import Payment, Invoice
from accounts.models import UserProfile

User = get_user_model()

# User Serializers
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'password', 'password2')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 
                  'user_type', 'is_active', 'date_joined', 'last_login')
        read_only_fields = ('id', 'user_type', 'is_active', 'date_joined', 'last_login')

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = '__all__'

# Shipping Serializers
class ShipmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        exclude = ('user', 'created_by', 'tracking_number', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        # Calculate shipping cost (simplified)
        validated_data['shipping_cost'] = 10.0  # Base rate
        validated_data['total_cost'] = validated_data['shipping_cost']
        return super().create(validated_data)

class ShipmentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    shipping_rate = serializers.StringRelatedField()
    
    class Meta:
        model = Shipment
        fields = '__all__'
        read_only_fields = ('tracking_number', 'created_at', 'updated_at', 'created_by')

class ShipmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = ('status',)

class ShippingRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingRate
        fields = '__all__'

# Consignment Serializers
class ConsignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consignment
        exclude = ('user', 'consignment_number', 'created_at', 'updated_at', 
                   'approved_by', 'approved_at')
    
    def create(self, validated_data):
        # Calculate total charges
        validated_data['total_charges'] = (
            validated_data.get('freight_charges', 0) +
            validated_data.get('handling_charges', 0) +
            validated_data.get('insurance_charges', 0) +
            validated_data.get('customs_charges', 0) +
            validated_data.get('other_charges', 0)
        )
        return super().create(validated_data)

class ConsignmentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Consignment
        fields = '__all__'
        read_only_fields = ('consignment_number', 'created_at', 'updated_at', 
                            'approved_by', 'approved_at')

# Payment Serializers
class PaymentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    shipment = ShipmentSerializer(read_only