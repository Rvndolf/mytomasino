# create_test_account.py
import os
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mytomasino.settings")
django.setup()

from django.contrib.auth.models import User
from user.models import UserProfile

EMAIL = "Testaccount@ust-legazpi.edu.ph"
PASSWORD = "Test_account123"
USERNAME = EMAIL.split("@")[0]  # "Testaccount"

existing = User.objects.filter(username=USERNAME).first()
if existing:
    print(f"User '{USERNAME}' already exists, skipping.")
else:
    user = User.objects.create_user(
        username=USERNAME,
        email=EMAIL,
        password=PASSWORD,
        first_name="Test",
        last_name="Account",
    )

    profile = UserProfile.objects.get(user=user)
    profile.id_number = "2024-0000"  # Change this if needed
    profile.save()

    print(f"Created user: {EMAIL} / {PASSWORD}")

print("Done!")