import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mytomasino.settings')
django.setup()

from django.contrib.auth.models import User
from user.models import UserProfile

if not User.objects.filter(username='Randolf Amaranto').exists():
    user = User.objects.create_user(
        username='Randolf Amaranto',
        password=None,
        first_name='Randolf',
        last_name='Amaranto',
    )
    user.set_unusable_password()
    user.save()

    UserProfile.objects.create(
        user=user,
        id_number='3200010',
    )
    print("Created: Randolf Amaranto — ID: 3200010")
else:
    print("User 'Randolf Amaranto' already exists, skipping.")