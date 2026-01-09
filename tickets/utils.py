from user.models import Office, StaffProfile
from admin_panel.utils import OFFICE_TICKET_CATEGORIES
from tickets.models import Notification

def assign_office_and_staff(ticket):

    # Get all offices that handle this category using the mapping
    offices_names = get_office_for_category(ticket.category)
    
    if not offices_names:
        ticket.assigned_to = None
        ticket.save()
        return
    
    # Get Office objects
    offices = Office.objects.filter(name__in=offices_names)
    
    if not offices.exists():
        ticket.assigned_to = None
        ticket.save()
        return
    
    # Get all staff members from these offices
    staff_profiles = StaffProfile.objects.filter(
        office__in=offices,
        user__is_active=True
    ).select_related('user', 'office')
    
    if staff_profiles.exists():
        # Assign to the first available staff member
        ticket.assigned_to = staff_profiles.first().user
        ticket.save()
        
        # Create notifications for ALL staff in the office(s)
        office_names = " and ".join([office.name for office in offices])
        
        for staff_profile in staff_profiles:
            Notification.objects.create(
                user=staff_profile.user,
                ticket=ticket,
                notification_type='ticket_created',
                title=f'New Ticket Assigned: {ticket.title}',
                message=f'A new {ticket.get_category_display()} ticket has been created and assigned to {office_names}.'
            )
    else:
        ticket.assigned_to = None
        ticket.save()

def get_office_for_category(category):
    """Get the office(s) responsible for a ticket category"""
    offices = []
    for office, categories in OFFICE_TICKET_CATEGORIES.items():
        if category in categories:
            offices.append(office)
    return offices

def get_categories_for_office(office_name):
    """Get all categories handled by an office"""
    return OFFICE_TICKET_CATEGORIES.get(office_name, [])