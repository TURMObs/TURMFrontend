# Generated by Django 5.1.3 on 2024-11-26 13:56

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("observation_data", "0002_expertobservation_required_amount_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="celestialtarget",
            name="catalog_id",
        ),
    ]
