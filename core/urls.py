from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('inventory/', views.inventory, name='inventory'),
    path('item/add/', views.add_item, name='add_item'),
    path('stock/', views.stock_management, name='stock_manage'),
    path('borrowing/', views.borrowing_system, name='borrowing'),
    path('scanner/', views.scanner, name='scanner'),
    path('item/<int:pk>/edit/', views.edit_item, name='edit_item'),
    path('item/<int:pk>/delete/', views.delete_item, name='delete_item'),
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('qr-generate/', views.qr_generator, name='qr_generator'),
    path('scan-barcode/', views.scan_barcode, name='scan_barcode'),
    path('api/item-action/', views.api_item_action, name='api_item_action'),

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
    
    # Responder Attendance
    path('attendance/', views.attendance_dashboard, name='attendance_dashboard'),
    path('api/attendance/scan/', views.api_attendance_scan, name='api_attendance_scan'),
    path('api/responder/register/', views.api_responder_register, name='api_responder_register'),
    path('api/responder/<int:pk>/delete/', views.api_responder_delete, name='api_responder_delete'),
    
    # First Aid Patient Assessment
    path('first-aid/', views.first_aid_dashboard, name='first_aid_dashboard'),
    path('first-aid/new/', views.first_aid_form, name='first_aid_form'),
    path('first-aid/<int:pk>/', views.first_aid_detail, name='first_aid_detail'),
    path('first-aid/<int:pk>/print/', views.first_aid_print, name='first_aid_print'),
    path('api/first-aid/save/', views.api_first_aid_save, name='api_first_aid_save'),
]
