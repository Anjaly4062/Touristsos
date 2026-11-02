from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Home
    path('', views.dashboard_home, name='dashboard_home'),

    # Notifications Page
    path('notifications/', views.notifications, name='notifications'),

    # Device Management
    path('devices/', views.device_list, name='device_list'),
    path('devices/register/', views.device_register, name='device_register'),
    path('devices/<int:pk>/', views.device_detail, name='device_detail'),
    path('devices/<int:pk>/edit/', views.device_edit, name='device_edit'),
    path('devices/<int:pk>/delete/', views.device_delete, name='device_delete'),

    # Tourist Registration & Device Assignment
    path('assign/', views.assign_device, name='assign_device'),

    # Assignment History & Device Return
    path('assignments/', views.assignment_history, name='assignment_history'),
    path('assignments/<int:pk>/return/', views.device_return, name='device_return'),

    # API Endpoints
    path('api/alerts/create/', views.create_tourist_alert, name='create_tourist_alert'),
    path('api/notifications/', views.get_notifications_api, name='dashboard_notifications_api'),
    path('api/notifications/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/alerts/<int:alert_id>/mark-read/', views.mark_notification_read, name='mark_alert_read'),
]
