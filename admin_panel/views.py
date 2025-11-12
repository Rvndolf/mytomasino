from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from tickets.models import Ticket
from .utils import send_ticket_status_email
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.models import User
from tickets.models import Ticket
from user.models import StaffProfile, Office  
from .utils import send_ticket_status_email  # assuming you have this

def is_staff_or_superuser(user):
    if user.is_superuser:
        return True
    return StaffProfile.objects.filter(user=user).exists()

@login_required
@user_passes_test(is_staff_or_superuser)
def admin_home(request):
    return render(request, 'admin_panel/admin_home.html')

@login_required
@user_passes_test(is_staff_or_superuser)
def ticket_list(request):
    status_filter = request.GET.get('status')
    active_categories = request.GET.getlist('categories')

    if request.user.is_superuser:
        tickets = Ticket.objects.all()
        if active_categories:
            tickets = tickets.filter(category__in=active_categories)
    else:
        try:
            staff_profile = StaffProfile.objects.get(user=request.user)
            tickets = Ticket.objects.filter(
                assigned_to__staffprofile__office=staff_profile.office
            )
            if active_categories:
                tickets = tickets.filter(category__in=active_categories)
        except StaffProfile.DoesNotExist:
            tickets = Ticket.objects.none()

    if status_filter:
        tickets = tickets.filter(status=status_filter)

    context = {
    'tickets': tickets,
    'status_filter': status_filter,
    'categories': Ticket.CATEGORY_CHOICES,
    'active_categories': active_categories,
    'status_choices': [
        ('open', 'Open', 'primary'),
        ('in_progress', 'In Progress', 'warning'),
        ('completed', 'Completed', 'success'),
    ],
    }


    if request.headers.get('HX-Request'):
        html = render(request, 'admin_panel/ticket_list.html', context).content
        start = html.find(b'<div id="ticket-table"')
        end = html.find(b'</div>', start) + len(b'</div>')
        return HttpResponse(html[start:end])

    return render(request, 'admin_panel/ticket_list.html', context)


# --- Users List ---
@login_required
@user_passes_test(is_staff_or_superuser)
def users_list(request):
    if request.user.is_superuser:
        users = User.objects.all()
    else:
        # Staff sees only students (exclude staff)
        users = User.objects.exclude(staffprofile__isnull=False)
    return render(request, 'admin_panel/users_list.html', {'users': users})


# --- Update Ticket Status ---
@login_required
@user_passes_test(is_staff_or_superuser)
def update_ticket_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.is_superuser:
        try:
            staff_profile = StaffProfile.objects.get(user=request.user)
            if ticket.assigned_to is None or ticket.assigned_to.staffprofile.office != staff_profile.office:
                return HttpResponse("Access denied", status=403)
        except StaffProfile.DoesNotExist:
            return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Ticket.STATUS_CHOICES):
            ticket.status = new_status
            ticket.save()
            send_ticket_status_email(ticket.created_by, ticket.ticket_id, new_status)
            messages.success(request, f"Ticket #{ticket.ticket_id} marked as {ticket.get_status_display()}.")
            return redirect('admin_panel:ticket_list')
        else:
            messages.error(request, "Invalid status selected.")

    return render(request, 'admin_panel/update_ticket.html', {'ticket': ticket})


# --- Delete Ticket ---
@login_required
@user_passes_test(is_staff_or_superuser)
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.is_superuser:
        try:
            staff_profile = StaffProfile.objects.get(user=request.user)
            if ticket.assigned_to is None or ticket.assigned_to.staffprofile.office != staff_profile.office:
                return HttpResponse("Access denied", status=403)
        except StaffProfile.DoesNotExist:
            return HttpResponse("Access denied", status=403)

    ticket.delete()
    messages.success(request, f"Ticket #{ticket.ticket_id} has been deleted.")
    return redirect('admin_panel:ticket_list')