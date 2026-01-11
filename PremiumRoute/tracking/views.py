from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from shipping.models import Shipment, ShipmentHistory
from consignment.models import Consignment, ConsignmentHistory

def track_shipment(request, tracking_number=None):
    """Public tracking page"""
    context = {}
    
    if request.method == 'POST':
        tracking_number = request.POST.get('tracking_number', '').strip()
        return redirect('track_shipment', tracking_number=tracking_number)
    
    if tracking_number:
        # Try to find shipment
        shipment = Shipment.objects.filter(tracking_number=tracking_number).first()
        if shipment:
            history = shipment.history.all().order_by('-created_at')
            context.update({
                'type': 'shipment',
                'object': shipment,
                'history': history,
            })
        else:
            # Try to find consignment
            consignment = Consignment.objects.filter(consignment_number=tracking_number).first()
            if consignment:
                history = consignment.history.all().order_by('-created_at')
                context.update({
                    'type': 'consignment',
                    'object': consignment,
                    'history': history,
                })
            else:
                context['error'] = 'Tracking number not found'
    
    return render(request, 'tracking/track.html', context)

def tracking_api(request, tracking_number):
    """API endpoint for tracking"""
    try:
        # Try shipment first
        shipment = Shipment.objects.get(tracking_number=tracking_number)
        history = shipment.history.all().order_by('-created_at')
        
        data = {
            'success': True,
            'type': 'shipment',
            'tracking_number': shipment.tracking_number,
            'status': shipment.status,
            'sender': shipment.sender_name,
            'receiver': shipment.receiver_name,
            'estimated_delivery': shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None,
            'history': [
                {
                    'status': h.status,
                    'location': h.location,
                    'description': h.description,
                    'timestamp': h.created_at.isoformat(),
                }
                for h in history
            ]
        }
        
        return JsonResponse(data)
    
    except Shipment.DoesNotExist:
        try:
            # Try consignment
            consignment = Consignment.objects.get(consignment_number=tracking_number)
            history = consignment.history.all().order_by('-created_at')
            
            data = {
                'success': True,
                'type': 'consignment',
                'tracking_number': consignment.consignment_number,
                'status': consignment.status,
                'shipper': consignment.shipper_name,
                'consignee': consignment.consignee_name,
                'estimated_arrival': consignment.arrival_date.isoformat() if consignment.arrival_date else None,
                'history': [
                    {
                        'status': h.status,
                        'location': h.location,
                        'description': h.description,
                        'timestamp': h.created_at.isoformat(),
                    }
                    for h in history
                ]
            }
            
            return JsonResponse(data)
        
        except Consignment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Tracking number not found'
            }, status=404)

@csrf_exempt
def webhook_update(request):
    """Webhook for external tracking updates"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tracking_number = data.get('tracking_number')
            status = data.get('status')
            location = data.get('location', '')
            description = data.get('description', '')
            
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
                
                return JsonResponse({'success': True})
            
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
                
                return JsonResponse({'success': True})
            
            return JsonResponse({'success': False, 'error': 'Tracking number not found'}, status=404)
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)