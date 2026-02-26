# create_students.py

import os
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mytomasino.settings")
django.setup()

from django.contrib.auth.models import User
from user.models import UserProfile

students = [
    {"first_name": "Test", "last_name": "User01", "email": "testuser01@ust-legazpi.edu.ph", "id_number": "2024-00001"},
    {"first_name": "Test", "last_name": "User02", "email": "testuser02@ust-legazpi.edu.ph", "id_number": "2024-00002"},
    {"first_name": "Test", "last_name": "User03", "email": "testuser03@ust-legazpi.edu.ph", "id_number": "2024-00003"},
    {"first_name": "Test", "last_name": "User04", "email": "testuser04@ust-legazpi.edu.ph", "id_number": "2024-00004"},
    {"first_name": "Test", "last_name": "User05", "email": "testuser05@ust-legazpi.edu.ph", "id_number": "2024-00005"},
    {"first_name": "Test", "last_name": "User06", "email": "testuser06@ust-legazpi.edu.ph", "id_number": "2024-00006"},
    {"first_name": "Test", "last_name": "User07", "email": "testuser07@ust-legazpi.edu.ph", "id_number": "2024-00007"},
    {"first_name": "Test", "last_name": "User08", "email": "testuser08@ust-legazpi.edu.ph", "id_number": "2024-00008"},
    {"first_name": "Test", "last_name": "User09", "email": "testuser09@ust-legazpi.edu.ph", "id_number": "2024-00009"},
    {"first_name": "Test", "last_name": "User10", "email": "testuser10@ust-legazpi.edu.ph", "id_number": "2024-00010"},
    {"first_name": "Test", "last_name": "User11", "email": "testuser11@ust-legazpi.edu.ph", "id_number": "2024-00011"},
    {"first_name": "Test", "last_name": "User12", "email": "testuser12@ust-legazpi.edu.ph", "id_number": "2024-00012"},
    {"first_name": "Test", "last_name": "User13", "email": "testuser13@ust-legazpi.edu.ph", "id_number": "2024-00013"},
    {"first_name": "Test", "last_name": "User14", "email": "testuser14@ust-legazpi.edu.ph", "id_number": "2024-00014"},
    {"first_name": "Test", "last_name": "User15", "email": "testuser15@ust-legazpi.edu.ph", "id_number": "2024-00015"},
    {"first_name": "Test", "last_name": "User16", "email": "testuser16@ust-legazpi.edu.ph", "id_number": "2024-00016"},
    {"first_name": "Test", "last_name": "User17", "email": "testuser17@ust-legazpi.edu.ph", "id_number": "2024-00017"},
    {"first_name": "Test", "last_name": "User18", "email": "testuser18@ust-legazpi.edu.ph", "id_number": "2024-00018"},
    {"first_name": "Test", "last_name": "User19", "email": "testuser19@ust-legazpi.edu.ph", "id_number": "2024-00019"},
    {"first_name": "Test", "last_name": "User20", "email": "testuser20@ust-legazpi.edu.ph", "id_number": "2024-00020"},
    {"first_name": "Test", "last_name": "User21", "email": "testuser21@ust-legazpi.edu.ph", "id_number": "2024-00021"},
    {"first_name": "Test", "last_name": "User22", "email": "testuser22@ust-legazpi.edu.ph", "id_number": "2024-00022"},
    {"first_name": "Test", "last_name": "User23", "email": "testuser23@ust-legazpi.edu.ph", "id_number": "2024-00023"},
    {"first_name": "Test", "last_name": "User24", "email": "testuser24@ust-legazpi.edu.ph", "id_number": "2024-00024"},
    {"first_name": "Test", "last_name": "User25", "email": "testuser25@ust-legazpi.edu.ph", "id_number": "2024-00025"},
]

PASSWORD = "test123"

for student in students:
    email = student["email"]
    username = email.split("@")[0]  # e.g. testuser01

    existing = User.objects.filter(username=username).first()
    if existing:
        print(f"User '{username}' already exists, skipping.")
        continue

    user = User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,
        first_name=student["first_name"],
        last_name=student["last_name"],
    )

    # Update the UserProfile created by the signal with the id_number
    profile = UserProfile.objects.get(user=user)
    profile.id_number = student["id_number"]
    profile.save()

    print(f"Created student: {email} / {PASSWORD} / ID: {student['id_number']}")

print("Done!")