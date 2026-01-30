from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.database import get_db
from app.models.campaign import Campaign, CampaignScene

from app.services.nano_banana_generator import nano_banana_generator
from app.services.beauty_prompt_generator import beauty_prompt_generator

# -----------------------------
# CONFIG
# -----------------------------


LOCKED_OUTFIT_MAP = {
    "nail salon": "cream white knit sweater, long sleeves, minimal design, no logos",
    "nail shop": "cream white knit sweater, long sleeves, minimal design, no logos",
    "hair salon": "cream white knit sweater, long sleeves, minimal design, no logos",
    "hair shop": "cream white knit sweater, long sleeves, minimal design, no logos",
    "spa": "white spa robe, clean texture, no patterns",
    "spa center": "white spa robe, clean texture, no patterns",
}

router = APIRouter(prefix="/api/campaign", tags=["Campaign"])


def apply_prompt_optimizations(
    scenes,
    business_type,
    campaign_theme,
    locked_outfit,
):
    """
    Applies BeautyPromptGenerator + environment & outfit locking
    """
    optimized = []

    for scene in scenes:
        final_prompt = beauty_prompt_generator.generate_scene_prompt(
            scene_data=scene,
            business_type=business_type,
            campaign_theme=campaign_theme,
            character_image_url=None,
            aspect_ratio="16:9",
        )

        scene["prompt"] = (
            f"IMPORTANT: The environment MUST stay the SAME across all scenes. "
            f"Theme: {campaign_theme}. Decorations must remain consistent.\n"
            f"IMPORTANT: The person MUST wear the SAME outfit in ALL scenes: {locked_outfit}. "
            f"Do NOT change clothing, colors, fabric, or style.\n\n"
            f"{final_prompt}"
        )

        optimized.append(scene)

    return optimized


def nail_salon_scenes(campaign_theme, locked_outfit):
    decor = f"{campaign_theme} decorations, pine garlands, warm string lights, festive wreaths"

    return [
        {
            "scene_number": 1,
            "title": "Arrival - Entrance",
            "camera_angle": "Wide shot, full body, eye level",
            "prompt": (
                f"Person wearing {locked_outfit}. "
                f"Wide shot entering a modern nail salon. Full body visible, steady walk, "
                f"natural smile. Face sharp. Clean interior, {decor}. "
                f"Natural even lighting. Photorealistic, 16:9."
            ),
        },
        {
            "scene_number": 2,
            "title": "Welcome - Reception",
            "camera_angle": "Medium shot, waist-up, eye level",
            "prompt": (
                "Medium waist-up shot at reception counter. "
                "Balanced studio + natural lighting. "
                "Face fully visible, relaxed expression. "
                f"Background with subtle {campaign_theme}-themed décor. "
                "Photorealistic, 16:9."
            ),
        },
        {
            "scene_number": 3,
            "title": "Service - Manicure",
            "camera_angle": "Medium close-up, hands visible",
            "prompt": (
                "Medium eye-level shot after manicure. "
                "Head and shoulders visible, face sharp, confident smile. "
                "Hands raised naturally at chest level, nails visible but not close. "
                f"Clean salon background with subtle {campaign_theme}-themed décor. "
                "Photorealistic, 16:9."
            ),
        },
        {
            "scene_number": 4,
            "title": "Reveal - Festive Nails",
            "camera_angle": "Medium close-up, hands shown naturally",
            "prompt": (
                "Medium close-up holding hands gently at chest height. "
                "Finished nails visible, face unobstructed. "
                f"Clean warm background with {decor}. "
                "Photorealistic, 1:1."
            ),
        },
        {
            "scene_number": 5,
            "title": "Joy - Final Portrait",
            "camera_angle": "Portrait, shoulders-up",
            "prompt": (
                "Portrait shoulders-up, smiling softly. "
                "One hand near face, not covering. "
                f"Warm festive background with {campaign_theme}-themed décor. "
                "Photorealistic, 9:16."
            ),
        },
    ]


def hair_salon_scenes(campaign_theme, locked_outfit):
    decor = f"{campaign_theme} decorations, holiday garlands, warm lights"

    return [
        {
            "scene_number": 1,
            "title": "Arrival - Entrance",
            "camera_angle": "Wide shot, full body, eye level",
            "prompt": (
                f"Person wearing {locked_outfit}. "
                f"Wide shot entering an upscale hair salon. "
                f"Natural stride, face clear, {decor}. "
                "Photorealistic, 16:9."
            ),
        },
        {
            "scene_number": 2,
            "title": "Consultation - Chair",
            "camera_angle": "Medium shot, eye level",
            "prompt": (
                "Medium shot seated in salon chair facing camera. "
                "Balanced studio + natural lighting. "
                "No mirrors, no reflections. "
                f"Subtle {campaign_theme}-themed décor. "
                "Photorealistic, 16:9."
            ),
        },
        {
            "scene_number": 3,
            "title": "Styling - Motion",
            "camera_angle": "Medium close-up, straight-on",
            "prompt": (
                "Medium close-up with hair gently moving from soft breeze. "
                "No tools, no hands. "
                "Face sharp, eyes visible. "
                f"Subtle {campaign_theme}-themed décor. "
                "Photorealistic, 16:9."
            ),
        },
        {
            "scene_number": 4,
            "title": "Reveal - New Style",
            "camera_angle": "Medium shot, slight angle",
            "prompt": (
                "Medium shot turning head slightly to show hairstyle. "
                "Confident smile, face visible. "
                f"{decor} softly in background. "
                "Photorealistic, 1:1."
            ),
        },
        {
            "scene_number": 5,
            "title": "Confidence - Portrait",
            "camera_angle": "Portrait, shoulders-up",
            "prompt": (
                "Commercial beauty portrait, shoulders-up. "
                "No hands covering face. "
                "Clean warm background, even lighting. "
                "Real human texture. Photorealistic."
            ),
        },
    ]


def spa_scenes(campaign_theme, locked_outfit):
    decor = f"{campaign_theme} spa decorations, candles, pine branches"

    return [
        {
            "scene_number": 1,
            "title": "Arrival - Welcome",
            "camera_angle": "Wide shot, full body, eye level",
            "prompt": (
                f"Person wearing {locked_outfit}. "
                f"Wide shot entering calm spa reception. "
                "Relaxed walk, face clear. "
                f"{decor}. Photorealistic, 16:9."
            ),
        },
        {
            "scene_number": 2,
            "title": "Preparation - Treatment Room",
            "camera_angle": "Medium shot, waist-up",
            "prompt": (
                "Medium shot near treatment bed. "
                "Relaxed posture, soft spa lighting. "
                f"Subtle {campaign_theme}-themed décor. "
                "Photorealistic, 16:9."
            ),
        },
        {
            "scene_number": 3,
            "title": "Treatment - Relax",
            "camera_angle": "Close-up, face visible",
            "prompt": (
                "Close-up relaxing on treatment bed. "
                "Face visible, eyes gently closed. "
                "Warm natural spa lighting. "
                "Photorealistic, 16:9."
            ),
        },
        {
            "scene_number": 4,
            "title": "Renewal - Post-Treatment",
            "camera_angle": "Medium close-up, straight-on",
            "prompt": (
                "Medium close-up gently touching face (not covering). "
                "Refreshed skin, soft light. "
                "Photorealistic, 1:1."
            ),
        },
        {
            "scene_number": 5,
            "title": "Bliss - Portrait",
            "camera_angle": "Portrait, shoulders-up",
            "prompt": (
                "Portrait shoulders-up with calm smile. "
                "Hand near face, not occluding. "
                "Warm spa background. "
                "Photorealistic, 9:16."
            ),
        },
    ]




# =========================================================
# GET CAMPAIGN
# =========================================================

def calculate_campaign_progress(campaign, scenes):
    """
    Derive progress (%) from campaign + scene state.
    Used by GET /campaign/{campaign_id}
    """

    if campaign.status == "video_failed":
        return None

    if campaign.status == "video_queued":
        return 5

    if campaign.status == "veo_generating":
        if not scenes:
            return 30

        total = len(scenes)
        completed = sum(
            1 for s in scenes if s.status == "video_generated"
        )

        return 30 + int((completed / total) * 40)

    if campaign.status == "merging_video":
        return 80

    if campaign.status == "videos_generated":
        return 100

    return 0


@router.get("/campaign/{campaign_id}")
async def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    scenes = (
        db.query(CampaignScene)
        .filter(CampaignScene.campaign_id == campaign_id)
        .order_by(CampaignScene.scene_number)
        .all()
    )
    progress = calculate_campaign_progress(campaign, scenes)

    return {
        "campaign": {
            "id": campaign.id,
            "theme": campaign.campaign_theme,
            "status": campaign.status,
            "progress": f"{progress}%" if progress is not None else None,
            "num_scenes": campaign.num_scenes,
            "product_type": campaign.product_type,
            "character_image_url": campaign.character_image_url,
            "final_video_url": campaign.final_video_url,
            "created_at": campaign.created_at.isoformat(),
        },
        "scenes": [
            {
                "scene_number": s.scene_number,
                "title": s.scene_title,
                "status": s.status,
                "generated_images": s.generated_images,
                "selected_image": s.selected_image_url,
                "video_url": s.video_url,
            }
            for s in scenes
        ],
    }
# =========================================================
# GENERATE CAMPAIGN VIDEOS (ASYNC – CELERY)
# =========================================================

@router.post("/generate_campaign_videos/{campaign_id}")
async def generate_campaign_videos(
    campaign_id: str,
    business_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    website: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Trigger async video generation.
    Heavy work is done by Celery workers.
    """

    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(404, "Campaign not found")

        if not campaign.character_image_url:
            raise HTTPException(400, "Character reference missing")

        scenes = (
            db.query(CampaignScene)
            .filter(CampaignScene.campaign_id == campaign_id)
            .order_by(CampaignScene.scene_number)
            .all()
        )

        scenes_with_images = [
            s for s in scenes
            if s.selected_image_url and s.scene_number <= campaign.num_scenes
        ]

        if not scenes_with_images:
            raise HTTPException(
                400,
                "No images selected. Generate images first using /generate_beauty_campaign."
            )

        # Save optional business info
        campaign.business_name = business_name
        campaign.phone_number = phone_number
        campaign.website = website

        # Mark queued
        campaign.status = "video_queued"
        db.commit()

        # Enqueue Celery job
        from app.tasks.video_tasks import generate_campaign_video_task
        generate_campaign_video_task.delay(campaign_id, business_name, phone_number, website)

        return {
            "status": "video_generation_started",
            "campaign_id": campaign_id,
            "message": "Video is generating. Poll campaign status."
        }

    except HTTPException:
        raise
    # except Exception as e:
    #     db.rollback()
    #     raise HTTPException(500, "Failed to start video generation")

@router.post("/generate_beauty_campaign")
async def generate_beauty_campaign(
    business_type: str,
    campaign_theme: str,
    character_age: Optional[str] = "28-32",
    character_gender: Optional[str] = "woman",
    character_ethnicity: Optional[str] = "indian",
    character_style: Optional[str] = "professional, natural",
    num_scenes: Optional[int] = 3,
    db: Session = Depends(get_db),
):
    """
    Generates character + scene images.
    Video is generated later via Celery.
    """

    campaign_id = f"camp_{uuid.uuid4().hex[:12]}"
    business_key = business_type.lower().strip()

    locked_outfit = LOCKED_OUTFIT_MAP.get(
        business_key,
        "neutral elegant professional outfit, no patterns, no logos"
    )

    try:
        # -------------------------------------------------
        # STEP 1: Generate character
        # -------------------------------------------------
        character_url = await nano_banana_generator.generate_character(
            campaign_id=campaign_id,
            age=character_age,
            gender=character_gender,
            ethnicity=character_ethnicity,
            outfit_prompt=locked_outfit,
        )

        # -------------------------------------------------
        # STEP 2: Define scenes (NO abstraction)
        # -------------------------------------------------
        if business_key in ["nail salon", "nail shop"]:
            base_scenes = nail_salon_scenes(campaign_theme, locked_outfit)

        elif business_key in ["hair salon", "hair shop"]:
            base_scenes = hair_salon_scenes(campaign_theme, locked_outfit)

        elif business_key in ["spa", "spa center"]:
            base_scenes = spa_scenes(campaign_theme, locked_outfit)

        else:
            raise HTTPException(400, f"Business type '{business_type}' not supported")

        scenes = base_scenes[:num_scenes]

        scenes = apply_prompt_optimizations(
            scenes,
            business_type,
            campaign_theme,
            locked_outfit,
        )


    
        # -------------------------------------------------
        # STEP 4: Save campaign
        # -------------------------------------------------
        campaign = Campaign(
            id=campaign_id,
            user_prompt=f"{business_type} {campaign_theme} professional {num_scenes}-scene campaign",
            product_type="beauty",
            character_image_url=character_url,
            campaign_theme=f"{business_type.title()} {campaign_theme}",
            num_scenes=num_scenes,
            status="character_generated",
        )
        db.add(campaign)
        db.commit()

        # -------------------------------------------------
        # STEP 5: Save scenes + generate images
        # -------------------------------------------------
        scene_results = []

        for scene in scenes:
            scene_num = scene["scene_number"]
            scene_id = f"scene_{uuid.uuid4().hex[:12]}"

            # Save pending scene to DB (NO response append)
            record = CampaignScene(
                id=scene_id,
                campaign_id=campaign_id,
                scene_number=scene_num,
                scene_title=scene["title"],
                visual_prompt=scene["prompt"],
                camera_movement=scene["camera_angle"],
                status="pending",
            )
            db.add(record)
            db.commit()

            # Generate image
            image_url = await nano_banana_generator.generate_scene_with_character(
                visual_prompt=scene["prompt"],
                character_image_url=character_url,
                outfit_reference_url=character_url,
                scene_number=scene_num,
                campaign_id=campaign_id,
                product_type="beauty",
                camera_angle=scene["camera_angle"],
            )

            # Update DB
            record.generated_images = [image_url]
            record.selected_image_url = image_url
            record.status = "image_selected"
            db.commit()

            # ✅ Append ONLY final result
            scene_results.append({
                "scene_number": scene_num,
                "title": scene["title"],
                "image": image_url,
                "status": "completed",
            })


        campaign.status = "images_generated"
        db.commit()

        return {
            "status": "images_generated",
            "campaign_id": campaign_id,
            "character_reference_url": character_url,
            "scenes": scene_results,
            "next_step": f"/api/campaign/generate_campaign_videos/{campaign_id}",
        }

    except HTTPException:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        raise
