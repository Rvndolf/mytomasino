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


@login_required
@user_passes_test(is_staff_or_superuser)
def update_ticket_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Permission check for staff
    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, []) if staff_profile else []
        if ticket.category not in allowed_categories:
            return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Ticket.STATUS_CHOICES):
            old_status_display = ticket.get_status_display()
            ticket.status = new_status
            ticket.save()
            new_status_display = ticket.get_status_display()

            # Save history
            TicketHistory.objects.create(
                ticket=ticket,
                ticket_title=ticket.title,
                new_status=new_status,
                action=f"Status changed from {old_status_display} to {new_status_display} by "
                       f"{request.user.get_full_name() or request.user.username}",
                user=request.user,
                created_by=ticket.created_by,
                activity_type='status_change'
            )

            # Create notification for ticket creator
            Notification.objects.create(
                user=ticket.created_by,
                ticket=ticket,
                notification_type='ticket_updated',
                title=f'Ticket Status Updated',
                message=f'Your ticket #{ticket.ticket_id()} "{ticket.title}" status has been changed to {new_status_display}.'
            )

            # Send notification email
            try:
                send_ticket_status_email(ticket.created_by, ticket.ticket_id(), new_status)
            except Exception as e:
                messages.warning(request, f"Status updated but email failed: {str(e)}")

            # HTMX response
            if request.headers.get("HX-Request"):
                history = TicketHistory.objects.filter(ticket=ticket).order_by('-timestamp')
                response = render(request, 'admin_panel/partials/ticket_detail_partial.html', {
                    'ticket': ticket,
                    'history': history
                })
                response['HX-Trigger'] = 'showToast, ticketUpdated'
                return response

            messages.success(request, f"Ticket #{ticket.ticket_id()} marked as {ticket.get_status_display()}.")
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
            TicketHistory.objects.create(
                ticket=ticket,
                ticket_title=ticket.title,
                action=f"Note added by {request.user.username.upper()} (Staff): {note}",
                user=request.user,
                created_by=ticket.created_by,
                activity_type='updated',
                new_status=ticket.status
            )

            Notification.objects.create(
                user=ticket.created_by,
                ticket=ticket,
                notification_type='ticket_response',
                title='New Response on Your Ticket',
                message=f'Staff has added a response to your ticket #{ticket.ticket_id()}: "{note[:100]}..."'
            )

            if request.headers.get("HX-Request"):
                # Return updated conversation view
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
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'})
    
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
    history_qs = TicketHistory.objects.select_related('ticket', 'ticket__created_by', 'ticket__assigned_to').order_by('-timestamp')
    
    # FILTER BY OFFICE - Only show tickets for categories this office handles
    if not request.user.is_superuser:
        staff_profile = StaffProfile.objects.filter(user=request.user).first()
        if staff_profile:
            # Get allowed categories for this office
            allowed_categories = OFFICE_TICKET_CATEGORIES.get(staff_profile.office.name, [])
            # Filter history to only show tickets in allowed categories
            history_qs = history_qs.filter(ticket__category__in=allowed_categories)
        else:
            # If no staff profile, show nothing
            history_qs = TicketHistory.objects.none()
    
    # Apply filters from GET parameters
    activity_type = request.GET.get('activity_type', '')
    status = request.GET.get('status', '')
    user_search = request.GET.get('user', '')
    
    # Filter by activity type (based on action text)
    if activity_type:
        if activity_type == 'created':
            history_qs = history_qs.filter(action__icontains='created')
        elif activity_type == 'updated':
            history_qs = history_qs.filter(action__icontains='updated')
        elif activity_type == 'status_change':
            history_qs = history_qs.filter(action__icontains='status')
        elif activity_type == 'response':
            history_qs = history_qs.filter(Q(action__icontains='response') | Q(action__icontains='reply'))
        elif activity_type == 'deleted':
            history_qs = history_qs.filter(action__icontains='deleted')
    
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
        # Determine activity type from action text
        action_lower = entry.action.lower()
        if 'created' in action_lower:
            activity_type_computed = 'created'
        elif 'deleted' in action_lower:
            activity_type_computed = 'deleted'
        elif 'status' in action_lower or 'changed' in action_lower:
            activity_type_computed = 'status_change'
        elif 'response' in action_lower or 'replied' in action_lower or 'reply' in action_lower or 'comment' in action_lower:
            activity_type_computed = 'response'
        elif 'updated' in action_lower or 'modified' in action_lower:
            activity_type_computed = 'updated'
        else:
            activity_type_computed = 'updated'
        
        # Use activity_type from database if available, otherwise use computed
        final_activity_type = entry.activity_type if entry.activity_type else activity_type_computed
        
        # Get user - use database user field, fallback to ticket.created_by
        user = entry.user
        if not user and entry.ticket:
            user = entry.ticket.created_by
        
        # Extract old and new status from action if it's a status change
        old_status = None
        new_status = entry.new_status
        if final_activity_type == 'status_change' and 'from' in action_lower and 'to' in action_lower:
            try:
                parts = entry.action.split('from')
                if len(parts) > 1:
                    status_part = parts[1].split('to')
                    if len(status_part) > 1:
                        old_status = status_part[0].strip().strip('"').strip("'").strip()
                        new_status = status_part[1].strip().strip('"').strip("'").strip()
            except:
                pass
        
        # Extract response preview if it's a response
        response_preview = None
        if final_activity_type == 'response':
            if ':' in entry.action:
                try:
                    preview_part = entry.action.split(':', 1)[1].strip().strip('"').strip("'")
                    response_preview = preview_part[:200]
                except:
                    pass
        
        # Create enriched entry object with all needed attributes
        enriched_entry = type('obj', (object,), {
            'id': entry.id,
            'ticket': entry.ticket,
            'ticket_id': entry.ticket.id if entry.ticket else getattr(entry, 'deleted_ticket_id', None),
            'ticket_title': entry.ticket_title,
            'action': entry.action,
            'timestamp': entry.timestamp,
            'new_status': new_status,
            'old_status': old_status,
            'activity_type': final_activity_type,
            'user': user,
            'response_preview': response_preview,
        })()
        
        enriched_entries.append(enriched_entry)
    
    # Pagination
    paginator = Paginator(enriched_entries, 20)  # Show 20 entries per page
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