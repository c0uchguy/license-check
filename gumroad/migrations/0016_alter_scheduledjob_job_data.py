# Generated by Django 4.1 on 2022-08-16 22:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gumroad', '0015_remove_scheduledjob_repeats_every_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scheduledjob',
            name='job_data',
            field=models.TextField(),
        ),
    ]
