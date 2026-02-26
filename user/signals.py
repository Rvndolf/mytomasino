from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

def extract_names_from_email(email):
    """Return first_name and last_name from email before @"""
    name_part = email.split("@")[0]  # "john.doe"
    parts = name_part.replace("_", ".").split(".")  # ["john", "doe"]
    first_name = parts[0].capitalize()
    last_name = parts[1].capitalize() if len(parts) > 1 else ""
    return first_name, last_name

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create UserProfile automatically
        UserProfile.objects.get_or_create(user=instance)

        # Automatically set first_name and last_name
        first_name, last_name = extract_names_from_email(instance.email)
        instance.first_name = first_name
        instance.last_name = last_name
        instance.save()
