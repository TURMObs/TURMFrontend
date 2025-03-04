# Generated by Django 5.1.3 on 2025-03-02 14:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("observation_data", "0009_alter_abstractobservation_project_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="DefaultRequestSettings",
            fields=[
                (
                    "id",
                    models.IntegerField(default=0, primary_key=True, serialize=False),
                ),
                ("settings", models.JSONField(default=dict)),
            ],
        ),
        migrations.AddField(
            model_name="expertobservation",
            name="end_observation_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="expertobservation",
            name="start_observation_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="expertobservation",
            name="cadence",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="expertobservation",
            name="end_observation",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="expertobservation",
            name="end_scheduling",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="expertobservation",
            name="next_upload",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="expertobservation",
            name="start_observation",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="expertobservation",
            name="start_scheduling",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="monitoringobservation",
            name="cadence",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="monitoringobservation",
            name="end_scheduling",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="monitoringobservation",
            name="next_upload",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="monitoringobservation",
            name="start_scheduling",
            field=models.DateField(blank=True, null=True),
        ),
    ]
