# Generated by Django 3.2.13 on 2022-07-10 18:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0017_rename_lot_multiplier_bot_lot_multiplier_down'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bot',
            name='direction',
        ),
    ]