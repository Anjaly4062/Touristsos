
from django.conf import settings
from django.db import models


class Tourist(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    tourist_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True
    )
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField()
    emergency_contact_name = models.CharField(max_length=150)
    emergency_contact_phone = models.CharField(max_length=20)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tourist_code} - {self.name}"


class SOSDevice(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
        ('lost', 'Lost'),
    ]

    device_code = models.CharField(max_length=30, unique=True)
    device_name = models.CharField(
        max_length=100,
        default='SOS Wristband'
    )
    device_type = models.CharField(
        max_length=50,
        default='SOS Wristband'
    )
    serial_number = models.CharField(max_length=100, unique=True)
    purchase_date = models.DateField(null=True, blank=True)
    battery_capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Battery capacity in mAh'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    last_seen_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['device_code']

    def __str__(self):
        return f"{self.device_code} - {self.device_name}"

    @property
    def is_available(self):
        """Check if device is active and not currently assigned."""
        return self.status == 'active' and not self.assignments.filter(assignment_status='assigned').exists()

    @property
    def current_assignment(self):
        """Return currently active assignment if any."""
        return self.assignments.filter(assignment_status='assigned').first()


class DeviceAssignment(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('returned', 'Returned'),
        ('lost', 'Lost'),
        ('cancelled', 'Cancelled'),
    ]

    tourist = models.ForeignKey(
        Tourist,
        on_delete=models.PROTECT,
        related_name='assignments'
    )
    device = models.ForeignKey(
        SOSDevice,
        on_delete=models.PROTECT,
        related_name='assignments'
    )
    assignment_code = models.CharField(max_length=30, unique=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    expected_return_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    assignment_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='assigned'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assignments_made',
        null=True,
        blank=True
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assignments_received',
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.assignment_code} - {self.tourist.name}"

    @property
    def is_active(self):
        return self.assignment_status == 'assigned'


class TouristAlert(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm'),
    ]

    tourist = models.ForeignKey(
        Tourist,
        on_delete=models.PROTECT,
        related_name='alerts'
    )

    device = models.ForeignKey(
        SOSDevice,
        on_delete=models.PROTECT,
        related_name='alerts'
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tourist_alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f"SOS Alert - {self.tourist.name}"