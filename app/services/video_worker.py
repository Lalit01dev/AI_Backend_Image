import asyncio
import logging
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.campaign import Campaign
from app.services.veo3_video_generator import veo3_video_generator

logger = logging.getLogger(__name__)

def run_video_generation(campaign_id: str):
    """
    Runs video generation OUTSIDE the request lifecycle.
    Safe against client disconnects and timeouts.
    """
    db: Session = SessionLocal()

    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id
        ).first()

        if not campaign:
            logger.error(f"[{campaign_id}] Campaign not found")
            return

        campaign.status = "video_generating"
        db.commit()

        logger.info(f"[{campaign_id}] Video generation started")

        # ACTUAL heavy work
        veo3_video_generator.generate_campaign_videos(
            campaign_id=campaign_id,
            db=db
        )

        campaign.status = "video_completed"
        db.commit()

        logger.info(f"[{campaign_id}] Video generation completed")

    except Exception as e:
        campaign.status = "video_failed"
        db.commit()
        logger.exception(f"[{campaign_id}] Video generation failed: {e}")

    finally:
        db.close()
