from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction, models
from django.utils import timezone
from django.db.models import Q, Count

from .models import Tourist, SOSDevice, DeviceAssignment
from .forms import SOSDeviceForm, TouristAssignmentForm


def dashboard_home(request):
    """
    Main Dashboard View with summary metrics and operational overview.
    """
    total_tourists = Tourist.objects.count()
    total_devices = SOSDevice.objects.count()
    
    # Available devices: status is active and not currently assigned
    available_devices_qs = SOSDevice.objects.filter(status='active').exclude(
        assignments__assignment_status='assigned'
    )
    available_devices_count = available_devices_qs.count()
    
    # Active assignments count
    active_assignments_count = DeviceAssignment.objects.filter(
        assignment_status='assigned'
    ).count()

    # Recent assignments (latest 6)
    recent_assignments = DeviceAssignment.objects.select_related(
        'tourist', 'device'
    ).order_by('-assigned_at')[:6]

    # Available devices preview (top 5)
    available_devices_preview = available_devices_qs.order_by('device_code')[:5]

    # Device status breakdown
    device_status_counts = {
        'active': SOSDevice.objects.filter(status='active').count(),
        'maintenance': SOSDevice.objects.filter(status='maintenance').count(),
        'inactive': SOSDevice.objects.filter(status='inactive').count(),
        'lost': SOSDevice.objects.filter(status='lost').count(),
    }

    context = {
        'page_title': 'Dashboard Overview',
        'active_menu': 'dashboard',
        'total_tourists': total_tourists,
        'total_devices': total_devices,
        'available_devices': available_devices_count,
        'active_assignments': active_assignments_count,
        'recent_assignments': recent_assignments,
        'available_devices_preview': available_devices_preview,
        'device_status_counts': device_status_counts,
    }
    return render(request, 'index.html', context)


def device_list(request):
    """
    List all SOS Wristband devices with filtering, search, and action controls.
    """
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    devices = SOSDevice.objects.all().prefetch_related('assignments', 'assignments__tourist')

    if search_query:
        devices = devices.filter(
            Q(device_code__icontains=search_query) |
            Q(device_name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(remarks__icontains=search_query)
        )

    if status_filter:
        devices = devices.filter(status=status_filter)

    # Attach current active assignment and can_delete flag to each device
    device_data = []
    for dev in devices:
        active_asg = None
        for asg in dev.assignments.all():
            if asg.assignment_status == 'assigned':
                active_asg = asg
                break
        
        has_history = dev.assignments.all().exists()
        device_data.append({
            'device': dev,
            'active_assignment': active_asg,
            'is_available': dev.status == 'active' and active_asg is None,
            'can_delete': not has_history,
            'history_count': dev.assignments.count(),
        })

    context = {
        'page_title': 'SOS Wristband Devices',
        'active_menu': 'device_list',
        'device_data': device_data,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': devices.count(),
    }
    return render(request, 'device_list.html', context)


def device_register(request):
    """
    Register a new SOS Wristband device.
    """
    if request.method == 'POST':
        form = SOSDeviceForm(request.POST)
        if form.is_valid():
            device = form.save()
            messages.success(
                request,
                f"Device '{device.device_code}' ({device.device_name}) was successfully registered!"
            )
            return redirect('device_list')
        else:
            messages.error(request, "Please correct the errors in the device registration form.")
    else:
        form = SOSDeviceForm()

    context = {
        'page_title': 'Register SOS Wristband',
        'active_menu': 'device_register',
        'form': form,
        'is_edit': False,
    }
    return render(request, 'device_form.html', context)


def device_detail(request, pk):
    """
    View specifications, current status, and full assignment history of a device.
    """
    device = get_object_or_404(SOSDevice, pk=pk)
    assignments = device.assignments.select_related('tourist').order_by('-assigned_at')
    active_assignment = assignments.filter(assignment_status='assigned').first()
    has_history = assignments.exists()

    context = {
        'page_title': f"Device Details — {device.device_code}",
        'active_menu': 'device_list',
        'device': device,
        'assignments': assignments,
        'active_assignment': active_assignment,
        'is_available': device.status == 'active' and active_assignment is None,
        'can_delete': not has_history,
    }
    return render(request, 'device_detail.html', context)


def device_edit(request, pk):
    """
    Edit an existing SOS Wristband device.
    """
    device = get_object_or_404(SOSDevice, pk=pk)

    if request.method == 'POST':
        form = SOSDeviceForm(request.POST, instance=device)
        if form.is_valid():
            device = form.save()
            messages.success(
                request,
                f"Device '{device.device_code}' was successfully updated!"
            )
            return redirect('device_detail', pk=device.pk)
        else:
            messages.error(request, "Please correct the errors before saving device changes.")
    else:
        form = SOSDeviceForm(instance=device)

    context = {
        'page_title': f"Edit Device — {device.device_code}",
        'active_menu': 'device_list',
        'form': form,
        'device': device,
        'is_edit': True,
    }
    return render(request, 'device_form.html', context)


def device_delete(request, pk):
    """
    Delete a device only if it has no assignment history.
    """
    device = get_object_or_404(SOSDevice, pk=pk)

    if request.method == 'POST':
        if device.assignments.exists():
            messages.error(
                request,
                f"Cannot delete device '{device.device_code}'. It has {device.assignments.count()} "
                f"assignment record(s) in history. Business rules prohibit deleting devices with assignment history."
            )
            return redirect('device_list')

        try:
            device_code = device.device_code
            device.delete()
            messages.success(request, f"Device '{device_code}' was deleted successfully.")
        except models.ProtectedError:
            messages.error(
                request,
                f"Cannot delete device '{device.device_code}' because protected relations exist."
            )
        except Exception as e:
            messages.error(request, f"Failed to delete device: {str(e)}")

    return redirect('device_list')


def assign_device(request):
    """
    Single form to register tourist details and assign an active SOS wristband.
    Uses atomic transaction to ensure tourist and assignment are saved together.
    """
    available_devices_count = SOSDevice.objects.filter(status='active').exclude(
        assignments__assignment_status='assigned'
    ).count()

    if request.method == 'POST':
        form = TouristAssignmentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Lock selected device row to prevent race conditions in assignment
                    selected_device = SOSDevice.objects.select_for_update().get(
                        pk=form.cleaned_data['device'].pk
                    )

                    # Re-verify availability within the transaction
                    if selected_device.status != 'active':
                        form.add_error(
                            'device',
                            f"Device '{selected_device.device_code}' is {selected_device.get_status_display()} and cannot be assigned."
                        )
                        raise ValueError("Device is not active")

                    if selected_device.assignments.filter(assignment_status='assigned').exists():
                        form.add_error(
                            'device',
                            f"Device '{selected_device.device_code}' was just assigned to another tourist."
                        )
                        raise ValueError("Device already assigned")

                    # 1. Save Tourist record in dashboard_tourist
                    tourist = Tourist.objects.create(
                        tourist_code=form.cleaned_data['tourist_code'],
                        name=form.cleaned_data['name'],
                        phone=form.cleaned_data['phone'],
                        email=form.cleaned_data['email'],
                        gender=form.cleaned_data['gender'],
                        date_of_birth=form.cleaned_data['date_of_birth'],
                        address=form.cleaned_data['address'],
                        emergency_contact_name=form.cleaned_data['emergency_contact_name'],
                        emergency_contact_phone=form.cleaned_data['emergency_contact_phone'],
                        status=form.cleaned_data['tourist_status'],
                    )

                    # 2. Save Assignment record in dashboard_deviceassignment
                    assignment = DeviceAssignment.objects.create(
                        tourist=tourist,
                        device=selected_device,
                        assignment_code=form.cleaned_data['assignment_code'],
                        expected_return_at=form.cleaned_data['expected_return_at'],
                        assignment_status='assigned',
                        notes=form.cleaned_data['notes'],
                    )

                    # 3. Confirmation message displaying all required attributes
                    messages.success(
                        request,
                        f"Wristband successfully assigned! "
                        f"Tourist Code: {tourist.tourist_code} | "
                        f"Tourist Name: {tourist.name} | "
                        f"Device Code: {selected_device.device_code} | "
                        f"Assignment Code: {assignment.assignment_code}"
                    )
                    return redirect('assignment_history')

            except ValueError:
                # Handled via form.add_error
                pass
            except Exception as e:
                messages.error(
                    request,
                    f"An error occurred during assignment: {str(e)}. The transaction was rolled back."
                )
        else:
            messages.error(request, "Please correct the highlighted errors in the form below.")
    else:
        form = TouristAssignmentForm()

    context = {
        'page_title': 'Assign SOS Wristband',
        'active_menu': 'assign_device',
        'form': form,
        'available_devices_count': available_devices_count,
    }
    return render(request, 'assign_device.html', context)


def assignment_history(request):
    """
    View complete assignment history with status filtering and search.
    Provides return/unassign action for active assignments.
    """
    status_filter = request.GET.get('status', 'all').strip()
    search_query = request.GET.get('q', '').strip()

    assignments = DeviceAssignment.objects.select_related('tourist', 'device').order_by('-assigned_at')

    if status_filter and status_filter != 'all':
        assignments = assignments.filter(assignment_status=status_filter)

    if search_query:
        assignments = assignments.filter(
            Q(assignment_code__icontains=search_query) |
            Q(tourist__name__icontains=search_query) |
            Q(tourist__tourist_code__icontains=search_query) |
            Q(device__device_code__icontains=search_query) |
            Q(device__serial_number__icontains=search_query)
        )

    # Calculate status counts for filter tabs
    all_count = DeviceAssignment.objects.count()
    assigned_count = DeviceAssignment.objects.filter(assignment_status='assigned').count()
    returned_count = DeviceAssignment.objects.filter(assignment_status='returned').count()

    context = {
        'page_title': 'Device Assignment History',
        'active_menu': 'assignment_history',
        'assignments': assignments,
        'status_filter': status_filter,
        'search_query': search_query,
        'all_count': all_count,
        'assigned_count': assigned_count,
        'returned_count': returned_count,
    }
    return render(request, 'assignment_history.html', context)


def device_return(request, pk):
    """
    Process return of an active wristband assignment.
    Marks assignment as returned, sets returned_at timestamp, and preserves history.
    """
    if request.method == 'POST':
        assignment = get_object_or_404(DeviceAssignment.objects.select_related('tourist', 'device'), pk=pk)

        if assignment.assignment_status == 'assigned':
            assignment.assignment_status = 'returned'
            assignment.returned_at = timezone.now()
            assignment.save()

            messages.success(
                request,
                f"Wristband '{assignment.device.device_code}' was successfully returned by '{assignment.tourist.name}'. "
                f"Assignment '{assignment.assignment_code}' is marked as Returned. "
                f"Device is now available for reuse."
            )
        else:
            messages.warning(
                request,
                f"Assignment '{assignment.assignment_code}' is already recorded as '{assignment.get_assignment_status_display()}'."
            )

    return redirect('assignment_history')
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import TouristAlert, Tourist, SOSDevice


@csrf_exempt
@require_POST
def create_tourist_alert(request):
    try:
        data = json.loads(request.body)

        tourist = Tourist.objects.get(id=data['tourist_id'])
        device = SOSDevice.objects.get(id=data['device_id'])

        alert = TouristAlert.objects.create(
            tourist=tourist,
            device=device,
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
        )

        return JsonResponse({
            'success': True,
            'message': 'SOS alert created successfully',
            'alert_id': alert.id,
            'status': alert.status
        }, status=201)

    except Tourist.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Tourist not found'
        }, status=404)

    except SOSDevice.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'SOS device not found'
        }, status=404)

    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({
            'success': False,
            'message': 'Invalid alert data'
        }, status=400)

def notifications(request):
    alerts = TouristAlert.objects.select_related(
        'tourist', 'device'
    ).all()

    return render(
        request,
        'notifications.html',
        {'alerts': alerts}
    )