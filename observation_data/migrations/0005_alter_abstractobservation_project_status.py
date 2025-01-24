# Generated by Django 5.1.3 on 2025-01-24 11:16

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "observation_data",
            "0004_rename_required_amount_variableobservation_frames_per_filter_and_more",
        ),
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
                    ("Pending Delete", "Pending Delete"),
                ]
            ),
        ),
    ]
