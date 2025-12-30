from django.core.mail import send_mail
from django.conf import settings

def send_ticket_status_email(user, ticket_id, new_status):
    if not user.profile.email_notifications:
        return

    subject = f"Ticket {ticket_id} Status Update"
    message = f"Hello {user.get_full_name()},\n\nYour ticket #{ticket_id} has been updated to '{new_status}'."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

OFFICE_TICKET_CATEGORIES = {
    "Registrar’s Office": ["academic"],          
    "ETC": ["technical"],                  
    "Physical Plant and Facilities Management Office": ["facilities"],  
    "Principal Office" : ["lostfound"],            
    "Office of Student Services": ["lostfound"],            
    "Guidance Office": ["welfare"],     
    "Office of Media, Alumni, and Public Affairs": ["generalinquiry"],         
}