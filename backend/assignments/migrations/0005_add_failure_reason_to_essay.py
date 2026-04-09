from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assignments", "0004_add_celery_task_id_to_assignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="essay",
            name="failure_reason",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Last processing/grading failure reason",
            ),
        ),
    ]
