from django.contrib import admin
from .models import Tourist, SOSDevice, DeviceAssignment


@admin.register(Tourist)
class TouristAdmin(admin.ModelAdmin):
    list_display = ('tourist_code', 'name', 'phone', 'email', 'status', 'created_at')
    search_fields = ('tourist_code', 'name', 'phone', 'email')
    list_filter = ('status', 'gender', 'created_at')
    ordering = ('-created_at',)


@admin.register(SOSDevice)
class SOSDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_code', 'device_name', 'device_type', 'serial_number', 'status', 'battery_capacity', 'last_seen_at')
    search_fields = ('device_code', 'device_name', 'serial_number')
    list_filter = ('status', 'device_type')
    ordering = ('device_code',)


@admin.register(DeviceAssignment)
class DeviceAssignmentAdmin(admin.ModelAdmin):
    list_display = ('assignment_code', 'tourist', 'device', 'assignment_status', 'assigned_at', 'expected_return_at', 'returned_at')
    search_fields = ('assignment_code', 'tourist__name', 'tourist__tourist_code', 'device__device_code', 'device__serial_number')
    list_filter = ('assignment_status', 'assigned_at')
    ordering = ('-assigned_at',)
