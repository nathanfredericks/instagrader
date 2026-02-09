import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "instagrader.settings")

app = Celery("instagrader")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
