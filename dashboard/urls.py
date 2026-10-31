from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Home
    path('', views.dashboard_home, name='dashboard_home'),

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
    path('api/notifications/', views.get_notifications_api, name='dashboard_notifications_api'),
]
