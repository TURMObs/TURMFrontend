# Generated by Django 4.2.16 on 2024-11-05 10:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("observations", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="abstractobservation",
            name="observatory",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="abstractobservation",
            name="target",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="observations",
                to="observations.celestialtarget",
            ),
        ),
    ]
