# Generated by Django 3.2 on 2021-04-17 08:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasking', '0006_alter_modeltask_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='modeltask',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
