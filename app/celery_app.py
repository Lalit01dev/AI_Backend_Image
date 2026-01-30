from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

celery_app = Celery(
    "video_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.video_tasks"] 
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

celery_app.autodiscover_tasks(["app.tasks"])