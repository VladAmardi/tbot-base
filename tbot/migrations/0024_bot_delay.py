# Generated by Django 3.2.14 on 2022-11-22 18:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0023_auto_20220729_1933'),
    ]

    operations = [
        migrations.AddField(
            model_name='bot',
            name='delay',
            field=models.FloatField(default=0),
        ),
    ]
