# Generated by Django 4.1 on 2022-08-13 19:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gumroad', '0009_rename_invites_invite'),
    ]

    operations = [
        migrations.AddField(
            model_name='guildeduser',
            name='avatar',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
    ]