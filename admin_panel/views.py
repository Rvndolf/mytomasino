from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from tickets.models import Ticket, TicketHistory, Notification
from user.models import StaffProfile
from .utils import send_ticket_status_email, OFFICE_TICKET_CATEGORIES, get_categories_for_office
from django.core.paginator import Paginator
from django.db.models import Count, Q
import threading


def is_staff_or_superuser(user):
    return user.is_superuser or StaffProfile.objects.filter(user=user).exists()

@login_required(login_url='user:login')
def admin_home(request):
    # Get tickets visible to this staff member
    # Adjust the filter based on your permission logic
    user_tickets = Ticket.objects.filter(
        assigned_to=request.user  # or whatever your filtering logic is
    )
    
    # Calculate ticket completion percentage
    completed_tickets = user_tickets.filter(status='completed').count()
    total_tickets = user_tickets.count()
    
    if total_tickets > 0:
        completion_percentage = round((completed_tickets / total_tickets) * 100)
    else:
        completion_percentage = 0
    
    # Get last 5 ticket histories for tickets visible to this user
    history_entries = TicketHistory.objects.filter(
        ticket__in=user_tickets
    ).select_related('ticket').order_by('-timestamp')[:3]
    
    # Get status counts for the chart
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
        # Render only the partial content for HTMX
        return render(request, "admin_panel/partials/admin_home_partial.html", context)

    # For full page load (refresh), render the base template
    return render(request, "admin_panel/admin_home.html", context)

@login_required
@user_passes_test(is_staff_or_superuser)
def ticket_list(request):
    status_filter = request.GET.get('status', 'open')
    active_categories = request.GET.getlist('categories')

    tickets = Ticket.objects.all()

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if staff_profile:
            # Filter tickets by office → category mapping
            allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, [])
            tickets = tickets.filter(category__in=allowed_categories)
        else:
            tickets = Ticket.objects.none()

    # Apply additional filters from GET params
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

    # Check if this is an HTMX request (from sidebar navigation or table refresh)
    if request.headers.get('HX-Request'):
        # Check if this is a table refresh (only tbody needs to be updated)
        if request.headers.get('HX-Target') == 'ticket-table-body':
            # Return only table rows for tbody refresh
            return render(request, 'admin_panel/partials/ticket_rows_partial.html', context)
        # Otherwise return the full content partial (for sidebar navigation)
        return render(request, 'admin_panel/partials/ticket_list_partial.html', context)
    
    # Full page load (browser refresh)
    return render(request, 'admin_panel/ticket_list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def ticket_detail(request, ticket_id):
    """View detailed ticket information with history"""
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if not staff_profile:
            return HttpResponse("Access denied", status=403)

        # Allow if ticket category is in the office's allowed categories
        allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, [])
        if ticket.category not in allowed_categories:
            return HttpResponse("Access denied", status=403)

    # Mark notifications as read for staff
    Notification.objects.filter(
        user=request.user,
        ticket=ticket,
        is_read=False
    ).update(is_read=True)

    history = TicketHistory.objects.filter(ticket=ticket).order_by('-timestamp')
    
    # Get all conversation notes (staff responses AND user replies)
    from django.db.models import Q
    
    conversation_notes = TicketHistory.objects.filter(
        ticket=ticket
    ).filter(
        Q(action__icontains='Note added by') | Q(action__icontains='User reply:')
    ).order_by('timestamp')  # Chronological order for conversation

    context = {
        'ticket': ticket,
        'history': history,
        'conversation_notes': conversation_notes,
    }

    # Return partial for HTMX requests
    if request.headers.get("HX-Request"):
        return render(request, 'admin_panel/partials/ticket_detail_partial.html', context)

    # Full page render for normal requests
    return render(request, 'admin_panel/ticket_detail.html', context)


def _send_email_async(user, ticket_id, new_status):
    """Fire-and-forget email in a daemon thread to avoid blocking the response."""
    try:
        send_ticket_status_email(user, ticket_id, new_status)
    except Exception as e:
        # In production, replace with proper logging: logger.error(...)
        print(f"[Email Error] Failed to send ticket status email: {e}")


@login_required
@user_passes_test(is_staff_or_superuser)
def update_ticket_status(request, ticket_id):
    # select_related pulls user + assigned_to + created_by in one query
    ticket = get_object_or_404(
        Ticket.objects.select_related('created_by', 'assigned_to'),
        pk=ticket_id
    )

    # Permission check for staff
    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.select_related('office').filter(user=request.user).first()
        allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, []) if staff_profile else []
        if ticket.category not in allowed_categories:
            return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        new_status = request.POST.get("status")

        if new_status in dict(Ticket.STATUS_CHOICES):
            old_status_display = ticket.get_status_display()
            ticket.status = new_status
            ticket.save(update_fields=['status'])  # only update the status column, not the whole row
            new_status_display = ticket.get_status_display()

            actor_name = request.user.get_full_name() or request.user.username
            ticket_id_val = ticket.ticket_id  # cache to avoid repeated calls — remove () if it's a field not a method

            # Save history
            TicketHistory.objects.create(
                ticket=ticket,
                ticket_title=ticket.title,
                new_status=new_status,
                action=f"Status changed from {old_status_display} to {new_status_display} by {actor_name}",
                user=request.user,
                created_by=ticket.created_by,
                activity_type='status_change'
            )

            # Notification for ticket creator
            Notification.objects.create(
                user=ticket.created_by,
                ticket=ticket,
                notification_type='ticket_updated',
                title='Ticket Status Updated',
                message=f'Your ticket #{ticket_id_val} "{ticket.title}" status has been changed to {new_status_display}.'
            )

            # Send email asynchronously — no longer blocks the response
            threading.Thread(
                target=_send_email_async,
                args=(ticket.created_by, ticket_id_val, new_status),
                daemon=True
            ).start()

            if request.headers.get("HX-Request"):
                # Fetch history and conversation notes efficiently in one query each
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

@login_required
@user_passes_test(is_staff_or_superuser)
def add_ticket_note(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Permission check for staff
    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, []) if staff_profile else []
        if ticket.category not in allowed_categories:
            return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        if note:
            attachment = request.FILES.get("attachment")

            TicketHistory.objects.create(
                ticket=ticket,
                ticket_title=ticket.title,
                action=f"Note added by {request.user.username.upper()} (Staff): {note}",
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
                message=f'Staff has added a response to your ticket #{ticket.ticket_id()}: "{note[:100]}..."'
            )

            if request.headers.get("HX-Request"):
                history = TicketHistory.objects.filter(ticket=ticket).order_by('-timestamp')
                conversation_notes = history.filter(
                    action__icontains='Note added by'
                ) | history.filter(
                    action__icontains='User reply:'
                )
                conversation_notes = conversation_notes.order_by('timestamp')
                
                return render(request, 'admin_panel/partials/ticket_detail_partial.html', {
                    'ticket': ticket,
                    'history': history,
                    'conversation_notes': conversation_notes,
                })

        messages.success(request, "Note added successfully.")
    return redirect('admin_panel:ticket_detail', ticket_id=ticket.id)

@login_required
@user_passes_test(is_staff_or_superuser)
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Staff permission check
    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, []) if staff_profile else []
        if ticket.category not in allowed_categories:
            return HttpResponse("Access denied", status=403)

    if request.method == 'GET':
        # Render confirmation partial for HTMX modal
        return render(request, 'admin_panel/partials/delete_ticket_partial.html', {'ticket': ticket})

    # POST: actually delete ticket
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
        # Trigger both: refresh ticket list AND reset ticket detail container
        response['HX-Trigger'] = 'refreshTicketList, resetTicketDetail , ticketDeleted'
        return response

    messages.success(request, f"Ticket #{ticket_id_display} has been deleted.")
    return redirect('admin_panel:ticket_list')

@login_required
@user_passes_test(is_staff_or_superuser)
def users_list(request):
    """View to list all regular users (excluding staff)"""
    # Filter out staff users - only show regular users
    users = User.objects.filter(is_staff=False).order_by('-date_joined')
    
    # Add pagination (optional)
    paginator = Paginator(users, 20)  # 20 users per page
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


# Notification API endpoints
@login_required
@user_passes_test(is_staff_or_superuser)
def notification_count(request):
    """Return unread notification count for admin's office"""
    try:
        staff_profile = StaffProfile.objects.select_related('office').get(user=request.user)
        office_name = staff_profile.office.name
    except StaffProfile.DoesNotExist:
        return JsonResponse({'unread_count': 0})
    
    # Get categories for this office
    categories = get_categories_for_office(office_name)
    
    # Count unread notifications for tickets in these categories
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False,
        ticket__category__in=categories
    ).count()
    
    return JsonResponse({'unread_count': unread_count})


@login_required
@user_passes_test(is_staff_or_superuser)
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.is_read = True
            notification.save()

            # Return ticket_id only if ticket still exists
            ticket_id = notification.ticket.id if notification.ticket else None
            return JsonResponse({'success': True, 'ticket_id': ticket_id})

        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
@user_passes_test(is_staff_or_superuser)
def mark_all_notifications_read(request):
    """Mark all notifications as read for admin's office"""
    if request.method == 'POST':
        try:
            staff_profile = StaffProfile.objects.select_related('office').get(user=request.user)
            office_name = staff_profile.office.name
        except StaffProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No office assigned'})
        
        categories = get_categories_for_office(office_name)
        
        Notification.objects.filter(
            user=request.user,
            is_read=False,
            ticket__category__in=categories
        ).update(is_read=True)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
@user_passes_test(is_staff_or_superuser)
def user_profile_view(request, user_id):
    """View to display a user's profile details"""
    profile_user = get_object_or_404(User, id=user_id)
    
    context = {
        'profile_user': profile_user,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'admin_panel/partials/user_profile_view_partial.html', context)
    
    return render(request, 'admin_panel/user_profile_view.html', context)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from tickets.models import TicketHistory, Ticket

def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_staff_or_superuser)
def admin_history(request):
    """View to display all ticket activity history for staff"""

    # Get all history entries, ordered by most recent first
    history_qs = TicketHistory.objects.select_related(
        'ticket', 'ticket__created_by', 'ticket__assigned_to', 'user'
    ).order_by('-timestamp')

    # FILTER BY OFFICE - Only show tickets for categories this office handles
    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if staff_profile:
            allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, [])
            # Include live ticket entries matching category OR deleted ticket entries (ticket=NULL)
            history_qs = history_qs.filter(
                Q(ticket__category__in=allowed_categories) |
                Q(ticket__isnull=True)
            )
        else:
            history_qs = TicketHistory.objects.none()

    # Apply filters from GET parameters
    activity_type_filter = request.GET.get('activity_type', '')
    status = request.GET.get('status', '')
    user_search = request.GET.get('user', '')

    # Filter by activity type
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

    # Filter by status
    if status:
        history_qs = history_qs.filter(new_status=status)

    # Filter by user
    if user_search:
        history_qs = history_qs.filter(
            Q(user__username__icontains=user_search) |
            Q(user__email__icontains=user_search) |
            Q(user__first_name__icontains=user_search) |
            Q(user__last_name__icontains=user_search)
        )

    # Enrich each history entry with computed fields for the template
    enriched_entries = []
    for entry in history_qs:
        action_lower = entry.action.lower()

        # Determine activity type - prefer DB value, fall back to action text
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

        # Get user - use entry user, fallback to ticket creator
        user = entry.user
        if not user and entry.ticket:
            user = entry.ticket.created_by

        # Extract old/new status for status_change entries
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

        # Extract response preview
        response_preview = None
        if final_activity_type == 'response' and ':' in entry.action:
            try:
                preview_part = entry.action.split(':', 1)[1].strip().strip('"\'')
                response_preview = preview_part[:200]
            except Exception:
                pass

        # Resolve ticket_id safely
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

    # Pagination
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