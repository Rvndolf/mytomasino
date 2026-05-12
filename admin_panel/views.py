from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q
from tickets.models import Ticket, TicketHistory, Notification
from user.models import StaffProfile
from .utils import send_ticket_status_email, OFFICE_TICKET_CATEGORIES, get_categories_for_office
import threading


def is_staff_or_superuser(user):
    return user.is_superuser or StaffProfile.objects.filter(user=user).exists()


def get_office_staff_ids(staff_profile):
    """Return a queryset of user IDs belonging to the same office as the given staff profile."""
    return StaffProfile.objects.filter(
        office=staff_profile.office
    ).values_list('user_id', flat=True)


def staff_can_access_ticket(staff_profile, ticket):
    """
    Return True if the staff member's office is allowed to access the ticket.
    Allows access if:
      - The ticket category is mapped to their office, OR
      - The ticket is directly assigned to someone in their office.
    """
    allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, [])
    if ticket.category in allowed_categories:
        return True
    office_staff_ids = get_office_staff_ids(staff_profile)
    return ticket.assigned_to_id in office_staff_ids


# ---------------------------------------------------------------------------
# Dashboard / Home
# ---------------------------------------------------------------------------

@login_required(login_url='user:login')
def admin_home(request):
    user_tickets = Ticket.objects.filter(assigned_to=request.user)

    completed_tickets = user_tickets.filter(status='completed').count()
    total_tickets = user_tickets.count()
    completion_percentage = round((completed_tickets / total_tickets) * 100) if total_tickets > 0 else 0

    history_entries = TicketHistory.objects.filter(
        ticket__in=user_tickets
    ).select_related('ticket').order_by('-timestamp')[:3]

    status_counts = {
        'open': user_tickets.filter(status='open').count(),
        'in_progress': user_tickets.filter(status='in_progress').count(),
        'completed': user_tickets.filter(status='completed').count(),
    }

    context = {
        'completion_percentage': completion_percentage,
        'history_entries': history_entries,
        'status_counts': status_counts,
    }

    if request.headers.get("HX-Request"):
        return render(request, "admin_panel/partials/admin_home_partial.html", context)

    return render(request, "admin_panel/admin_home.html", context)


# ---------------------------------------------------------------------------
# Ticket List
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_staff_or_superuser)
def ticket_list(request):
    status_filter = request.GET.get('status', 'open')
    active_categories = request.GET.getlist('categories')

    tickets = Ticket.objects.all()

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if staff_profile:
            allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, [])
            office_staff_ids = get_office_staff_ids(staff_profile)
            tickets = tickets.filter(
                Q(category__in=allowed_categories) |
                Q(assigned_to__in=office_staff_ids)
            )
        else:
            tickets = Ticket.objects.none()

    if active_categories:
        tickets = tickets.filter(category__in=active_categories)
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    context = {
        'tickets': tickets.order_by('-created_at'),
        'status_filter': status_filter,
        'categories': Ticket.CATEGORY_CHOICES,
        'active_categories': active_categories,
        'status_choices': [
            ('open', 'Open', 'primary'),
            ('in_progress', 'In Progress', 'warning'),
            ('completed', 'Completed', 'success'),
        ],
        'OFFICE_TICKET_CATEGORIES': OFFICE_TICKET_CATEGORIES,
    }

    if request.headers.get('HX-Request'):
        if request.headers.get('HX-Target') == 'ticket-table-body':
            return render(request, 'admin_panel/partials/ticket_rows_partial.html', context)
        return render(request, 'admin_panel/partials/ticket_list_partial.html', context)

    return render(request, 'admin_panel/ticket_list.html', context)


# ---------------------------------------------------------------------------
# Ticket Detail
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_staff_or_superuser)
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if not staff_profile or not staff_can_access_ticket(staff_profile, ticket):
            return HttpResponse("Access denied", status=403)

    Notification.objects.filter(
        user=request.user,
        ticket=ticket,
        is_read=False
    ).update(is_read=True)

    history = TicketHistory.objects.filter(ticket=ticket).order_by('-timestamp')

    conversation_notes = TicketHistory.objects.filter(
        ticket=ticket
    ).filter(
        Q(action__icontains='Note added by') | Q(action__icontains='User reply:')
    ).order_by('timestamp')

    context = {
        'ticket': ticket,
        'history': history,
        'conversation_notes': conversation_notes,
    }

    if request.headers.get("HX-Request"):
        return render(request, 'admin_panel/partials/ticket_detail_partial.html', context)

    return render(request, 'admin_panel/ticket_detail.html', context)


# ---------------------------------------------------------------------------
# Update Ticket Status
# ---------------------------------------------------------------------------

def _send_email_async(user, ticket_id, new_status):
    try:
        send_ticket_status_email(user, ticket_id, new_status)
    except Exception as e:
        print(f"[Email Error] Failed to send ticket status email: {e}")


@login_required
@user_passes_test(is_staff_or_superuser)
def update_ticket_status(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related('created_by', 'assigned_to'),
        pk=ticket_id
    )

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.select_related('office').filter(user=request.user).first()
        if not staff_profile or not staff_can_access_ticket(staff_profile, ticket):
            return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        new_status = request.POST.get("status")

        if new_status in dict(Ticket.STATUS_CHOICES):
            old_status_display = ticket.get_status_display()
            ticket.status = new_status
            ticket.save(update_fields=['status'])
            new_status_display = ticket.get_status_display()

            actor_name = request.user.get_full_name() or request.user.username
            ticket_id_val = ticket.ticket_id()

            TicketHistory.objects.create(
                ticket=ticket,
                ticket_title=ticket.title,
                new_status=new_status,
                action=f"Status changed from {old_status_display} to {new_status_display} by {actor_name}",
                user=request.user,
                created_by=ticket.created_by,
                activity_type='status_change'
            )

            Notification.objects.create(
                user=ticket.created_by,
                ticket=ticket,
                notification_type='ticket_updated',
                title='Ticket Status Updated',
                message=f'Your ticket #{ticket_id_val} "{ticket.title}" status has been changed to {new_status_display}.'
            )

            threading.Thread(
                target=_send_email_async,
                args=(ticket.created_by, ticket_id_val, new_status),
                daemon=True
            ).start()

            if request.headers.get("HX-Request"):
                history = (
                    TicketHistory.objects
                    .filter(ticket=ticket)
                    .select_related('user')
                    .order_by('-timestamp')
                )
                conversation_notes = (
                    TicketHistory.objects
                    .filter(ticket=ticket, activity_type__in=['note', 'user_reply'])
                    .select_related('user')
                    .order_by('timestamp')
                )
                response = render(request, 'admin_panel/partials/ticket_detail_partial.html', {
                    'ticket': ticket,
                    'history': history,
                    'conversation_notes': conversation_notes,
                })
                response['HX-Trigger'] = 'ticketUpdated'
                return response

            messages.success(request, f"Ticket #{ticket_id_val} marked as {new_status_display}.")
            return redirect('admin_panel:ticket_detail', ticket_id=ticket.id)

        messages.error(request, "Invalid status selected.")

    return redirect('admin_panel:ticket_detail', ticket_id=ticket.id)


# ---------------------------------------------------------------------------
# Add Ticket Note
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_staff_or_superuser)
def add_ticket_note(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if not staff_profile or not staff_can_access_ticket(staff_profile, ticket):
            return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        attachment = request.FILES.get("attachment")

        if note or attachment:
            action_text = (
                f"Note added by {request.user.username.upper()} (Staff): {note}"
                if note else
                f"Note added by {request.user.username.upper()} (Staff): [Attachment]"
            )

            TicketHistory.objects.create(
                ticket=ticket,
                ticket_title=ticket.title,
                action=action_text,
                user=request.user,
                created_by=ticket.created_by,
                activity_type='updated',
                new_status=ticket.status,
                attachment=attachment
            )

            Notification.objects.create(
                user=ticket.created_by,
                ticket=ticket,
                notification_type='ticket_response',
                title='New Response on Your Ticket',
                message=f'Staff has added a response to your ticket #{ticket.ticket_id()}: "{note[:100] if note else "Attachment"}"'
            )

            if request.headers.get("HX-Request"):
                history = TicketHistory.objects.filter(ticket=ticket).order_by('-timestamp')
                conversation_notes = (
                    history.filter(action__icontains='Note added by') |
                    history.filter(action__icontains='User reply:')
                ).order_by('timestamp')

                return render(request, 'admin_panel/partials/ticket_detail_partial.html', {
                    'ticket': ticket,
                    'history': history,
                    'conversation_notes': conversation_notes,
                })

        messages.success(request, "Note added successfully.")

    return redirect('admin_panel:ticket_detail', ticket_id=ticket.id)


# ---------------------------------------------------------------------------
# Delete Ticket
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_staff_or_superuser)
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if not staff_profile or not staff_can_access_ticket(staff_profile, ticket):
            return HttpResponse("Access denied", status=403)

    if request.method == 'GET':
        return render(request, 'admin_panel/partials/delete_ticket_partial.html', {'ticket': ticket})

    ticket_id_display = ticket.ticket_id()

    TicketHistory.objects.create(
        ticket=None,
        ticket_title=ticket.title,
        deleted_ticket_id=ticket.id,
        new_status='deleted',
        action=f"Ticket #{ticket_id_display} was deleted by {request.user.get_full_name() or request.user.username}",
        user=request.user,
        created_by=ticket.created_by,
        activity_type='deleted'
    )

    Notification.objects.create(
        user=ticket.created_by,
        ticket=None,
        notification_type='ticket_updated',
        title='Ticket Deleted by Staff',
        message=f'Your ticket #{ticket_id_display} has been deleted by staff.'
    )

    ticket.delete()

    if request.headers.get("HX-Request"):
        response = HttpResponse(status=200)
        response['HX-Trigger'] = 'refreshTicketList, resetTicketDetail, ticketDeleted'
        return response

    messages.success(request, f"Ticket #{ticket_id_display} has been deleted.")
    return redirect('admin_panel:ticket_list')


# ---------------------------------------------------------------------------
# Users List
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_staff_or_superuser)
def users_list(request):
    users = User.objects.filter(is_staff=False).order_by('-date_joined')

    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'admin_panel/partials/users_list_partial.html', context)

    return render(request, 'admin_panel/users_list.html', context)


# ---------------------------------------------------------------------------
# Notification endpoints
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_staff_or_superuser)
def notification_count(request):
    try:
        staff_profile = StaffProfile.objects.select_related('office').get(user=request.user)
        office_name = staff_profile.office.name
    except StaffProfile.DoesNotExist:
        return JsonResponse({'unread_count': 0})

    categories = get_categories_for_office(office_name)
    office_staff_ids = get_office_staff_ids(staff_profile)

    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False,
    ).filter(
        Q(ticket__category__in=categories) |
        Q(ticket__assigned_to__in=office_staff_ids)
    ).count()

    return JsonResponse({'unread_count': unread_count})


@login_required
@user_passes_test(is_staff_or_superuser)
def mark_notification_read(request, notification_id):
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            ticket_id = notification.ticket.id if notification.ticket else None
            return JsonResponse({'success': True, 'ticket_id': ticket_id})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
@user_passes_test(is_staff_or_superuser)
def mark_all_notifications_read(request):
    if request.method == 'POST':
        try:
            staff_profile = StaffProfile.objects.select_related('office').get(user=request.user)
            office_name = staff_profile.office.name
        except StaffProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No office assigned'})

        categories = get_categories_for_office(office_name)
        office_staff_ids = get_office_staff_ids(staff_profile)

        Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).filter(
            Q(ticket__category__in=categories) |
            Q(ticket__assigned_to__in=office_staff_ids)
        ).update(is_read=True)

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_staff_or_superuser)
def user_profile_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)

    context = {'profile_user': profile_user}

    if request.headers.get('HX-Request'):
        return render(request, 'admin_panel/partials/user_profile_view_partial.html', context)

    return render(request, 'admin_panel/user_profile_view.html', context)


# ---------------------------------------------------------------------------
# Admin History
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_staff_or_superuser)
def admin_history(request):
    history_qs = TicketHistory.objects.select_related(
        'ticket', 'ticket__created_by', 'ticket__assigned_to', 'user'
    ).order_by('-timestamp')

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if staff_profile:
            allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, [])
            office_staff_ids = get_office_staff_ids(staff_profile)
            history_qs = history_qs.filter(
                Q(ticket__category__in=allowed_categories) |
                Q(ticket__assigned_to__in=office_staff_ids) |
                Q(ticket__isnull=True)
            )
        else:
            history_qs = TicketHistory.objects.none()

    activity_type_filter = request.GET.get('activity_type', '')
    status = request.GET.get('status', '')
    user_search = request.GET.get('user', '')

    if activity_type_filter:
        if activity_type_filter == 'created':
            history_qs = history_qs.filter(
                Q(activity_type='created') | Q(action__icontains='created')
            )
        elif activity_type_filter == 'updated':
            history_qs = history_qs.filter(
                Q(activity_type='updated') | Q(action__icontains='updated')
            )
        elif activity_type_filter == 'status_change':
            history_qs = history_qs.filter(
                Q(activity_type='status_change') | Q(action__icontains='status')
            )
        elif activity_type_filter == 'response':
            history_qs = history_qs.filter(
                Q(activity_type='response') |
                Q(action__icontains='response') |
                Q(action__icontains='reply')
            )
        elif activity_type_filter == 'deleted':
            history_qs = history_qs.filter(
                Q(activity_type='deleted') |
                Q(ticket__isnull=True) |
                Q(action__icontains='deleted')
            )

    if status:
        history_qs = history_qs.filter(new_status=status)

    if user_search:
        history_qs = history_qs.filter(
            Q(user__username__icontains=user_search) |
            Q(user__email__icontains=user_search) |
            Q(user__first_name__icontains=user_search) |
            Q(user__last_name__icontains=user_search)
        )

    enriched_entries = []
    for entry in history_qs:
        action_lower = entry.action.lower()

        if entry.activity_type:
            final_activity_type = entry.activity_type
        elif entry.ticket is None:
            final_activity_type = 'deleted'
        elif 'created' in action_lower:
            final_activity_type = 'created'
        elif 'deleted' in action_lower:
            final_activity_type = 'deleted'
        elif 'status' in action_lower or 'changed' in action_lower:
            final_activity_type = 'status_change'
        elif 'response' in action_lower or 'replied' in action_lower or 'reply' in action_lower or 'comment' in action_lower:
            final_activity_type = 'response'
        else:
            final_activity_type = 'updated'

        user = entry.user
        if not user and entry.ticket:
            user = entry.ticket.created_by

        old_status = None
        new_status = entry.new_status
        if final_activity_type == 'status_change' and 'from' in action_lower and 'to' in action_lower:
            try:
                parts = entry.action.split('from')
                if len(parts) > 1:
                    status_part = parts[1].split('to')
                    if len(status_part) > 1:
                        old_status = status_part[0].strip().strip('"\'')
                        new_status = status_part[1].strip().strip('"\'')
            except Exception:
                pass

        response_preview = None
        if final_activity_type == 'response' and ':' in entry.action:
            try:
                preview_part = entry.action.split(':', 1)[1].strip().strip('"\'')
                response_preview = preview_part[:200]
            except Exception:
                pass

        ticket_id = entry.ticket.id if entry.ticket else None

        enriched_entries.append(type('EnrichedEntry', (object,), {
            'id': entry.id,
            'ticket': entry.ticket,
            'ticket_id': ticket_id,
            'ticket_title': entry.ticket_title if hasattr(entry, 'ticket_title') else None,
            'action': entry.action,
            'timestamp': entry.timestamp,
            'new_status': new_status,
            'old_status': old_status,
            'activity_type': final_activity_type,
            'user': user,
            'response_preview': response_preview,
        })())

    paginator = Paginator(enriched_entries, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'history_entries': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'admin_panel/partials/admin_history_partial.html', context)

    return render(request, 'admin_panel/admin_history.html', context)