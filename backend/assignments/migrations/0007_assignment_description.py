from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assignments", "0006_assignment_grading_completed_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
