from django import template
import re

register = template.Library()

@register.filter
def extract_note_content(action_text):
    """
    Extract the actual note content from TicketHistory action text.
    
    Examples:
    - "Note added by ADMIN (Staff): This is the note" -> "This is the note"
    - "User reply: This is a reply" -> "This is a reply"
    """
    if 'User reply:' in action_text:
        return action_text.split('User reply:', 1)[1].strip()
    
    if '(Staff):' in action_text:
        # Extract everything after "(Staff): "
        parts = action_text.split('(Staff):', 1)
        if len(parts) > 1:
            return parts[1].strip()
    
    return action_text
