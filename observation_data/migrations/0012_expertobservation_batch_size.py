# Generated by Django 5.1.3 on 2025-03-09 14:24

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("observation_data", "0011_alter_abstractobservation_project_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="expertobservation",
            name="batch_size",
            field=models.IntegerField(default=10),
            preserve_default=False,
        ),
    ]
