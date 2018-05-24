from django.db import migrations

def insert_new(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    RandomKeywordId = apps.get_model('singkat', 'RandomKeywordId')
    rk = RandomKeywordId()
    rk.save()

class Migration(migrations.Migration):

    dependencies = [
        ('singkat', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(insert_new),
    ]
