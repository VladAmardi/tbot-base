# Generated by Django 3.2.13 on 2022-07-10 18:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0016_auto_20220710_1836'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bot',
            old_name='lot_multiplier',
            new_name='lot_multiplier_down',
        ),
    ]