# yourapp/templatetags/custom_filters.py
from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def short_timesince(value):
    """
    Convert a datetime to a short format like '3h', '5m', '2d'
    """
    if not value:
        return ""
    
    now = timezone.now()
    
    # Make sure value is timezone-aware
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    
    diff = now - value
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "now"
    elif seconds < 3600:  # Less than 1 hour
        minutes = int(seconds / 60)
        return f"{minutes}m"
    elif seconds < 86400:  # Less than 1 day
        hours = int(seconds / 3600)
        return f"{hours}h"
    elif seconds < 604800:  # Less than 1 week
        days = int(seconds / 86400)
        return f"{days}d"
    elif seconds < 2592000:  # Less than 30 days
        weeks = int(seconds / 604800)
        return f"{weeks}w"
    else:  # More than 30 days
        months = int(seconds / 2592000)
        return f"{months}mo"