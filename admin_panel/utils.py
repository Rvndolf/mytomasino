from django.core.mail import send_mail
from django.conf import settings

def send_ticket_status_email(user, ticket_id, new_status):
    if not user.profile.email_notifications:
        return

    subject = f"Ticket {ticket_id} Status Update"
    message = f"Hello {user.get_full_name()},\n\nYour ticket #{ticket_id} has been updated to '{new_status}'."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

OFFICE_TICKET_CATEGORIES = {
    "Registrar's Office": ["academic"],          
    "ETC": ["technical"],                  
    "Physical Plant and Facilities Management Office": ["facilities"],  
    "Principal Office" : ["lostfound"],            
    "Office of Student Services": ["lostfound"],            
    "Guidance Office": ["welfare"],     
    "Office of Media, Alumni, and Public Affairs": ["generalinquiry"],         
}

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