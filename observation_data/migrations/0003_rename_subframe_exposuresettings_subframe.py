# Generated by Django 5.1.5 on 2025-02-02 17:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('observation_data', '0002_expertobservation_subframe'),
    ]

    operations = [
        migrations.RenameField(
            model_name='exposuresettings',
            old_name='subFrame',
            new_name='subframe',
        ),
    ]
