from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def admin_notes_count(ticket):
    """Count unread admin notes (notes added after user's last view)"""
    if not ticket.last_admin_update:
        return 0
    
    if not ticket.last_viewed_by_user:
        # User has never viewed, count all admin notes
        last_view = ticket.created_at
    else:
        last_view = ticket.last_viewed_by_user
    
    # Only count notes added after last view
    if ticket.last_admin_update > last_view:
        return ticket.tickethistory_set.filter(
            action__icontains='Note added by',
            timestamp__gt=last_view
        ).count()
    
    return 0

@register.filter
def has_unread_updates(ticket):
    return ticket.has_unread_admin_notes()

@register.filter
def extract_note(action):
    if 'Note added by' in action and ': ' in action:
        parts = action.split(': ', 1)
        if len(parts) > 1:
            return parts[1]
    return action

@register.filter
def dict_get(d, key):
    return d.get(key, [])