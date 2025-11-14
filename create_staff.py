# create_staff.py

import os
import django

# Setup Django environment (so we can run this standalone)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mytomasino.settings")  # replace with your settings module
django.setup()

from django.contrib.auth.models import User
from user.models import Office, StaffProfile

# Offices, emails, and passwords
offices = [
    {"name": "Registrar’s Office", "email": "registrar@ust-legazpi.edu.ph", "password": "registrar123"},
    {"name": "IT Office", "email": "it@ust-legazpi.edu.ph", "password": "it123"},
    {"name": "Physical Plant and Facilities Management Office", "email": "ppfmo@ust-legazpi.edu.ph", "password": "ppfmo123"},
    {"name": "Principal Office", "email": "principal@ust-legazpi.edu.ph", "password": "principal123"},
    {"name": "Guidance Office", "email": "guidance@ust-legazpi.edu.ph", "password": "guidance123"},
]

for office_info in offices:
    office_name = office_info["name"]
    email = office_info["email"]
    password = office_info["password"]

    try:
        office = Office.objects.get(name=office_name)
    except Office.DoesNotExist:
        print(f"Office '{office_name}' does not exist. Skipping.")
        continue

    # Use email prefix as username
    username = email.split("@")[0]

    # Check if user exists, delete if yes (to avoid duplicates)
    existing_user = User.objects.filter(username=username).first()
    if existing_user:
        existing_user.delete()
        print(f"Deleted existing user '{username}' to recreate.")

    # Create new user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )

    # Make staff
    user.is_staff = True
    user.save()

    # Create StaffProfile
    StaffProfile.objects.create(user=user, office=office)

    print(f"Created user '{email}' with password '{password}' for office '{office_name}'")
