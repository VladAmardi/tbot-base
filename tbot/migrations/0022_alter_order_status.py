# Generated by Django 3.2.14 on 2022-07-28 11:38

import db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0021_auto_20220727_1039'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=db.fields.EnumField(choices=[('NEW', 'New'), ('ACTIVE', 'Active'), ('FILLED', 'Filled'), ('CANCELED', 'Canceled'), ('EXPIRED', 'Expired'), ('ERROR', 'Error')], default='NEW'),
        ),
    ]