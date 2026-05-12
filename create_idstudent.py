from django.contrib.auth.models import User
from user.models import UserProfile

# Create the user — no email needed for barcode-only login
user = User.objects.create_user(
    username='Randolf Amaranto',
    password=None,          # no password — barcode only
    first_name='Randolf',
    last_name='Amaranto',
)
user.set_unusable_password()  # prevents password login entirely
user.save()

# Attach the student ID
UserProfile.objects.create(
    user=user,
    id_number='3200010',  # replace with your actual test barcode value
)

print(f"Created: {user.username} — ID: 3200010")