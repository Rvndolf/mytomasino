from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.models import User
from tickets.models import Ticket
from user.models import StaffProfile
from .utils import send_ticket_status_email


def is_staff_or_superuser(user):
    return user.is_superuser or StaffProfile.objects.filter(user=user).exists()

@login_required
@user_passes_test(is_staff_or_superuser)
def admin_home(request):
    template = 'admin_panel/admin_home_partial.html' if request.headers.get('HX-Request') else 'admin_panel/admin_home.html'
    return render(request, template)


@login_required
@user_passes_test(is_staff_or_superuser)
def ticket_list(request):

    status_filter = request.GET.get('status', 'open')
    active_categories = request.GET.getlist('categories')

    # --- Get tickets based on user ---
    if request.user.is_superuser:
        tickets = Ticket.objects.all()
    else:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if staff_profile:
            tickets = Ticket.objects.filter(assigned_to__staffprofile__office=staff_profile.office)
        else:
            tickets = Ticket.objects.none()

    if active_categories:
        tickets = tickets.filter(category__in=active_categories)
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

    # --- HTMX returns the wrapper partial (filters + table) ---
    template = 'admin_panel/partials/ticket_list_partial_wrapper.html' if request.headers.get('HX-Request') else 'admin_panel/ticket_list.html'
    return render(request, template, context)


@login_required
@user_passes_test(is_staff_or_superuser)
def users_list(request):
    if request.user.is_superuser:
        users = User.objects.all()
    else:
        users = User.objects.exclude(staffprofile__isnull=False)

    context = {'users': users}
    template = 'admin_panel/users_list_partial.html' if request.headers.get('HX-Request') else 'admin_panel/users_list.html'
    return render(request, template, context)


@login_required
@user_passes_test(is_staff_or_superuser)
def update_ticket_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if not staff_profile or ticket.assigned_to is None or ticket.assigned_to.staffprofile.office != staff_profile.office:
            return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Ticket.STATUS_CHOICES):
            ticket.status = new_status
            ticket.save()
            send_ticket_status_email(ticket.created_by, ticket.ticket_id, new_status)

            if request.headers.get("HX-Request"):
                # Return ticket detail partial (or maybe row partial)
                return render(request, 'admin_panel/partials/ticket_detail_partial.html', {'ticket': ticket})

            messages.success(request, f"Ticket #{ticket.ticket_id} marked as {ticket.get_status_display()}.")
            return redirect('admin_panel:ticket_list')
        else:
            messages.error(request, "Invalid status selected.")

    return render(request, 'admin_panel/update_ticket.html', {'ticket': ticket})


@login_required
@user_passes_test(is_staff_or_superuser)
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if not staff_profile or ticket.assigned_to is None or ticket.assigned_to.staffprofile.office != staff_profile.office:
            return HttpResponse("Access denied", status=403)

    ticket_id_str = ticket.ticket_id
    ticket.delete()

    if request.headers.get("HX-Request"):
        return render(request, 'admin_panel/partials/delete_ticket_partial.html', {'ticket_id': ticket_id_str})

    messages.success(request, f"Ticket #{ticket_id_str} has been deleted.")
    return redirect('admin_panel:ticket_list')
