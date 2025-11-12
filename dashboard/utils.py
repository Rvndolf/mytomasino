from django.core.mail import send_mail
from django.conf import settings

def send_ticket_status_email(user, ticket_id, new_status):

    profile = getattr(user, 'profile', None)
    if not profile or not profile.email_notifications:
        return False  #

    subject = f"Ticket #{ticket_id} Status Update"
    message = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Your ticket with ID #{ticket_id} has been updated to '{new_status.upper()}'.\n\n"
        f"Please log in to your dashboard for more details.\n\n"
        f"Thank you,\nYour Support Team"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    return True
