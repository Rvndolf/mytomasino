# tickets/context_processors.py

from tickets.models import Notification
from user.models import StaffProfile

def notifications(request):
    if not request.user.is_authenticated:
        return {
            'notifications': [],
            'unread_count': 0,
            'user_date_format': 'MM/DD/YYYY',
            'user_number_format': '1,000.00',
        }
    
    # ── User preferences ──────────────────────────────────────────
    profile = getattr(request.user, 'profile', None)
    user_date_format = getattr(profile, 'date_format', 'MM/DD/YYYY') if profile else 'MM/DD/YYYY'
    user_number_format = getattr(profile, 'number_format', '1,000.00') if profile else '1,000.00'

    # ── Notifications ─────────────────────────────────────────────
    # Check if user is staff with an office assignment
    try:
        staff_profile = StaffProfile.objects.select_related('office').get(user=request.user)
        # User is staff - filter by office categories
        from admin_panel.utils import get_categories_for_office
        
        office_name = staff_profile.office.name
        categories = get_categories_for_office(office_name)
        
        # Get notifications for tickets in this office's categories
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False,
            ticket__category__in=categories
        ).select_related('ticket').order_by('-created_at')[:10]
        
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False,
            ticket__category__in=categories
        ).count()
        
    except StaffProfile.DoesNotExist:
        # Regular user - show all their notifications
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).select_related('ticket').order_by('-created_at')[:10]
        
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
    
    return {
        'notifications': unread_notifications,
        'unread_count': unread_count,
        'user_date_format': user_date_format,
        'user_number_format': user_number_format,
    }