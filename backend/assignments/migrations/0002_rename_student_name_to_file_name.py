from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("assignments", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="essay",
            old_name="student_name",
            new_name="file_name",
        ),
    ]
