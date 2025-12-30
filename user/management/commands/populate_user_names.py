from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Populate first_name and last_name from email for all users without names'

    def handle(self, *args, **kwargs):
        updated_count = 0

        for user in User.objects.all():
            if not user.first_name:
                name_part = user.email.split("@")[0]
                parts = name_part.replace("_", ".").split(".")
                user.first_name = parts[0].capitalize()
                user.last_name = parts[1].capitalize() if len(parts) > 1 else ""
                user.save()
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Updated first_name and last_name for {updated_count} users.'
        ))
