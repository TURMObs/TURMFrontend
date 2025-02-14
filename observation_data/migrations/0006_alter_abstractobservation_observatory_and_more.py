# Generated by Django 5.1.3 on 2025-02-11 16:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("observation_data", "0005_alter_exposuresettings_subframe"),
    ]

    operations = [
        migrations.AlterField(
            model_name="abstractobservation",
            name="observatory",
            field=models.ForeignKey(
                db_column="observatory",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="observation_data.observatory",
            ),
        ),
        migrations.AlterField(
            model_name="filter",
            name="filter_type",
            field=models.CharField(
                db_column="type", max_length=2, primary_key=True, serialize=False
            ),
        ),
        migrations.AlterField(
            model_name="observatoryexposuresettings",
            name="exposure_settings",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="observation_data.exposuresettings",
            ),
        ),
        migrations.AlterField(
            model_name="observatoryexposuresettings",
            name="observatory",
            field=models.ForeignKey(
                db_column="observatory",
                on_delete=django.db.models.deletion.CASCADE,
                to="observation_data.observatory",
            ),
        ),
    ]
