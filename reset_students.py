# reset_students.py

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mytomasino.settings")
django.setup()

from django.contrib.auth.models import User
from user.models import UserProfile

students = [
    {"first_name": "Test", "last_name": "User01", "email": "testuser01@ust-legazpi.edu.ph", "id_number": "2024-0001"},
    {"first_name": "Test", "last_name": "User02", "email": "testuser02@ust-legazpi.edu.ph", "id_number": "2024-0002"},
    {"first_name": "Test", "last_name": "User03", "email": "testuser03@ust-legazpi.edu.ph", "id_number": "2024-0003"},
    {"first_name": "Test", "last_name": "User04", "email": "testuser04@ust-legazpi.edu.ph", "id_number": "2024-0004"},
    {"first_name": "Test", "last_name": "User05", "email": "testuser05@ust-legazpi.edu.ph", "id_number": "2024-0005"},
    {"first_name": "Test", "last_name": "User06", "email": "testuser06@ust-legazpi.edu.ph", "id_number": "2024-0006"},
    {"first_name": "Test", "last_name": "User07", "email": "testuser07@ust-legazpi.edu.ph", "id_number": "2024-0007"},
    {"first_name": "Test", "last_name": "User08", "email": "testuser08@ust-legazpi.edu.ph", "id_number": "2024-0008"},
    {"first_name": "Test", "last_name": "User09", "email": "testuser09@ust-legazpi.edu.ph", "id_number": "2024-0009"},
    {"first_name": "Test", "last_name": "User10", "email": "testuser10@ust-legazpi.edu.ph", "id_number": "2024-0010"},
    {"first_name": "Test", "last_name": "User11", "email": "testuser11@ust-legazpi.edu.ph", "id_number": "2024-0011"},
    {"first_name": "Test", "last_name": "User12", "email": "testuser12@ust-legazpi.edu.ph", "id_number": "2024-0012"},
    {"first_name": "Test", "last_name": "User13", "email": "testuser13@ust-legazpi.edu.ph", "id_number": "2024-0013"},
    {"first_name": "Test", "last_name": "User14", "email": "testuser14@ust-legazpi.edu.ph", "id_number": "2024-0014"},
    {"first_name": "Test", "last_name": "User15", "email": "testuser15@ust-legazpi.edu.ph", "id_number": "2024-0015"},
    {"first_name": "Test", "last_name": "User16", "email": "testuser16@ust-legazpi.edu.ph", "id_number": "2024-0016"},
    {"first_name": "Test", "last_name": "User17", "email": "testuser17@ust-legazpi.edu.ph", "id_number": "2024-0017"},
    {"first_name": "Test", "last_name": "User18", "email": "testuser18@ust-legazpi.edu.ph", "id_number": "2024-0018"},
    {"first_name": "Test", "last_name": "User19", "email": "testuser19@ust-legazpi.edu.ph", "id_number": "2024-0019"},
    {"first_name": "Test", "last_name": "User20", "email": "testuser20@ust-legazpi.edu.ph", "id_number": "2024-0020"},
    {"first_name": "Test", "last_name": "User21", "email": "testuser21@ust-legazpi.edu.ph", "id_number": "2024-0021"},
    {"first_name": "Test", "last_name": "User22", "email": "testuser22@ust-legazpi.edu.ph", "id_number": "2024-0022"},
    {"first_name": "Test", "last_name": "User23", "email": "testuser23@ust-legazpi.edu.ph", "id_number": "2024-0023"},
    {"first_name": "Test", "last_name": "User24", "email": "testuser24@ust-legazpi.edu.ph", "id_number": "2024-0024"},
    {"first_name": "Test", "last_name": "User25", "email": "testuser25@ust-legazpi.edu.ph", "id_number": "2024-0025"},
]

PASSWORD = "test123"

for student in students:
    email = student["email"]
    username = email.split("@")[0]

    # Delete existing user (cascades to UserProfile and related data)
    existing = User.objects.filter(username=username).first()
    if existing:
        existing.delete()
        print(f"Deleted existing user: {username}")

    # Recreate fresh
    user = User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,
        first_name=student["first_name"],
        last_name=student["last_name"],
    )

    profile = UserProfile.objects.get(user=user)
    profile.id_number = student["id_number"]
    profile.save()

    print(f"Recreated: {email} / {PASSWORD} / ID: {student['id_number']}")

print("Done!")