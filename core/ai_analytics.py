"""
AI-Powered Analytics Engine for SNSU DRRM Inventory Management
Handles predictive analysis, consumption forecasting, and automated alert generation
"""
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg, F
from .models import (
    Item, StockTransaction, Borrowing, ConsumptionAnalytics,
    RestockAlert, SupplyConsumptionCycle, LogisticsAnalytics, Notification
)
from .models import MaintenanceAlert
from django.contrib.auth.models import User


class AIAnalyticsEngine:
    """Main AI engine for inventory analytics and predictions."""

    @staticmethod
    def calculate_weekly_consumption():
        """
        Calculate and store weekly consumption data for all items.
        Aggregates consumable items and borrowed items.
        Should be run weekly (Monday).
        """
        today = timezone.now().date()
        # Get Monday of current week
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        items = Item.objects.filter(category__in=['Consumable', 'Medical', 'Safety'])
        
        for item in items:
            # Get stock transactions for the week
            stock_out = StockTransaction.objects.filter(
                item=item,
                type='OUT',
                timestamp__date__gte=week_start,
                timestamp__date__lte=week_end
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            # Get borrowed items for the week
            borrowed = Borrowing.objects.filter(
                item=item,
                date_borrowed__date__gte=week_start,
                date_borrowed__date__lte=week_end,
                status='Pending'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            total_movement = stock_out + borrowed
            days_in_period = 7
            avg_daily = total_movement / days_in_period if days_in_period > 0 else 0
            
            ConsumptionAnalytics.objects.update_or_create(
                item=item,
                week_start=week_start,
                defaults={
                    'week_end': week_end,
                    'consumable_consumed': stock_out,
                    'borrowed_quantity': borrowed,
                    'total_movement': total_movement,
                    'avg_daily_consumption': avg_daily
                }
            )

    @staticmethod
    def predict_stock_level(item, days_ahead=7):
        """
        Predict stock level for an item N days into the future.
        Uses exponential moving average of recent consumption.
        """
        # Get last 4 weeks of consumption data
        four_weeks_ago = timezone.now().date() - timedelta(days=28)
        recent_consumption = ConsumptionAnalytics.objects.filter(
            item=item,
            week_start__gte=four_weeks_ago
        ).order_by('-week_start')
        
        if not recent_consumption.exists():
            # Fallback: calculate from recent transactions
            week_ago = timezone.now().date() - timedelta(days=7)
            transactions = StockTransaction.objects.filter(
                item=item,
                type='OUT',
                timestamp__date__gte=week_ago
            ).aggregate(total=Sum('quantity'))['total'] or 0
            avg_daily_consumption = transactions / 7
        else:
            # Use weighted average (recent weeks weighted more)
            consumptions = list(recent_consumption.values_list('avg_daily_consumption', flat=True))
            if consumptions:
                # Exponential moving average
                weights = [0.4, 0.3, 0.2, 0.1][:len(consumptions)]
                sum_weights = sum(weights)
                avg_daily_consumption = sum(c * w for c, w in zip(consumptions, weights)) / sum_weights
            else:
                avg_daily_consumption = 0
        
        current_quantity = item.quantity
        predicted_quantity = max(0, current_quantity - (avg_daily_consumption * days_ahead))
        
        return {
            'current': current_quantity,
            'predicted': predicted_quantity,
            'avg_daily_consumption': avg_daily_consumption,
            'days_ahead': days_ahead
        }

    @staticmethod
    def generate_restock_alerts():
        """
        Generate AI-powered restock alerts based on consumption patterns.
        Should be run weekly.
        Creates or updates RestockAlert records.
        """
        consumable_items = Item.objects.filter(category__in=['Consumable', 'Medical', 'Safety', 'Equipment'])
        alerts_created = 0
        
        for item in consumable_items:
            # Predict stock for 7 days ahead
            prediction = AIAnalyticsEngine.predict_stock_level(item, days_ahead=7)
            current_qty = prediction['current']
            predicted_qty = prediction['predicted']
            avg_consumption = prediction['avg_daily_consumption']
            
            # Determine if threshold breached
            threshold = item.low_stock_threshold
            days_until_stockout = (current_qty / avg_consumption) if avg_consumption > 0 else float('inf')
            
            # Get consumption trend
            trend = AIAnalyticsEngine.get_consumption_trend(item)
            
            # Determine severity and restock recommendation
            # Prepare a safe days-until-stockout string
            if days_until_stockout == float('inf'):
                days_str = 'unknown'
            else:
                days_str = str(int(days_until_stockout))

            if predicted_qty <= 0 or (days_until_stockout != float('inf') and days_until_stockout <= 3):
                severity = 'CRITICAL'
                recommended_restock = int(item.low_stock_threshold * 5)  # Restock to 5x threshold
                reason = f"Critical stock risk. Item will run out in {days_str} days at current consumption rate."
            elif predicted_qty <= threshold or (days_until_stockout != float('inf') and days_until_stockout <= 7):
                severity = 'HIGH'
                recommended_restock = int(item.low_stock_threshold * 3)
                reason = f"Low stock warning. Predicted to fall below threshold in {days_str} days."
            elif predicted_qty <= (threshold * 2):
                severity = 'MEDIUM'
                recommended_restock = int(item.low_stock_threshold * 2)
                reason = f"Preventive restock recommended. Consumption trend is {trend}."
            else:
                severity = 'LOW'
                recommended_restock = int(item.low_stock_threshold)
                reason = f"Routine check suggested. Current stock is stable."
            
            # Only create alert if not already active
            existing_alert = RestockAlert.objects.filter(
                item=item,
                status='ACTIVE'
            ).first()
            
            if existing_alert:
                # Update existing alert
                existing_alert.severity = severity
                existing_alert.current_quantity = current_qty
                existing_alert.predicted_quantity = int(predicted_qty)
                existing_alert.recommended_restock = recommended_restock
                existing_alert.predicted_stockout_date = (
                    timezone.now().date() + timedelta(days=int(days_until_stockout))
                ) if days_until_stockout != float('inf') else None
                existing_alert.avg_weekly_consumption = avg_consumption * 7
                existing_alert.consumption_trend = trend
                existing_alert.reason = reason
                existing_alert.save()
            else:
                # Create new alert only for MEDIUM and above severity
                if severity in ['CRITICAL', 'HIGH', 'MEDIUM']:
                    RestockAlert.objects.create(
                        item=item,
                        severity=severity,
                        current_quantity=current_qty,
                        predicted_quantity=int(predicted_qty),
                        recommended_restock=recommended_restock,
                        predicted_stockout_date=(
                            timezone.now().date() + timedelta(days=int(days_until_stockout))
                        ) if days_until_stockout != float('inf') else None,
                        avg_weekly_consumption=avg_consumption * 7,
                        consumption_trend=trend,
                        reason=reason
                    )
                    alerts_created += 1
        
        return alerts_created

    @staticmethod
    def get_consumption_trend(item):
        """
        Analyze consumption trend for an item.
        Returns: STABLE, INCREASING, or DECREASING
        """
        # Get last 4 weeks of data
        four_weeks_ago = timezone.now().date() - timedelta(days=28)
        analytics = ConsumptionAnalytics.objects.filter(
            item=item,
            week_start__gte=four_weeks_ago
        ).order_by('week_start').values_list('avg_daily_consumption', flat=True)
        
        if len(analytics) < 2:
            return 'STABLE'
        
        analytics_list = list(analytics)
        first_half_avg = sum(analytics_list[:len(analytics_list)//2]) / (len(analytics_list)//2 or 1)
        second_half_avg = sum(analytics_list[len(analytics_list)//2:]) / (len(analytics_list) - len(analytics_list)//2 or 1)
        
        change_percent = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        
        if abs(change_percent) < 10:
            return 'STABLE'
        elif change_percent > 10:
            return 'INCREASING'
        else:
            return 'DECREASING'

    @staticmethod
    def generate_monthly_analytics():
        """
        Generate comprehensive monthly supply consumption cycle and logistics analytics.
        Should be run on the 1st of each month.
        """
        # Get first day of previous month (since we're analyzing completed month)
        today = timezone.now().date()
        current_month_start = date(today.year, today.month, 1)
        previous_month_start = current_month_start - timedelta(days=1)
        previous_month_start = date(previous_month_start.year, previous_month_start.month, 1)
        
        month_end = current_month_start - timedelta(days=1)  # Last day of previous month
        
        # Generate SupplyConsumptionCycle for each item
        items = Item.objects.all()
        for item in items:
            # Calculate consumption metrics
            consumed = StockTransaction.objects.filter(
                item=item,
                type='OUT',
                timestamp__date__gte=previous_month_start,
                timestamp__date__lte=month_end
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            borrowed = Borrowing.objects.filter(
                item=item,
                date_borrowed__date__gte=previous_month_start,
                date_borrowed__date__lte=month_end,
                status='Pending'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            restocked = StockTransaction.objects.filter(
                item=item,
                type='IN',
                timestamp__date__gte=previous_month_start,
                timestamp__date__lte=month_end
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            restock_events = StockTransaction.objects.filter(
                item=item,
                type='IN',
                timestamp__date__gte=previous_month_start,
                timestamp__date__lte=month_end
            ).count()
            
            # Calculate daily stats
            days_in_month = (month_end - previous_month_start).days + 1
            total_consumed = consumed + borrowed
            avg_daily = total_consumed / days_in_month if days_in_month > 0 else 0
            
            # Calculate variance (simple method)
            daily_consumptions = []
            for i in range(days_in_month):
                day = previous_month_start + timedelta(days=i)
                day_consumption = StockTransaction.objects.filter(
                    item=item,
                    type='OUT',
                    timestamp__date=day
                ).aggregate(total=Sum('quantity'))['total'] or 0
                daily_consumptions.append(day_consumption)
            
            variance = 0
            if daily_consumptions:
                mean = sum(daily_consumptions) / len(daily_consumptions)
                variance = (sum((x - mean) ** 2 for x in daily_consumptions) / len(daily_consumptions)) ** 0.5
            
            # Find peak consumption day
            peak_day = None
            if daily_consumptions:
                peak_day = daily_consumptions.index(max(daily_consumptions)) + 1
            
            # Predict next month's consumption using simple extrapolation
            predicted_next_month = avg_daily * 30  # Assume 30-day month
            
            # Determine deployment status
            if avg_daily > (item.quantity / 10):
                deployment_status = 'CRITICAL'
            elif total_consumed == 0:
                deployment_status = 'BUILDING'
            elif avg_daily > (item.low_stock_threshold / 7):
                deployment_status = 'STABLE'
            else:
                deployment_status = 'TRANSITIONING'
            
            # Restock recommendations
            min_restock = int(predicted_next_month + (item.low_stock_threshold * 2))
            optimal_restock = int(predicted_next_month * 1.25)  # 25% buffer
            
            SupplyConsumptionCycle.objects.update_or_create(
                item=item,
                month_year=previous_month_start,
                defaults={
                    'total_consumed': total_consumed,
                    'total_borrowed': borrowed,
                    'total_restocked': restocked,
                    'restock_count': restock_events,
                    'avg_daily_consumption': avg_daily,
                    'consumption_variance': variance,
                    'peak_consumption_day': peak_day,
                    'category': item.category,
                    'deployment_status': deployment_status,
                    'predicted_consumption_next_month': predicted_next_month,
                    'min_restock_recommended': min_restock,
                    'optimal_restock_quantity': optimal_restock,
                }
            )
        
        # Generate LogisticsAnalytics
        total_borrowing = Borrowing.objects.filter(
            date_borrowed__date__gte=previous_month_start,
            date_borrowed__date__lte=month_end
        ).count()
        
        total_units_deployed = Borrowing.objects.filter(
            date_borrowed__date__gte=previous_month_start,
            date_borrowed__date__lte=month_end
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Calculate return metrics
        returned = Borrowing.objects.filter(
            return_date__date__gte=previous_month_start,
            return_date__date__lte=month_end,
            status='Returned'
        )
        
        on_time_returns = 0
        for borrowing in returned:
            expected_return = borrowing.date_borrowed + timedelta(days=7)
            if borrowing.return_date <= expected_return:
                on_time_returns += 1
        
        delayed_returns = returned.count() - on_time_returns
        return_rate = (returned.count() / total_borrowing * 100) if total_borrowing > 0 else 0
        
        # Calculate average deployment duration
        active_borrowings = Borrowing.objects.filter(
            date_borrowed__date__gte=previous_month_start,
            date_borrowed__date__lte=month_end,
            status='Returned'
        )
        
        avg_duration = 0
        if active_borrowings.exists():
            durations = [(b.return_date - b.date_borrowed).days for b in active_borrowings if b.return_date]
            avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Category deployment breakdown
        equipment_deployed = Borrowing.objects.filter(
            item__category='Equipment',
            date_borrowed__date__gte=previous_month_start,
            date_borrowed__date__lte=month_end
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        consumable_deployed = Borrowing.objects.filter(
            item__category='Consumable',
            date_borrowed__date__gte=previous_month_start,
            date_borrowed__date__lte=month_end
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        medical_deployed = Borrowing.objects.filter(
            item__category='Medical',
            date_borrowed__date__gte=previous_month_start,
            date_borrowed__date__lte=month_end
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        safety_deployed = Borrowing.objects.filter(
            item__category='Safety',
            date_borrowed__date__gte=previous_month_start,
            date_borrowed__date__lte=month_end
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        tools_deployed = Borrowing.objects.filter(
            item__category='Tools',
            date_borrowed__date__gte=previous_month_start,
            date_borrowed__date__lte=month_end
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Find most borrowed item
        most_borrowed_item = Borrowing.objects.filter(
            date_borrowed__date__gte=previous_month_start,
            date_borrowed__date__lte=month_end
        ).values('item').annotate(
            total=Sum('quantity')
        ).order_by('-total').first()
        
        most_borrowed_item_obj = None
        if most_borrowed_item:
            most_borrowed_item_obj = Item.objects.get(id=most_borrowed_item['item'])
        
        # Calculate efficiency score (0-100)
        efficiency_score = min(100, (return_rate * 0.5) + (min(on_time_returns, total_borrowing) / max(1, total_borrowing) * 50))
        
        # Determine trend
        prev_logistics = LogisticsAnalytics.objects.filter(
            month_year__lt=previous_month_start
        ).order_by('-month_year').first()
        
        if prev_logistics:
            if total_units_deployed > prev_logistics.total_units_deployed:
                trend = 'INCREASING'
            elif total_units_deployed < prev_logistics.total_units_deployed:
                trend = 'DECREASING'
            else:
                trend = 'STABLE'
        else:
            trend = 'STABLE'
        
        most_borrowed_cat = most_borrowed_item_obj.category if most_borrowed_item_obj else 'Equipment'
        
        LogisticsAnalytics.objects.update_or_create(
            month_year=previous_month_start,
            defaults={
                'total_borrowing_events': total_borrowing,
                'total_units_deployed': total_units_deployed,
                'avg_deployment_duration_days': avg_duration,
                'active_deployments': Borrowing.objects.filter(
                    status='Pending'
                ).count(),
                'on_time_returns': on_time_returns,
                'delayed_returns': delayed_returns,
                'return_rate_percentage': return_rate,
                'equipment_deployed': equipment_deployed,
                'consumable_deployed': consumable_deployed,
                'medical_deployed': medical_deployed,
                'safety_deployed': safety_deployed,
                'tools_deployed': tools_deployed,
                'most_borrowed_item': most_borrowed_item_obj,
                'most_borrowed_category': most_borrowed_cat,
                'logistics_efficiency_score': efficiency_score,
                'trend': trend,
            }
        )

    @staticmethod
    def generate_maintenance_alerts():
        """
        Generate maintenance alerts based on `integrity_score`, `lifespan_days`, and recent wear reports.
        Should be run weekly alongside restock alerts.
        """
        alerts_created = 0
        items = Item.objects.filter(category__in=['Equipment', 'Tools', 'Medical', 'Safety'])

        for item in items:
            now_date = timezone.now().date()
            integrity = item.integrity_score if item.integrity_score is not None else 100.0
            lifespan = item.lifespan_days
            created = item.created_at.date() if getattr(item, 'created_at', None) else None
            age_days = None
            pct_life_used = None
            if lifespan and created:
                age_days = (now_date - created).days
                try:
                    pct_life_used = (age_days / lifespan) * 100
                except Exception:
                    pct_life_used = None

            # Determine severity
            severity = 'LOW'
            recommended_action = 'Monitor condition and schedule inspections.'
            reason_parts = []

            if integrity <= 20 or (pct_life_used is not None and pct_life_used >= 100):
                severity = 'CRITICAL'
                recommended_action = 'Replace item immediately.'
                reason_parts.append('Integrity critically low or lifespan exceeded')
            elif integrity <= 40 or (pct_life_used is not None and pct_life_used >= 80):
                severity = 'HIGH'
                recommended_action = 'Plan replacement within maintenance cycle.'
                reason_parts.append('High wear or nearing end-of-life')
            elif integrity <= 60 or (pct_life_used is not None and pct_life_used >= 60):
                severity = 'MEDIUM'
                recommended_action = 'Schedule maintenance/inspection soon.'
                reason_parts.append('Moderate wear or significant life used')
            else:
                severity = 'LOW'
                recommended_action = 'Monitor and inspect as scheduled.'

            # Additional info from recent borrowings' wear_score
            recent_borrows = Borrowing.objects.filter(item=item, status='Returned').order_by('-return_date')[:5]
            avg_wear = None
            wear_vals = [b.wear_score for b in recent_borrows if b.wear_score is not None]
            if wear_vals:
                avg_wear = sum(wear_vals) / len(wear_vals)
                reason_parts.append(f'Average reported wear: {avg_wear:.1f}')

            reason = '; '.join(reason_parts) if reason_parts else 'Integrity check based on item metrics.'

            predicted_eol = None
            if lifespan and created:
                predicted_eol = created + timedelta(days=lifespan)

            existing = MaintenanceAlert.objects.filter(item=item, status='ACTIVE').first()
            if existing:
                existing.severity = severity
                existing.current_integrity = integrity
                existing.predicted_end_of_life = predicted_eol
                existing.recommended_action = recommended_action
                existing.reason = reason
                existing.save()
            else:
                # Only create alerts for MEDIUM and above
                if severity in ['CRITICAL', 'HIGH', 'MEDIUM']:
                    MaintenanceAlert.objects.create(
                        item=item,
                        severity=severity,
                        current_integrity=integrity,
                        predicted_end_of_life=predicted_eol,
                        recommended_action=recommended_action,
                        reason=reason
                    )
                    alerts_created += 1

            # Create notifications for HIGH/CRITICAL
            if severity in ['CRITICAL', 'HIGH']:
                Notification.objects.update_or_create(
                    notification_type='SYSTEM',
                    item=item,
                    defaults={
                        'title': f'{severity} maintenance: {item.name}',
                        'message': reason + ' — ' + recommended_action,
                        'action_required': True,
                    }
                )

        return alerts_created

    @staticmethod
    def get_top_consumed_items(limit=5):
        """Get the most consumed consumable items this week."""
        week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
        
        return ConsumptionAnalytics.objects.filter(
            week_start=week_start,
            item__category__in=['Consumable', 'Medical', 'Safety']
        ).order_by('-total_movement')[:limit]

    @staticmethod
    def get_most_borrowed_items(limit=5):
        """Get the most borrowed items this week."""
        week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
        
        borrowings = Borrowing.objects.filter(
            date_borrowed__date__gte=week_start,
            status='Pending'
        ).values('item').annotate(
            total_borrowed=Sum('quantity')
        ).order_by('-total_borrowed')[:limit]
        
        items = []
        for b in borrowings:
            item = Item.objects.get(id=b['item'])
            items.append({
                'item': item,
                'total_borrowed': b['total_borrowed']
            })
        
        return items

    @staticmethod
    def acknowledge_alert(alert_id, user):
        """Acknowledge a restock alert (mark as seen by staff)."""
        try:
            alert = RestockAlert.objects.get(id=alert_id)
            alert.status = 'ACKNOWLEDGED'
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = user
            alert.save()
            return True
        except RestockAlert.DoesNotExist:
            return False

    @staticmethod
    def mark_alert_restocked(alert_id):
        """Mark an alert as restocked."""
        try:
            alert = RestockAlert.objects.get(id=alert_id)
            alert.status = 'RESTOCKED'
            alert.save()
            return True
        except RestockAlert.DoesNotExist:
            return False
