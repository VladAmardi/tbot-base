# Generated by Django 3.2.13 on 2022-06-25 18:09

import db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0007_alter_bot_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exchangeconnection',
            name='exchange',
            field=db.fields.EnumField(choices=[('BINANCE', 'Binance'), ('FAKE', 'Fake')], default='BINANCE'),
        ),
        migrations.AlterField(
            model_name='symbol',
            name='exchange',
            field=db.fields.EnumField(choices=[('BINANCE', 'Binance'), ('FAKE', 'Fake')], default='BINANCE'),
        ),
    ]
