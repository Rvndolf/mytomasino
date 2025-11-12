from django.db import migrations

def create_offices(apps, schema_editor):
    Office = apps.get_model('user', 'Office')
    offices = [
        'Registrar’s Office',
        'IT Office',
        'Physical Plant and Facilities Management Office',
        'Principal Office',
        'Guidance Office',
    ]
    for office in offices:
        Office.objects.get_or_create(name=office)

class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_office_staffprofile'),  # or replace with your latest existing migration
    ]

    operations = [
        migrations.RunPython(create_offices),
    ]
