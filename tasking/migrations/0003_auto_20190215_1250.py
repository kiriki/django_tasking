# Generated by Django 2.1.5 on 2019-02-15 09:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasking', '0002_auto_20190210_1525'),
    ]

    operations = [
        migrations.RenameField(
            model_name='modeltask',
            old_name='task',
            new_name='action',
        ),
    ]