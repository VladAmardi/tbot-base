# Generated by Django 3.2.13 on 2022-07-10 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0015_auto_20220706_1904'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bot',
            old_name='step',
            new_name='step_down',
        ),
        migrations.RenameField(
            model_name='bot',
            old_name='step_delta',
            new_name='step_down_delta',
        ),
        migrations.AddField(
            model_name='bot',
            name='step_up',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
    ]