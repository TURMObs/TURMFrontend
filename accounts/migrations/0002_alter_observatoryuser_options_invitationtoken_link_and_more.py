# Generated by Django 5.1.3 on 2025-01-29 15:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="observatoryuser",
            options={
                "permissions": [
                    ("can_generate_invitation", "Can generate invitation links"),
                    ("can_invite_admins", "Can invite new admin users"),
                    ("can_invite_group_leaders", "Can invite new group leaders"),
                    ("can_create_expert_observation", "Can create expert observation"),
                    ("can_see_all_observations", "Can see all observations"),
                ]
            },
        ),
        migrations.AddField(
            model_name="invitationtoken",
            name="link",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="invitationtoken",
            name="username",
            field=models.CharField(default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="observatoryuser",
            name="deletion_pending",
            field=models.BooleanField(default=False),
        ),
    ]
