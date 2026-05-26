from django.contrib import admin
from .models import (
    Item, StockTransaction, Borrowing, ActivityLog, Task, TaskItem,
    ConsumptionAnalytics, RestockAlert, SupplyConsumptionCycle,
    LogisticsAnalytics, Notification
)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'barcode', 'category', 'quantity', 'status')
    list_filter = ('category', 'status')
    search_fields = ('name', 'barcode')

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('item', 'type', 'quantity', 'timestamp', 'user')
    list_filter = ('type', 'timestamp')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('item', 'borrower_name', 'quantity', 'date_borrowed', 'status')
    list_filter = ('status', 'date_borrowed')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    list_filter = ('timestamp',)

class TaskItemInline(admin.TabularInline):
    model = TaskItem
    extra = 1

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    inlines = [TaskItemInline]

# AI Analytics Models
@admin.register(ConsumptionAnalytics)
class ConsumptionAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('item', 'week_start', 'week_end', 'consumable_consumed', 'borrowed_quantity', 'avg_daily_consumption')
    list_filter = ('week_start', 'item__category')
    search_fields = ('item__name',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(RestockAlert)
class RestockAlertAdmin(admin.ModelAdmin):
    list_display = ('item', 'severity', 'status', 'current_quantity', 'predicted_quantity', 'recommended_restock', 'alert_generated_at')
    list_filter = ('severity', 'status', 'consumption_trend', 'alert_generated_at')
    search_fields = ('item__name',)
    readonly_fields = ('alert_generated_at', 'acknowledged_at')

@admin.register(SupplyConsumptionCycle)
class SupplyConsumptionCycleAdmin(admin.ModelAdmin):
    list_display = ('item', 'month_year', 'total_consumed', 'avg_daily_consumption', 'deployment_status')
    list_filter = ('month_year', 'category', 'deployment_status')
    search_fields = ('item__name',)
    readonly_fields = ('generated_at', 'updated_at')

@admin.register(LogisticsAnalytics)
class LogisticsAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('month_year', 'total_borrowing_events', 'total_units_deployed', 'return_rate_percentage', 'logistics_efficiency_score', 'trend')
    list_filter = ('month_year', 'trend')
    readonly_fields = ('generated_at', 'updated_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'user', 'is_read', 'action_required', 'created_at')
    list_filter = ('notification_type', 'is_read', 'action_required', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at', 'read_at')
