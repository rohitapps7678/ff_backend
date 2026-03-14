import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ff_backend.settings')

app = Celery('ff_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()