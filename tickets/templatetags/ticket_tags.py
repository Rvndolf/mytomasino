from django import template

register = template.Library()

@register.filter
def admin_notes_count(ticket):
    return ticket.tickethistory_set.filter(action__icontains='Note added by').count()

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