from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from .models import (
    Item, StockTransaction, Borrowing, ActivityLog, Task, TaskItem,
    RestockAlert, ConsumptionAnalytics, SupplyConsumptionCycle,
    LogisticsAnalytics, Notification
)
from django.db.models import F, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from .ai_analytics import AIAnalyticsEngine
import json
import csv
import datetime
from django.utils import timezone

def notification_context(request):
    """Global context processor for notifications (referenced in settings.py TEMPLATES)."""
    return {'notifications': []}

def log_activity(user, action, description):
    ActivityLog.objects.create(user=user, action=action, description=description)

def is_admin(user):
    return user.is_authenticated and user.is_superuser

def is_staff(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
def dashboard(request):
    """Real-time operational dashboard with AI-powered insights."""
    total_items = Item.objects.count()
    low_stock_items = Item.objects.filter(status='Low Stock').count()
    out_of_stock = Item.objects.filter(status='Out of Stock').count()
    borrowed_units = Borrowing.objects.filter(status='Pending').aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    # Recent activity for timeline
    recent_logs = ActivityLog.objects.all().order_by('-timestamp')[:10]
    
    # Chart Data: Category Distribution
    category_data = Item.objects.values('category').annotate(count=Count('id'))
    cons_pie_labels = [entry['category'] for entry in category_data]
    cons_pie_values = [entry['count'] for entry in category_data]

    # Forecast/Trend Data (Simplified for production look)
    # Using last 7 days of stock transactions
    seven_days_ago = timezone.now() - datetime.timedelta(days=7)
    trends = StockTransaction.objects.filter(timestamp__gte=seven_days_ago).annotate(date=TruncDate('timestamp')).values('date').annotate(total=Sum('quantity')).order_by('date')
    
    actual_labels = []
    actual_values = []
    for i in range(7, -1, -1):
        d = timezone.now().date() - datetime.timedelta(days=i)
        actual_labels.append(d.strftime('%b %d'))
        val = next((entry['total'] for entry in trends if entry['date'] == d), 0)
        actual_values.append(float(val))
    
    # AI ANALYTICS SECTION
    # Get AI-generated restock alerts
    critical_alerts = RestockAlert.objects.filter(
        status='ACTIVE',
        severity__in=['CRITICAL', 'HIGH']
    ).order_by('-alert_generated_at')[:5]
    
    # Get most consumed consumable items this week
    most_consumed = AIAnalyticsEngine.get_top_consumed_items(limit=5)
    
    # Get most borrowed items
    most_borrowed = AIAnalyticsEngine.get_most_borrowed_items(limit=5)
    
    # Get latest consumption analytics for dashboard
    week_start = timezone.now().date() - datetime.timedelta(days=timezone.now().weekday())
    consumption_data = ConsumptionAnalytics.objects.filter(
        week_start=week_start
    ).order_by('-total_movement')[:5]
    
    # Get latest logistics analytics
    latest_logistics = LogisticsAnalytics.objects.order_by('-month_year').first()
    
    # Get system notifications
    unread_notifications = Notification.objects.filter(
        is_read=False,
        action_required=True
    )[:5]

    context = {
        'total_items': total_items,
        'low_stock_items': low_stock_items,
        'out_of_stock': out_of_stock,
        'borrowed_equipment': borrowed_units,
        'recent_logs': recent_logs,
        'items_summary': Item.objects.filter(status__in=['Low Stock', 'Out of Stock']).order_by('quantity')[:5],
        'cons_pie_labels': json.dumps(cons_pie_labels),
        'cons_pie_values': json.dumps(cons_pie_values),
        'actual_labels': json.dumps(actual_labels),
        'actual_values': json.dumps(actual_values),
        'forecast_values': json.dumps([v * 1.1 for v in actual_values]), # Mock projection
        'pending_count': Task.objects.filter(status='Pending').count(),
        'avg_daily_usage': round(sum(actual_values)/8, 2) if actual_values else 0,
        'top_item_name': Item.objects.order_by('-quantity').first().name if Item.objects.exists() else "None",
        # AI Analytics Data
        'critical_alerts': critical_alerts,
        'alerts_count': RestockAlert.objects.filter(status='ACTIVE').count(),
        'most_consumed_items': most_consumed,
        'most_borrowed_items': most_borrowed,
        'consumption_analytics': consumption_data,
        'latest_logistics': latest_logistics,
        'unread_notifications': unread_notifications,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def item_detail(request, pk):
    """Structured item detail page with full action history."""
    item = get_object_or_404(Item, id=pk)
    transactions = StockTransaction.objects.filter(item=item).order_by('-timestamp')[:10]
    active_borrowings = Borrowing.objects.filter(item=item, status='Pending').order_by('-date_borrowed')
    
    context = {
        'item': item,
        'transactions': transactions,
        'active_borrowings': active_borrowings,
    }
    return render(request, 'core/item_detail.html', context)

@login_required
@user_passes_test(is_admin)
def qr_generator(request):
    """Admin feature to generate printable QR asset tags."""
    items = Item.objects.all().order_by('name')
    return render(request, 'core/qr_generate.html', {'items': items})

@login_required
def inventory(request):
    """Full CRUD Inventory Registry."""
    items = Item.objects.all().order_by('name')
    q = request.GET.get('q')
    if q:
        items = items.filter(Q(name__icontains=q) | Q(barcode__icontains=q))
    
    cat = request.GET.get('category')
    if cat:
        items = items.filter(category=cat)
        
    stat = request.GET.get('status')
    if stat:
        items = items.filter(status=stat)
        
    return render(request, 'core/inventory.html', {'items': items})

@login_required
@user_passes_test(is_staff)
def add_item(request):
    """Custom view to register a new resource."""
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        description = request.POST.get('description', '')
        quantity = int(request.POST.get('quantity', 0))
        low_stock_threshold = int(request.POST.get('low_stock_threshold', 5))
        max_capacity_value = request.POST.get('max_capacity', '').strip()
        max_capacity = int(max_capacity_value) if max_capacity_value.isdigit() else None
        
        item = Item.objects.create(
            name=name,
            category=category,
            description=description,
            quantity=quantity,
            low_stock_threshold=low_stock_threshold,
            max_capacity=max_capacity
        )
        log_activity(request.user, "Resource Registered", f"Added {quantity}x {item.name} ({item.category})")
        return redirect('inventory')
    return redirect('inventory')

@login_required
@user_passes_test(is_staff)
def stock_management(request):
    """Handle stock adjustments."""
    error_message = None
    selected_item_id = None
    selected_type = None
    entered_quantity = None

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        t_type = request.POST.get('type')
        qty = int(request.POST.get('quantity', 0))
        remarks = request.POST.get('remarks', '')

        selected_item_id = item_id
        selected_type = t_type
        entered_quantity = qty

        item = get_object_or_404(Item, id=item_id)

        if qty <= 0:
            error_message = 'Quantity must be a positive number.'
        elif t_type == 'OUT' and item.quantity < qty:
            error_message = 'Insufficient stock for this item.'
        elif t_type == 'IN' and item.available_in_quantity is not None and qty > item.available_in_quantity:
            error_message = f'Cannot add more than {item.available_in_quantity} units for {item.name} to stay within maximum capacity.'

        if not error_message:
            StockTransaction.objects.create(
                item=item, type=t_type, quantity=qty,
                remarks=remarks, user=request.user
            )

            if t_type == 'IN':
                item.quantity += qty
            else:
                item.quantity -= qty
            item.save()

            log_activity(request.user, f"Stock {t_type}", f"Adjusted {item.name} by {qty} units. Remarks: {remarks}")
            return redirect('item_detail', pk=item.id)

    items = Item.objects.all()
    transactions = StockTransaction.objects.all().order_by('-timestamp')[:20]
    context = {
        'items': items,
        'transactions': transactions,
        'error_message': error_message,
        'selected_item_id': selected_item_id,
        'selected_type': selected_type,
        'entered_quantity': entered_quantity,
    }
    return render(request, 'core/stock_manage.html', context)

@login_required
@user_passes_test(is_staff)
def borrowing_system(request):
    """Handle asset borrowing and returns."""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'borrow':
            item_id = request.POST.get('item_id')
            borrower = request.POST.get('borrower_name')
            qty = int(request.POST.get('quantity', 1))
            
            item = get_object_or_404(Item, id=item_id)
            if item.quantity < qty:
                return JsonResponse({'status': 'error', 'message': 'Insufficient items available'})
            
            Borrowing.objects.create(
                item=item, borrower_name=borrower, quantity=qty
            )
            item.quantity -= qty
            item.save()
            log_activity(request.user, "Asset Borrowed", f"Authorized {qty}x {item.name} to {borrower}")
            return redirect('item_detail', pk=item.id)
            
        elif action == 'return':
            borrow_id = request.POST.get('borrow_id')
            borrow_record = get_object_or_404(Borrowing, id=borrow_id)
            
            if borrow_record.status == 'Pending':
                borrow_record.status = 'Returned'
                borrow_record.return_date = timezone.now()
                borrow_record.save()
                
                # Update Inventory
                item = borrow_record.item
                item.quantity += borrow_record.quantity
                item.save()
                
                log_activity(request.user, "Asset Returned", f"Processed return of {borrow_record.quantity}x {item.name} from {borrow_record.borrower_name}")
            
            return redirect('item_detail', pk=borrow_record.item.id)

    borrowings = Borrowing.objects.all().order_by('-date_borrowed')
    items = Item.objects.filter(quantity__gt=0).exclude(category__in=['Consumable', 'Medical'])
    return render(request, 'core/borrowing.html', {'borrowings': borrowings, 'items': items})

@login_required
def scanner(request):
    """Render the QR code scanner page."""
    return render(request, 'core/scanner.html')

@login_required
def item_detail(request, pk):
    """Structured item detail page with full action history."""
    item = get_object_or_404(Item, id=pk)
    transactions = StockTransaction.objects.filter(item=item).order_by('-timestamp')[:5]
    borrowings = Borrowing.objects.filter(item=item).order_by('-date_borrowed')[:5]
    
    context = {
        'item': item,
        'transactions': transactions,
        'borrowings': borrowings,
    }
    return render(request, 'core/item_detail.html', context)

@login_required
@user_passes_test(is_admin)
def qr_generator(request):
    """Admin feature to generate printable QR asset tags."""
    items = Item.objects.all().order_by('name')
    return render(request, 'core/qr_generate.html', {'items': items})

@csrf_exempt
def scan_barcode(request):
    """AJAX endpoint to identify item by structured QR payload or simple barcode."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            raw_code = data.get('barcode', '')
            
            # Handle structured format: Code|Name|Category|ID
            item = None
            if "|" in raw_code:
                parts = raw_code.split("|")
                if len(parts) >= 4:
                    item_id = parts[3]
                    item = Item.objects.filter(id=item_id).first()
            
            # Fallback to simple barcode match
            if not item:
                item = Item.objects.filter(Q(barcode=raw_code) | Q(item_code=raw_code)).first()
            
            if item:
                return JsonResponse({
                    'status': 'success',
                    'item': {
                        'id': item.id,
                        'name': item.name,
                        'item_code': item.item_code,
                        'quantity': item.quantity,
                        'status': item.status,
                        'category': item.category,
                        'detail_url': f"/item/{item.id}/"
                    }
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Asset not identified in registry.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@csrf_exempt
@login_required
def api_item_action(request):
    """Unified API for scanner actions."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            action = data.get('action') # 'in', 'out', 'borrow', 'return'
            qty = int(data.get('quantity', 1))
            
            item = get_object_or_404(Item, id=item_id)
            
            if action == 'in':
                item.quantity += qty
                StockTransaction.objects.create(item=item, type='IN', quantity=qty, user=request.user, remarks="Scanner Stock In")
                log_activity(request.user, "Stock In", f"Added {qty}x {item.name} via scanner")
            elif action == 'out':
                if item.quantity < qty:
                    return JsonResponse({'status': 'error', 'message': 'Insufficient stock'})
                item.quantity -= qty
                StockTransaction.objects.create(item=item, type='OUT', quantity=qty, user=request.user, remarks="Scanner Stock Out")
                log_activity(request.user, "Stock Out", f"Removed {qty}x {item.name} via scanner")
            elif action == 'borrow':
                if item.quantity < qty:
                    return JsonResponse({'status': 'error', 'message': 'Insufficient stock'})
                item.quantity -= qty
                Borrowing.objects.create(item=item, borrower_name=f"Scanner Session ({request.user.username})", quantity=qty)
                log_activity(request.user, "Borrow", f"Borrowed {qty}x {item.name} via scanner")
            elif action == 'return':
                borrow_record = Borrowing.objects.filter(item=item, status='Pending').last()
                if borrow_record:
                    borrow_record.status = 'Returned'
                    borrow_record.return_date = timezone.now()
                    borrow_record.save()
                    item.quantity += borrow_record.quantity
                    log_activity(request.user, "Return", f"Returned {borrow_record.quantity}x {item.name} via scanner")
                else:
                    return JsonResponse({'status': 'error', 'message': 'No active borrowing record found'})
            
            item.save()
            return JsonResponse({'status': 'success', 'message': f'Action {action} completed', 'new_quantity': item.quantity})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def kanban(request):
    """Deployment Pipeline."""
    tasks = Task.objects.all().order_by('-created_at')
    context = {
        'pending': tasks.filter(status='Pending'),
        'approved': tasks.filter(status='Approved'),
        'in_use': tasks.filter(status='In Use'),
        'completed': tasks.filter(status='Completed'),
    }
    return render(request, 'core/kanban.html', context)

@login_required
@user_passes_test(is_staff)
def add_task(request):
    """Custom view to create a new deployment task."""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        created_by = request.POST.get('created_by', request.user.username)
        
        Task.objects.create(
            title=title,
            description=description,
            created_by=created_by,
            status='Pending'
        )
        log_activity(request.user, "Task Created", f"New deployment request: {title}")
    return redirect('kanban')

@csrf_exempt
@login_required
def update_task_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            new_status = data.get('status')
            task = get_object_or_404(Task, id=task_id)
            old_status = task.status
            task.status = new_status
            task.save()
            log_activity(request.user, "Task Update", f"Moved task '{task.title}' from {old_status} to {new_status}")
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def analytics(request):
    """Advanced Analytics View."""
    return render(request, 'core/analytics.html')

@login_required
def activity_logs(request):
    """System Audit Trail."""
    logs = ActivityLog.objects.all().order_by('-timestamp')
    return render(request, 'core/activity.html', {'logs': logs})

@login_required
@user_passes_test(is_admin)
def clear_activity_logs(request):
    """Clear all system audit trail logs."""
    if request.method == 'POST':
        ActivityLog.objects.all().delete()
        log_activity(request.user, "Audit Trail Cleared", "Administrator cleared the system audit trail.")
    return redirect('activity_logs')

@login_required
def export_inventory(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
    writer = csv.writer(response)
    writer.writerow(['Barcode', 'Name', 'Category', 'Quantity', 'Status'])
    for item in Item.objects.all():
        writer.writerow([item.barcode, item.name, item.category, item.quantity, item.status])
    return response

@staff_member_required
def user_management(request):
    """Professional user list and management dashboard."""
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'core/users.html', {'users': users})

@staff_member_required
def add_user(request):
    """Custom view to enroll new personnel."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        role = request.POST.get('role', 'Standard')
        
        # Create user
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username=username, email=email, password=password)
            if role == 'Superuser':
                user.is_superuser = True
                user.is_staff = True
            elif role == 'Staff':
                user.is_staff = True
            user.save()
            log_activity(request.user, "Personnel Enrolled", f"Enrolled {username} with {role} access.")
    return redirect('user_management')

@staff_member_required
def settings(request):
    """System configuration and institutional settings terminal."""
    return render(request, 'core/settings.html')

@login_required
def get_notifications(request):
    """API endpoint for header notifications."""
    logs = ActivityLog.objects.all().order_by('-timestamp')[:5]
    data = [{
        'user': log.user.username,
        'action': log.action,
        'details': log.description,
        'time': log.timestamp.strftime("%I:%M %p")
    } for log in logs]
    return JsonResponse({'status': 'success', 'notifications': data})


# AI ANALYTICS ENDPOINTS
@login_required
def ai_alerts(request):
    """View all AI-generated restock alerts."""
    alerts = RestockAlert.objects.all().order_by('-alert_generated_at')
    
    context = {
        'alerts': alerts,
        'critical_count': RestockAlert.objects.filter(severity='CRITICAL', status='ACTIVE').count(),
        'high_count': RestockAlert.objects.filter(severity='HIGH', status='ACTIVE').count(),
        'medium_count': RestockAlert.objects.filter(severity='MEDIUM', status='ACTIVE').count(),
    }
    return render(request, 'core/ai_alerts.html', context)

@login_required
@csrf_exempt
def acknowledge_restock_alert(request):
    """Acknowledge a restock alert (AJAX endpoint)."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            alert_id = data.get('alert_id')
            success = AIAnalyticsEngine.acknowledge_alert(alert_id, request.user)
            if success:
                return JsonResponse({'status': 'success', 'message': 'Alert acknowledged'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Alert not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
@csrf_exempt
def mark_restocked(request):
    """Mark an alert as restocked (AJAX endpoint)."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            alert_id = data.get('alert_id')
            success = AIAnalyticsEngine.mark_alert_restocked(alert_id)
            if success:
                return JsonResponse({'status': 'success', 'message': 'Alert marked as restocked'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Alert not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def consumption_analytics_view(request):
    """View consumption analytics for all items."""
    week_start = timezone.now().date() - datetime.timedelta(days=timezone.now().weekday())
    analytics = ConsumptionAnalytics.objects.filter(
        week_start=week_start
    ).order_by('-total_movement')
    
    # Get historical data for trending
    month_start = week_start.replace(day=1)
    monthly_analytics = SupplyConsumptionCycle.objects.filter(
        month_year=month_start
    ).order_by('-total_consumed')
    
    context = {
        'week_analytics': analytics,
        'monthly_analytics': monthly_analytics,
        'week_start': week_start,
        'month_start': month_start,
    }
    return render(request, 'core/consumption_analytics.html', context)

@login_required
def logistics_analytics_view(request):
    """View logistics and deployment analytics."""
    monthly_data = LogisticsAnalytics.objects.all().order_by('-month_year')
    latest = monthly_data.first()
    
    # Prepare chart data
    months = [m.month_year.strftime('%B %Y') for m in monthly_data[:12]]
    deployments = [m.total_units_deployed for m in monthly_data[:12]]
    return_rates = [m.return_rate_percentage for m in monthly_data[:12]]
    efficiency_scores = [m.logistics_efficiency_score for m in monthly_data[:12]]
    
    context = {
        'latest_analytics': latest,
        'all_analytics': monthly_data,
        'months_json': json.dumps(months),
        'deployments_json': json.dumps(deployments),
        'return_rates_json': json.dumps(return_rates),
        'efficiency_json': json.dumps(efficiency_scores),
    }
    return render(request, 'core/logistics_analytics.html', context)

@login_required
def supply_cycle_view(request):
    """View supply consumption cycle analysis by item."""
    current_month = datetime.date.today().replace(day=1)
    cycles = SupplyConsumptionCycle.objects.filter(
        month_year=current_month
    ).order_by('-total_consumed')
    
    # Get by category
    by_category = cycles.values('category').annotate(
        total_consumed=Sum('total_consumed'),
        items_count=Count('id')
    ).order_by('-total_consumed')
    
    context = {
        'cycles': cycles,
        'by_category': by_category,
        'month': current_month.strftime('%B %Y'),
    }
    return render(request, 'core/supply_cycle.html', context)
