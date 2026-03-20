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

@register.filter
def cloudinary_raw_url(url):
    """Convert Cloudinary image URL to raw URL for non-image files"""
    if url and '/image/upload/' in url:
        return url.replace('/image/upload/', '/raw/upload/')
    return url

@register.filter
def cloudinary_download_url(url):
    """Force Cloudinary file as download attachment"""
    if url and '/raw/upload/' in url:
        return url.replace('/raw/upload/', '/raw/upload/fl_attachment/')
    return url