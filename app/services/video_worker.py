import asyncio
import logging
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.campaign import Campaign, CampaignScene
from app.services.veo3_video_generator import veo3_video_generator
from app.services.elevenlabs_tts_service import elevenlabs_tts_service
from app.services.video_merger import video_merger
from app.services.s3_service import upload_to_s3
from app.services.retry_utils import generate_video_with_retries
from app.services.narration import build_scene_narration
from app.constants.motion_presets import VEO_MOTION_PRESETS


# ------------------------------------------------------------------
# Logger setup (Celery already adds timestamps)
# ------------------------------------------------------------------
logger = logging.getLogger("video_pipeline")
logger.setLevel(logging.INFO)

# Silence noisy libs
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)


def run_video_generation(campaign_id: str, business_info: dict | None):
    """
    FULL VIDEO GENERATION PIPELINE
    --------------------------------
    Runs ONLY inside Celery worker.
    Uses runtime business_info (Option 1).
    """

    db: Session = SessionLocal()

    try:
        # ==================================================
        # START
        # ==================================================
        logger.info("▶️ Campaign %s: video generation started", campaign_id)

        # --------------------------------------------------
        # 1️⃣ Load campaign
        # --------------------------------------------------
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise Exception("Campaign not found")

        campaign.status = "veo_generating"
        db.commit()
        logger.info("✅ Campaign loaded")

        # --------------------------------------------------
        # 2️⃣ Load scenes
        # --------------------------------------------------
        scenes = (
            db.query(CampaignScene)
            .filter(CampaignScene.campaign_id == campaign_id)
            .order_by(CampaignScene.scene_number)
            .all()
        )

        if not scenes:
            raise Exception("No scenes found")

        logger.info("✅ %d scenes loaded", len(scenes))

        # --------------------------------------------------
        # 3️⃣ Generate scene videos + narration
        # --------------------------------------------------
        scene_video_urls: list[str] = []
        scene_voice_paths: list[str] = []

        for scene in scenes:
            if not scene.selected_image_url:
                continue

            logger.info(
                "🎬 Scene %s: processing started",
                scene.scene_number,
            )

            motion_prompt = VEO_MOTION_PRESETS.get(
                "brand", VEO_MOTION_PRESETS["brand"]
            )

            # ---- Video generation (async → sync boundary)
            video_url = asyncio.run(
                generate_video_with_retries(
                    veo3_video_generator,
                    scene_image_url=scene.selected_image_url,
                    motion_prompt=motion_prompt,
                    text_overlays={},
                    campaign_id=campaign_id,
                    scene_number=scene.scene_number,
                    business_info=business_info,
                    product_type=campaign.product_type or "beauty",
                    retries=4,
                    base_delay=6,
                )
            )

            logger.info(
                "✅ Scene %s: video generated",
                scene.scene_number,
            )

            # ---- Voice generation
            narration_text = build_scene_narration({}, business_info) or ""
            voice_path = elevenlabs_tts_service.generate_voice(narration_text)

            logger.info(
                "✅ Scene %s: voice generated",
                scene.scene_number,
            )

            # ---- Persist scene result
            scene.video_url = video_url
            scene.status = "video_generated"
            db.commit()

            scene_video_urls.append(video_url)
            scene_voice_paths.append(voice_path)

        if not scene_video_urls:
            raise Exception("No scene videos generated")

        # --------------------------------------------------
        # 4️⃣ Merge final video
        # --------------------------------------------------
        campaign.status = "merging_video"
        db.commit()
        logger.info("🧩 Merging final video")

        final_path = video_merger.process_full_pipeline(
            scene_video_urls=scene_video_urls,
            voice_paths=scene_voice_paths,
            campaign_id=campaign_id,
            output_name="final_ad.mp4",
        )

        final_url = upload_to_s3(final_path)

        campaign.final_video_url = final_url
        campaign.status = "videos_generated"
        db.commit()

        # ==================================================
        # DONE
        # ==================================================
        logger.info(
            "🏁 Campaign %s completed successfully",
            campaign_id,
        )
        logger.info("✅ Final video URL: %s", final_url)

        return final_url

    except Exception:
        campaign.status = "video_failed"
        db.commit()
        logger.exception("❌ Campaign %s failed", campaign_id)
        raise

    finally:
        db.close()
