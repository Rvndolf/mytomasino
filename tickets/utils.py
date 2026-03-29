from user.models import Office, StaffProfile
from admin_panel.utils import OFFICE_TICKET_CATEGORIES
from tickets.models import Notification

def assign_office_and_staff(ticket):

    # Check if the user manually directed this ticket to a specific office
    directed_office_key = ticket.metadata.get('directed_office') if ticket.metadata else None

    if directed_office_key:
        OFFICE_KEY_MAP = {
            'registrar': "Registrar's Office",
            'etc': 'ETC',
            'ppfmo': 'Physical Plant and Facilities Management Office',
            'principal': 'Principal Office',
            'studentservices': 'Office of Student Services',
            'guidance': 'Guidance Office',
            'mapa': 'Office of Media, Alumni, and Public Affairs',
        }
        office_name = OFFICE_KEY_MAP.get(directed_office_key)
        offices = Office.objects.filter(name=office_name) if office_name else Office.objects.none()
    else:
        # Auto-route based on category
        offices_names = get_office_for_category(ticket.category)

        if not offices_names:
            ticket.assigned_to = None
            ticket.save()
            return

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
        ticket.assigned_to = staff_profiles.first().user
        ticket.save()

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