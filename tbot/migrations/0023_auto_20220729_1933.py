# Generated by Django 3.2.14 on 2022-07-29 19:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0022_alter_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='position_key',
            field=models.CharField(blank=True, default=None, max_length=128, null=True),
        ),
        migrations.AlterIndexTogether(
            name='order',
            index_together={('position', 'position_key')},
        ),
    ]
