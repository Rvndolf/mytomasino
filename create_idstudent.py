import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mytomasino.settings')
django.setup()

from django.contrib.auth.models import User
from user.models import UserProfile

user, user_created = User.objects.get_or_create(
    username='Randolf Amaranto',
    defaults={
        'first_name': 'Randolf',
        'last_name': 'Amaranto',
    }
)

if user_created:
    user.set_unusable_password()
    user.save()

profile, profile_created = UserProfile.objects.get_or_create(
    user=user,
    defaults={'id_number': '3200010'}
)

if not profile_created and profile.id_number != '3200010':
    profile.id_number = '3200010'
    profile.save()

print(f"{'Created' if user_created else 'Already exists'}: Randolf Amaranto — ID: {profile.id_number}")