import uuid
from django import forms
from django.utils import timezone
from .models import SOSDevice, Tourist, DeviceAssignment


class SOSDeviceForm(forms.ModelForm):
    """
    Form for registering and editing SOS Wristband devices.
    """
    class Meta:
        model = SOSDevice
        fields = [
            'device_code',
            'device_name',
            'device_type',
            'serial_number',
            'purchase_date',
            'battery_capacity',
            'status',
            'last_seen_at',
            'remarks',
        ]
        widgets = {
            'device_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. SOS-WRIST-001',
                'required': True,
            }),
            'device_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. SOS Wristband',
                'required': True,
            }),
            'device_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. SOS Wristband',
                'required': True,
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. SN-88234-A1',
                'required': True,
            }),
            'purchase_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'battery_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 500 (in mAh)',
                'min': '0',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'last_seen_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional hardware, firmware, or inspection notes...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['device_name'].initial = 'SOS Wristband'
            self.fields['device_type'].initial = 'SOS Wristband'
            self.fields['status'].initial = 'active'

    def clean_device_code(self):
        device_code = self.cleaned_data.get('device_code', '').strip()
        qs = SOSDevice.objects.filter(device_code__iexact=device_code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Device code '{device_code}' is already registered. Please use a unique device code.")
        return device_code

    def clean_serial_number(self):
        serial_number = self.cleaned_data.get('serial_number', '').strip()
        qs = SOSDevice.objects.filter(serial_number__iexact=serial_number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Serial number '{serial_number}' is already registered. Please check the serial number.")
        return serial_number


class DeviceChoiceField(forms.ModelChoiceField):
    """
    Custom choice field to render clear, detailed device identifiers.
    """
    def label_from_instance(self, obj):
        battery_str = f"{obj.battery_capacity} mAh" if obj.battery_capacity else "N/A"
        return f"{obj.device_code} — {obj.device_name} (S/N: {obj.serial_number} | Battery: {battery_str})"


class TouristAssignmentForm(forms.Form):
    """
    Single form to collect Tourist details and assign an existing SOS wristband.
    Ensures validation and atomic commit to both Tourist and DeviceAssignment tables.
    """
    # Tourist Details
    tourist_code = forms.CharField(
        max_length=20,
        label="Tourist Code",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. TR-2026-001',
            'required': True,
        }),
        help_text="Unique identification code for this tourist"
    )
    name = forms.CharField(
        max_length=150,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. John Doe',
            'required': True,
        })
    )
    phone = forms.CharField(
        max_length=20,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. +1 555-0199',
            'required': True,
        })
    )
    email = forms.EmailField(
        required=False,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. tourist@example.com',
        })
    )
    gender = forms.ChoiceField(
        choices=[('', '-- Select Gender --')] + Tourist.GENDER_CHOICES,
        required=False,
        label="Gender",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_of_birth = forms.DateField(
        required=False,
        label="Date of Birth",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        })
    )
    address = forms.CharField(
        label="Address / Hotel Location",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Hotel name, room number, or local accommodation address',
            'required': True,
        })
    )
    emergency_contact_name = forms.CharField(
        max_length=150,
        label="Emergency Contact Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Jane Doe (Spouse/Relative/Guide)',
            'required': True,
        })
    )
    emergency_contact_phone = forms.CharField(
        max_length=20,
        label="Emergency Contact Phone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. +1 555-0200',
            'required': True,
        })
    )
    tourist_status = forms.ChoiceField(
        choices=Tourist.STATUS_CHOICES,
        initial='active',
        label="Tourist Status",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Device & Assignment Details
    device = DeviceChoiceField(
        queryset=SOSDevice.objects.none(),
        empty_label="-- Select Available SOS Wristband --",
        label="Select SOS Wristband",
        widget=forms.Select(attrs={'class': 'form-select', 'required': True}),
        help_text="Only registered, active, unassigned wristbands appear in this list"
    )
    assignment_code = forms.CharField(
        max_length=30,
        label="Assignment Code",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. ASG-2026-001',
            'required': True,
        }),
        help_text="Unique assignment tracking code"
    )
    expected_return_at = forms.DateTimeField(
        required=False,
        label="Expected Return Date & Time",
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
        }),
        help_text="Estimated date and time when tourist will return the wristband"
    )
    notes = forms.CharField(
        required=False,
        label="Assignment Notes / Remarks",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Tour group name, special medical conditions, planned routes...',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate available devices: status is active AND not currently in an active assignment
        available_devices = SOSDevice.objects.filter(status='active').exclude(
            assignments__assignment_status='assigned'
        ).order_by('device_code')
        self.fields['device'].queryset = available_devices

    def clean_tourist_code(self):
        tourist_code = self.cleaned_data.get('tourist_code', '').strip()
        if Tourist.objects.filter(tourist_code__iexact=tourist_code).exists():
            raise forms.ValidationError(
                f"Tourist code '{tourist_code}' already exists in the system. Each tourist must have a unique code."
            )
        return tourist_code

    def clean_assignment_code(self):
        assignment_code = self.cleaned_data.get('assignment_code', '').strip()
        if DeviceAssignment.objects.filter(assignment_code__iexact=assignment_code).exists():
            raise forms.ValidationError(
                f"Assignment code '{assignment_code}' already exists. Please provide a unique assignment code."
            )
        return assignment_code

    def clean_device(self):
        device = self.cleaned_data.get('device')
        if not device:
            raise forms.ValidationError("Please select an active SOS wristband.")
        
        # Re-verify device availability on server side
        if device.status != 'active':
            raise forms.ValidationError(
                f"Device '{device.device_code}' cannot be assigned because its status is '{device.get_status_display()}'."
            )
        if device.assignments.filter(assignment_status='assigned').exists():
            raise forms.ValidationError(
                f"Device '{device.device_code}' is currently assigned to another tourist. Please select an available device."
            )
        return device
