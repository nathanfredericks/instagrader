from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rubrics", "0003_remove_rubric_versioning_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="rubric",
            old_name="title",
            new_name="name",
        ),
    ]
