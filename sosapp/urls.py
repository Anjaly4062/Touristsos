"""
URL configuration for sosapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from dashboard import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('api/alerts/create/', views.create_tourist_alert, name='create_tourist_alert'),
    path('api/notifications/', views.get_notifications_api, name='get_notifications_api'),
    path('api/notifications/mark-read/', views.mark_notification_read, name='mark_notification_read_root'),
    path('api/alerts/<int:alert_id>/mark-read/', views.mark_notification_read, name='mark_alert_read_root'),
    path('notifications/', views.notifications, name='notifications_root'),
]
