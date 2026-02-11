# Generated migration for OneNote change tracking fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_recording'),
    ]

    operations = [
        migrations.AddField(
            model_name='notereference',
            name='content_text',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='notereference',
            name='changes_summary',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='notereference',
            name='change_type',
            field=models.CharField(
                choices=[('new', 'New'), ('updated', 'Updated'), ('unchanged', 'Unchanged')],
                default='new',
                max_length=20,
            ),
        ),
    ]
