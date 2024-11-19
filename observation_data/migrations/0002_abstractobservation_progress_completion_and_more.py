# Generated by Django 5.1.3 on 2024-11-18 14:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("observation_data", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="abstractobservation",
            name="progress_completion",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="abstractobservation",
            name="project_status",
            field=models.CharField(
                choices=[
                    ("Pending Upload", "Pending"),
                    ("Uploaded", "Uploaded"),
                    ("Error", "Error"),
                    ("Completed", "Completed"),
                ]
            ),
        ),
    ]