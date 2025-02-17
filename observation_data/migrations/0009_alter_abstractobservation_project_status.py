# Generated by Django 5.1.3 on 2025-02-17 11:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("observation_data", "0008_expertobservation_end_observation_time_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="abstractobservation",
            name="project_status",
            field=models.CharField(
                choices=[
                    ("Pending Upload", "Pending"),
                    ("Uploaded", "Uploaded"),
                    ("Error", "Error"),
                    ("Completed", "Completed"),
                    ("Pending Deletion", "Pending Deletion"),
                    ("Failed", "Failed"),
                ]
            ),
        ),
    ]
