from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('inventory/', views.inventory, name='inventory'),
    path('stock/', views.stock_management, name='stock_manage'),
    path('borrowing/', views.borrowing_system, name='borrowing'),
    path('scanner/', views.scanner, name='scanner'),
    path('item/add/', views.add_item, name='add_item'),
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('qr-generate/', views.qr_generator, name='qr_generator'),
    path('scan-barcode/', views.scan_barcode, name='scan_barcode'),
    path('api/item-action/', views.api_item_action, name='api_item_action'),
    path('kanban/', views.kanban, name='kanban'),
    path('kanban/add/', views.add_task, name='add_task'),
    path('kanban/update/', views.update_task_status, name='update_task_status'),
    path('analytics/', views.analytics, name='analytics'),
    path('activity/', views.activity_logs, name='activity_logs'),
    path('activity/clear/', views.clear_activity_logs, name='clear_activity_logs'),
    path('users/', views.user_management, name='user_management'),
    path('users/add/', views.add_user, name='add_user'),
    path('settings/', views.settings, name='settings'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('export/inventory/', views.export_inventory, name='export_inventory'),
    
    # AI Analytics Endpoints
    path('ai/alerts/', views.ai_alerts, name='ai_alerts'),
    path('api/ai/acknowledge-alert/', views.acknowledge_restock_alert, name='acknowledge_alert'),
    path('api/ai/mark-restocked/', views.mark_restocked, name='mark_restocked'),
    path('ai/consumption-analytics/', views.consumption_analytics_view, name='consumption_analytics'),
    path('ai/logistics-analytics/', views.logistics_analytics_view, name='logistics_analytics'),
    path('ai/supply-cycle/', views.supply_cycle_view, name='supply_cycle'),
]
