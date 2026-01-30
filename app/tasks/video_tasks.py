from app.celery_app import celery_app
from app.services.video_worker import run_video_generation


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
    retry_backoff=True,
)
def generate_campaign_video_task(self, campaign_id, business_name, phone_number, website):
    business_info = {
        "name": business_name,
        "phone": phone_number,
        "website": website,
    } if business_name else None

    run_video_generation(campaign_id, business_info)