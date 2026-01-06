from django.db import models
import random
import string
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator, MaxLengthValidator, MinLengthValidator


class Office(models.Model):
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    office = models.ForeignKey(Office, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.office.name}"
    
class UserProfile(models.Model):
    GRADE_LEVEL_CHOICES = [
        ("11", "Grade 11"),
        ("12", "Grade 12"),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    id_number = models.CharField(
        max_length=9,
        validators=[
            RegexValidator(r"^\d{1,9}$", "ID Number must contain only up to 9 digits.")
        ],
        unique=True,
        blank=True,
        null=True,
    )
    grade_level = models.CharField(
        max_length=2,
        choices=GRADE_LEVEL_CHOICES,
        blank=True,
        null=True,
    )
    section = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )
    contact_number = models.CharField(
        max_length=13,
        validators=[
            RegexValidator(
                r"^\+63\d{10}$",
                "Contact number must start with +63 and contain 13 characters total (e.g., +639123456789).",
            )
        ],
        blank=True,
        null=True,
    )
    address = models.TextField(blank=True, null=True)
    
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    language_preference = models.CharField(max_length=5, default="en")
    region = models.CharField(max_length=20, default="asia-ph")
    date_format = models.CharField(max_length=10, default="MM/DD/YYYY")
    number_format = models.CharField(max_length=10, default="1,000.00")
    
    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


