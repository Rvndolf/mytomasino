from django.db import models
import random
import string
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class EmailVerification(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # store hashed password
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_code(length=6):
        return ''.join(random.choices(string.digits, k=length))

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=15)

    def __str__(self):
        return f"{self.email}"

# user/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MaxLengthValidator, MinLengthValidator

class UserProfile(models.Model):
    DEPARTMENT_CHOICES = [
        ("JHS", "Junior High School"),
        ("SHS", "Senior High School"),
        ("CASE", "College of Arts, Sciences, and Education (CASE)"),
        ("CHS", "College of Health Sciences (CHS)"),
        ("CEAFA", "College of Engineering, Fine Arts, and Architecture (CEAFA)"),
        ("CBMA", "College of Business Management and Accountancy (CBMA)"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    id_number = models.CharField(
        max_length=9,
        validators=[
            RegexValidator(r"^\d{1,9}$", "ID Number must contain only up to 9 digits.")
        ],
        blank=True,
        null=True,
    )
    department = models.CharField(
        max_length=20,
        choices=DEPARTMENT_CHOICES,
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