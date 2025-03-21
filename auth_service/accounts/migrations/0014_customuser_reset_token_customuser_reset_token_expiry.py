# Generated by Django 5.1.7 on 2025-03-18 10:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_rename_phone_number_profile_phone_number_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='reset_token',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='reset_token_expiry',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
