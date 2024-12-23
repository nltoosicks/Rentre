# Generated by Django 5.1 on 2024-12-08 07:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentapp', '0002_property_property_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lease',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive')], db_index=True, default='inactive', max_length=10),
        ),
        migrations.AlterField(
            model_name='leasetenant',
            name='confirmed',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='property',
            name='city',
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='property',
            name='state',
            field=models.CharField(db_index=True, max_length=2),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(db_index=True, max_length=254, unique=True),
        ),
    ]
