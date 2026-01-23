from fastapi import APIRouter, Depends, HTTPException, status
import asyncio
import os
import boto3
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.campaign_schemas import SceneScript
from app.models.campaign import Campaign, CampaignScene
from app.services.video_merger import video_merger
from app.services.elevenlabs_tts_service import elevenlabs_tts_service
from app.services.nano_banana_generator import nano_banana_generator
from app.services.veo3_video_generator import veo3_video_generator
from app.services.beauty_prompt_generator import beauty_prompt_generator
import uuid
from typing import Optional

DEMO_MODE = False


# VEO-SAFE MOTION PRESETS (DO NOT EDIT)


VEO_MOTION_PRESETS = {
    "brand": (
        "Subject stands confidently, gentle head movement and blinking. "
        "Slow cinematic camera push-in. Stable framing."
    ),

    "service": (
        "Medium eye-level shot. Person and activity visible together. "
        "Hands move naturally but not close to camera. "
        "Slow, smooth camera push-in."
    ),

    "reaction": (
         "Medium eye-level shot. Subject smiles naturally and blinks. "
         "One hand gently lifts to mid-chest level to subtly display the finished result, "
        "then relaxes. Subtle breathing visible. "
        "Very slow, smooth camera push-in. Stable framing."
    ),

    "cta": (
        "Subject looks confidently toward camera. "
        "Minimal movement with gentle blinking. "
        "Slow push-in. Stable framing."
    ),
}

LOCKED_OUTFIT_MAP = {
    "nail salon": "cream white knit sweater, long sleeves, minimal design, no logos",
    "nail shop": "cream white knit sweater, long sleeves, minimal design, no logos",
    "hair salon": "cream white knit sweater, long sleeves, minimal design, no logos",
    "hair shop": "cream white knit sweater, long sleeves, minimal design, no logos",
    "spa": "white spa robe, clean texture, no patterns",
    "spa center": "white spa robe, clean texture, no patterns",}

router = APIRouter(prefix="/api/campaign", tags=["Campaign"])


# NARRATION HELPERS

def build_narration_from_overlay(text_overlay: dict) -> str:
    if text_overlay is None:
        return ""
    parts = [text_overlay.get("headline"), text_overlay.get("subtext"), text_overlay.get("cta")]
    return ". ".join([p for p in parts if p])


def build_scene_narration(scene_config, business_info):
    parts = []
    text = scene_config.get("text", {})

    if text.get("headline"):
        parts.append(text["headline"])
    if text.get("subtext"):
        parts.append(text["subtext"])
    if text.get("cta"):
        parts.append(text["cta"])

    if business_info:
        if text.get("cta") and business_info.get("phone"):
            parts.append(f"Call us at {business_info['phone']}")
        if text.get("cta") and business_info.get("website"):
            parts.append(f"Visit {business_info['website']}")

    return ". ".join(parts)

def upload_to_s3(local_path: str) -> str:
    """Upload a local file to S3 and return the public URL."""
    s3_bucket = os.getenv("S3_CAMPAIGN_BUCKET", "ai-images-2")
    s3_region = os.getenv("AWS_REGION")
    s3_client = boto3.client(
        "s3",
        region_name=s3_region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    filename = os.path.basename(local_path)
    key = f"campaigns/videos/{filename}"

    s3_client.upload_file(local_path, s3_bucket, key, ExtraArgs={"ContentType": "video/mp4"})

    if s3_region:
        return f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{key}"
    return f"https://{s3_bucket}.s3.amazonaws.com/{key}"

async def generate_video_with_retries(
    generator,  
    *,
    scene_image_url,
    motion_prompt,
    text_overlays,
    campaign_id,
    scene_number,
    business_info,
    product_type="beauty",
    retries=3,
    base_delay=8
):
    last_exc = None

    for attempt in range(1, retries + 1):
        try:
            return await generator.generate_video_with_text(
                scene_image_url=scene_image_url,
                motion_prompt=motion_prompt,
                text_overlays=text_overlays,
                campaign_id=campaign_id,
                scene_number=scene_number,
                business_info=business_info,
                product_type=product_type
            )

        except Exception as e:
            last_exc = e
            msg = str(e).lower()

            if (
                "429" in msg
                or "resource_exhausted" in msg
                or "timeout" in msg
                or "temporar" in msg
            ):
                if attempt < retries:
                    wait = base_delay * (2 ** (attempt - 1))
                    print(
                        f" Attempt {attempt} failed with retryable error, "
                        f"sleeping {wait}s and retrying..."
                    )
                    await asyncio.sleep(wait)
                    continue

            print(f" generate_video_with_retries failed (attempt {attempt}): {e}")
            raise

    raise last_exc



# ENDPOINT 1: Get Campaign Details

@router.get("/campaign/{campaign_id}")
async def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Get campaign details by ID"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(404, f"Campaign {campaign_id} not found")

    # Get all scenes
    scenes = db.query(CampaignScene).filter(
        CampaignScene.campaign_id == campaign_id
    ).order_by(CampaignScene.scene_number).all()

    return {
        "campaign": {
            "id": campaign.id,
            "theme": campaign.campaign_theme,
            "status": campaign.status,
            "num_scenes": campaign.num_scenes,
            "product_type": campaign.product_type,
            "character_image_url": campaign.character_image_url,
            "created_at": campaign.created_at.isoformat()
        },
        "scenes": [
            {
                "scene_number": scene.scene_number,
                "title": scene.scene_title,
                "status": scene.status,
                "generated_images": scene.generated_images,
                "selected_image": scene.selected_image_url,
                "video_url": scene.video_url
            }
            for scene in scenes
        ]
    }




# ENDPOINT 2: NEW Generate Videos (VEO 3 - ACTIVE)

@router.post("/generate_campaign_videos/{campaign_id}")
async def generate_campaign_videos(
    campaign_id: str,
    business_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    website: Optional[str] = None,
    
    db: Session = Depends(get_db)
):
    """
     Generate VEO 3.1 videos with text overlays for campaign
    - 8-second professional videos
    - Text overlays with captions
    - Character consistency
    - Native audio
    -  Automatically merges all scenes into ONE final ad
    """
    
    print("\n" + "="*80)
    print(f" VEO 3.1: GENERATING VIDEOS WITH TEXT")
    print("="*80)
    print(f"Campaign: {campaign_id}")
    if business_name:
        print(f"Business: {business_name}")
    print("="*80)
    
    try:
            
            # GET CAMPAIGN
            
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(404, "Campaign not found")

            if not campaign.character_image_url:
                raise HTTPException(400, "No character reference")

            
            # GET SCENES
            
            scenes = db.query(CampaignScene).filter(
                CampaignScene.campaign_id == campaign_id
            ).order_by(CampaignScene.scene_number).all()
            
            
            # HARD VALIDATION (DO NOT REMOVE)
            
            scenes_with_images = [
                s for s in scenes if s.selected_image_url
            ]
            
            scenes_with_images = [
                s for s in scenes_with_images
                if s.scene_number <= campaign.num_scenes
            ]


            if not scenes_with_images:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "No images selected for this campaign. "
                        "You must generate images first using "
                        "/generate_beauty_campaign and use the SAME campaign_id."
                    )
                )


            if not scenes:
                raise HTTPException(400, "No scenes found")

            print(f" Found {len(scenes)} scenes")
            print(f" Character reference: {campaign.character_image_url[:60]}...")

            business_info = {
                "name": business_name,
                "phone": phone_number,
                "website": website
            } if business_name else None

            
            # SCENE CONFIGS (UNCHANGED)
           
            
            scene_configs = {
                1: {
                    "role": "brand",
                    "text": {
                        "headline": f"Welcome to {business_name}",
                        "subtext": f"{campaign.campaign_theme} Special",
                    },
                },
                2: {
                    "role": "service",
                    "text": {
                        "subtext": "Professional Care",
                    },
                },
                3: {
                    "role": "reaction",
                    "text": {"subtext": "Beautiful Results"},  
                },
                4: {
                    "role": "cta",
                    "text": {
                        "cta": "Book Now",
                    },
                },
            }

            # scene_configs = {
            #     1: {
            #         "type": "brand",
            #         "motion": "Slow cinematic dolly-in toward the subject. Stable eye-level shot.",
            #         "text": {
            #             "headline": f"Welcome to {business_name or 'Our Salon'}",
            #             "subtext": f"{campaign.campaign_theme} Special",
            #         }
            #     },
            #     2:  {
            #         "motion": (
            #             "Medium eye-level shot of a nail technician actively filing and shaping the client’s nails. "
            #             "Hands and tools moving continuously. "
            #             "Client remains relaxed and visible. "
            #             "Camera performs a slow push-in."
            #         ),
            #         "text": {
            #             "subtext": "Professional Care"
            #         }
            #     },
                
                
            #     3: {
            #         "type": "service",
            #         "motion": (
            #             "Close-up service action. "
            #             "Hands actively moving while performing the service. "
            #             "Tools moving naturally. "
            #             "Clear continuous motion. "
            #             "Camera remains stable with slight natural movement."
            #         ),
            #         "text": {}  # 🔥 IMPORTANT: NO TEXT FOR SERVICE SCENE
            #     },
            #     4: {
            #         "type": "emotion",
            #         "motion": "Static close-up.",
            #         "text": {
            #             "headline": f"{campaign.campaign_theme} Magic!",
                        
            #         }
            #     },
            #     5: {
            #         "type": "cta",
            #         "motion": "Static shot.",
            #         "text": {
            #             "headline": f"Happy {campaign.campaign_theme}!",
            #             "subtext": f"From {business_name or 'Us'}",
                        
            #         }
            #     }
            # }
            
            # ================================
            # STEP 1 — GENERATE SCENE VIDEOS + VOICE
            # ================================
            video_results = []
            total_videos = 0
            scene_voice_paths = []

            for scene in scenes_with_images:
                if not scene.selected_image_url:
                    continue

                print(f" Generating Scene {scene.scene_number}")

                scene_config = scene_configs.get(scene.scene_number, scene_configs[1])

                
                # DETERMINE ASPECT RATIO (VEO-SAFE)
                
                aspect_ratio = "16:9"  

                prompt_text = (scene.visual_prompt or "").lower()

                if "9:16" in prompt_text or "portrait" in prompt_text:
                    aspect_ratio = "9:16"

                
                if aspect_ratio not in ["16:9", "9:16"]:
                    print(
                        f"⏭ Skipping Scene {scene.scene_number} — "
                        f"unsupported aspect ratio"
                    )
                    continue

                print(f" Scene {scene.scene_number} forced aspect ratio → {aspect_ratio}")

                
                # FIX 2 — RESOLVE VEO-SAFE MOTION (DO NOT TRUST scene_config)
                
                role = scene_config.get("role", "brand")

                motion_prompt = VEO_MOTION_PRESETS.get(
                    role,
                    VEO_MOTION_PRESETS["brand"]
                )

                text_overlays = scene_config.get("text", {})

                #  Reaction scenes must NOT carry text
                if role == "reaction":
                    text_overlays = {}

                print(f" Scene role → {role}")
                print(f" Motion prompt → {motion_prompt}")

                # ==========================
                # GENERATE VIDEO (VEO)
                # ==========================
                video_url = await generate_video_with_retries(
                    veo3_video_generator,
                    scene_image_url=scene.selected_image_url,
                    motion_prompt=motion_prompt,
                    text_overlays=text_overlays,
                    campaign_id=campaign_id,
                    scene_number=scene.scene_number,
                    business_info=business_info,
                    product_type="beauty",
                    retries=2,
                    base_delay=6
                )


                # -------- Scene-specific narration --------
                narration_text = build_scene_narration(scene_config, business_info) or ""
                print(f" Scene {scene.scene_number} narration:", narration_text)

                voice_path = elevenlabs_tts_service.generate_voice(narration_text)
                scene_voice_paths.append(voice_path)

                video_results.append({
                    "scene_number": scene.scene_number,
                    "video_url": video_url,
                    "status": "completed"
                })
                total_videos += 1


            scene_video_urls = [
                v["video_url"]
                for v in video_results
                if v["status"] == "completed" and v["video_url"]
            ]

            if not scene_video_urls:
                raise HTTPException(400, "No videos generated to merge")


            
            # STEP 2 — FINAL VIDEO PIPELINE
            
            print(" Creating final advertisement")

            final_path = await asyncio.to_thread(
                video_merger.process_full_pipeline,
                scene_video_urls=scene_video_urls,
                voice_paths=scene_voice_paths,   
                campaign_id=campaign_id,
                output_name="final_ad.mp4",
                background_music=None
            )


            
            # STEP 3 — UPLOAD FINAL VIDEO
            
            final_s3_url = await asyncio.to_thread(upload_to_s3, final_path)

            campaign.final_video_url = final_s3_url
            campaign.status = "videos_generated"
            db.commit()

            print(" FINAL VIDEO READY:", final_s3_url)


           
            # RETURN (UI NEEDS ONLY THIS)
           
            return {
                "final_merged_video": final_s3_url
            }


    except HTTPException:
        raise
    except Exception as e:
        print(f"\n ERROR: {str(e)}\n")
        db.rollback()
        raise HTTPException(500, f"Video generation failed: {str(e)}")






# ENDPOINT 8: NEW Beauty Campaign (NANO BANANA + VEO 3 - ACTIVE)

@router.post("/generate_beauty_campaign")
async def generate_beauty_campaign(
    
    
    
    business_type: str,
    campaign_theme: str,
    character_age: Optional[str] = "28-32",
    character_gender: Optional[str] = "woman",
    character_ethnicity: Optional[str] = "indian",
    character_style: Optional[str] = "professional, natural",
    num_scenes: Optional[int] = 3,
    db: Session = Depends(get_db)
):
      
      
   
    #  OUTFIT LOCK 
  
    business_key = business_type.lower().strip()  
    
    locked_outfit = LOCKED_OUTFIT_MAP.get(
        business_key,
            "neutral elegant professional outfit, no patterns, no logos"
    )
    print(f" Locked outfit for all scenes: {locked_outfit}")
    """
     PROFESSIONAL 5-SCENE CAMPAIGNS
    Supports: Nail Shop, Hair Salon, Spa
    Uses: Google Best Practices for prompting
    """
    
    campaign_id = f"camp_{uuid.uuid4().hex[:12]}"
    
    print("\n" + "="*80)
    print(f" {business_type.upper()}: 5-Scene Professional Campaign")
    print("="*80)
    print(f"Theme: {campaign_theme}")
    print(f"Character: {character_gender}, {character_age}, {character_ethnicity}")
    print(f"Campaign ID: {campaign_id}")
    print("="*80)
    
    try:
        # STEP 1: Generate character
        print("\n STEP 1: Generate character reference...")
        character_url = await nano_banana_generator.generate_character(
            campaign_id=campaign_id,
            age=character_age,
            gender=character_gender,
            ethnicity=character_ethnicity,
            outfit_prompt=locked_outfit        )
        
        
        # STEP 2: Get scene definitions based on business type
        print(f"\n STEP 2: Creating {business_type} story...")

 
        
        theme_decor = f"{campaign_theme} themed decorations appropriate for the business environment"

        
    
        


        if business_type.lower() in ["nail shop", "nail salon"]:
            outfit = "cream white knit sweater"
            decor = f"{campaign_theme} decorations, pine garlands, warm string lights, festive wreaths"
            all_scenes = [
                {
                    "scene_number": 1,
                    "title": "Arrival - Entrance",
                    "camera_angle": "Wide shot, full body, eye level",
                    "prompt": (
                        f"Person wearing {locked_outfit}. "
                        f"Wide shot of the person entering a modern nail salon. Full body visible, "
                        f"steady walk, natural smile. Face fully visible and sharp. Clean interior, "
                        f"{decor}. Natural even lighting. Photorealistic, 16:9."
                    )
                },
                {
                   "scene_number": 2,
                    "title": "Welcome - Reception",
                    "camera_angle": "Medium shot, waist-up, eye level",
                    "prompt": (
                        "Medium shot, waist-up of the person at the reception counter. "
                        "Balanced studio + natural lighting (soft key + gentle fill). "
                        "Face fully visible, relaxed expression. Hands may rest naturally but not close to camera. "
                        "Background clean and modern with tasteful {campaign_theme}-themed décor in the background, "
                        "soft warm accents, not overpowering. Photorealistic, 16:9."
                                    )
                },
                {
                    "scene_number": 3,
                    "title": "Service - Manicure",
                    "camera_angle": "Medium close-up, hands visible",
                    "prompt" : (
                        f"Medium eye-level shot of the person after the manicure service. "
                        f"Head and shoulders clearly visible, face sharp, eyes visible, natural confident smile. "
                        f"Hands raised naturally at mid-chest level, fully visible inside the frame, "
                        f"finished nails clearly visible but not close to the camera. "
                        f"Clean professional nail salon background with subtle {campaign_theme}-themed décor. "
                        f"Balanced studio and natural lighting. "
                        f"Photorealistic, 16:9."
                    )
                    
                },
                {
                    "scene_number": 4,
                    "title": "Reveal - Festive Nails",
                    "camera_angle": "Medium close-up, hands shown naturally",
                    "prompt": (
                        f"Medium close-up of person holding hands gently toward camera at chest height (not covering face). "
                        f"Finished nails visible but not blocking face. Clean warm background with {decor}. Photorealistic, 1:1."
                        f" Subtle {campaign_theme}-themed décor in the background, warm and not overpowering."

                    )
                },
                {
                    "scene_number": 5,
                    "title": "Joy - Final Portrait",
                    "camera_angle": "Portrait, shoulders-up",
                    "prompt": (
                        f"Portrait shoulders-up of person smiling with one hand near face (not covering). "
                        f"Face fully visible, soft warm lighting, simple festive background. Photorealistic, 9:16."
                        f" Subtle {campaign_theme}-themed décor in the background, warm and not overpowering."

                    )
                }
            ]
            scenes = all_scenes[:num_scenes]
           
            #  APPLY NANO + VEO OPTIMIZED PROMPTS (BeautyPromptGenerator)

            updated_scenes = []
            for scene_data in scenes:

                # build VEO-safe Nano Banana prompt
                final_prompt = beauty_prompt_generator.generate_scene_prompt(
                    scene_data=scene_data,
                    business_type=business_type,
                    campaign_theme=campaign_theme,
                    character_image_url=None,        
                    aspect_ratio="16:9",
                   
                )

                # override the prompt with the optimized one
                scene_data["prompt"] = (
    f"IMPORTANT: The environment MUST stay the SAME across all scenes. "
    f"Theme: {campaign_theme}. Decorations must remain consistent.\n"
    f"IMPORTANT: The person MUST wear the SAME outfit in ALL scenes: {locked_outfit}. "
    f"Do NOT change clothing, colors, fabric, or style.\n\n"
    f"{final_prompt}"
)



                updated_scenes.append(scene_data)

           
            scenes = updated_scenes



        elif business_type.lower() in ["hair salon", "hair shop"]:
            outfit = "cream white knit sweater"
            decor = f"{campaign_theme} decorations, holiday garlands, warm lights"
            all_scenes = [
                {
                    "scene_number": 1,
                    "title": "Arrival - Entrance",
                    "camera_angle": "Wide shot, full body, eye level",
                    "prompt": (
                        f"Person wearing {outfit}. "
                        f"Wide shot of the person entering an upscale hair salon. Full body visible, natural stride, face clear. "
                        f"Clean décor, {decor}, natural window light. Photorealistic, 16:9."
                    )
                },
                {
                     "scene_number": 2,
                    "title": "Consultation - Chair",
                    "camera_angle": "Medium shot, eye level",
                    "prompt": (
                        "Medium shot of the person seated in a salon chair facing camera. "
                        "Balanced studio + natural lighting (soft key + natural warm fill). "
                        "Face fully visible, no mirrors, no reflections. "
                        "Background clean with tasteful {campaign_theme}-themed décor "
                        "that stays subtle and professional. Photorealistic, 16:9."
                    )
                },
                {
                    "scene_number": 3,
                    "title": "Styling - Motion",
                    "camera_angle": "Medium close-up, straight-on",
                    "prompt": (
                        "Medium close-up of hair gently moving from soft breeze (no hands or tools). "
                        "Face sharp, eyes visible. Lighting balanced warm+natural for commercial beauty. "
                        "Background minimal with subtle {campaign_theme}-themed décor accents. "
                        "Avoid strong blur or dramatic color shifts. Photorealistic, 16:9."
                    )
                },
                {
                    "scene_number": 4,
                    "title": "Reveal - New Style",
                    "camera_angle": "Medium shot, slight angle",
                    "prompt": (
                        f"Medium shot of the person turning head slightly to display hairstyle. Confident natural smile, face visible, "
                        f"{decor} softly in background. Photorealistic, 1:1 or 16:9."
                        f" Subtle {campaign_theme}-themed décor in the background, warm and not overpowering."

                    )
                },
                {
                    "scene_number": 5,
                    "title": "Confidence - Portrait",
                    "camera_angle": "Portrait, shoulders-up",
                    "prompt": (
    "Photorealistic commercial beauty portrait. Shoulders-up, the person smiling softly at the camera. "
    "No hands covering the face. Clean warm background, evenly lit, no reflections, no secondary subjects. "
    "Maintain real human textures. Not illustration, not CGI."
    f" Subtle {campaign_theme}-themed décor in the background, warm and not overpowering."

)

                    
                }
            ]
            scenes = all_scenes[:num_scenes]
           
            #  APPLY NANO + VEO OPTIMIZED PROMPTS (BeautyPromptGenerator)

            updated_scenes = []
            for scene_data in scenes:

                # build VEO-safe Nano Banana prompt
                final_prompt = beauty_prompt_generator.generate_scene_prompt(
                    scene_data=scene_data,
                    business_type=business_type,
                    campaign_theme=campaign_theme,
                    character_image_url=None,       
                    aspect_ratio="16:9"              
                )
 
                # override the prompt with the optimized one
                scene_data["prompt"] = (
    f"IMPORTANT: The environment MUST stay the SAME across all scenes. "
    f"Theme: {campaign_theme}. Decorations must remain consistent.\n"
    f"IMPORTANT: The person MUST wear the SAME outfit in ALL scenes: {locked_outfit}. "
    f"Do NOT change clothing, colors, fabric, or style.\n\n"
    f"{final_prompt}"
)

                updated_scenes.append(scene_data)

           
            scenes = updated_scenes
            


        elif business_type.lower() in ["spa", "spa center"]:
            outfit = "white spa robe"
            decor = f"{campaign_theme} spa decorations, candles, pine branches"
            all_scenes = [
                {
                    "scene_number": 1,
                    "title": "Arrival - Welcome",
                    "camera_angle": "Wide shot, full body, eye level",
                    "prompt": (
                        f"Person wearing {outfit}. "
                        f"Wide shot of the person entering a calm spa reception. Full body visible, relaxed walk, face clear. "
                        f"Soft diffused light, clean zen décor, photorealistic, 16:9."
                    )
                },
                {
                     "scene_number": 2,
                    "title": "Preparation - Treatment Room",
                    "camera_angle": "Medium shot, waist-up",
                    "prompt": (
                        "Medium shot of the person standing near treatment bed, calm posture. "
                        "Balanced soft lighting (spa ambient + warm key). "
                        "Face unobstructed, relaxed expression. "
                        "Background clean spa setting with tasteful {campaign_theme}-themed décor, "
                        "soft warm elements. Photorealistic, 16:9."
                    )
                },
                {
                     "scene_number": 3,
                    "title": "Treatment - Relax",
                    "camera_angle": "Close-up, face visible",
                    "prompt": (
                        "Close-up of person relaxing on treatment bed, face fully visible and softly lit. "
                        "Eyes gently closed. Balanced warm+natural spa lighting. "
                        "Background minimal with subtle {campaign_theme}-themed décor hints. "
        "No deep blur. Photorealistic, 16:9."
                    )
                },
                {
                    "scene_number": 4,
                    "title": "Renewal - Post-Treatment",
                    "camera_angle": "Medium close-up, straight-on",
                    "prompt": (
                        f"Medium close-up of the person gently touching face (not covering) showing refreshed skin. "
                        f"Soft natural light, clean background, photorealistic, 1:1."
                        f" Subtle {campaign_theme}-themed décor in the background, warm and not overpowering."

                    )
                },
                {
                    "scene_number": 5,
                    "title": "Bliss - Portrait",
                    "camera_angle": "Portrait, shoulders-up",
                    "prompt": (
                        f"Portrait shoulders-up of the person smiling with calm expression, hand near face but not occluding. "
                        f"Warm spa background, photorealistic, 9:16."
                        f" Subtle {campaign_theme}-themed décor in the background, warm and not overpowering."

                    )
                }
            ]
            scenes = all_scenes[:num_scenes]
            
            #  APPLY NANO + VEO OPTIMIZED PROMPTS (BeautyPromptGenerator)

            updated_scenes = []
            for scene_data in scenes:

                # build VEO-safe Nano Banana prompt
                final_prompt = beauty_prompt_generator.generate_scene_prompt(
                    scene_data=scene_data,
                    business_type=business_type,
                    campaign_theme=campaign_theme,
                    character_image_url=None,       
                    aspect_ratio="16:9"              
                )

                # override the prompt with the optimized one
                scene_data["prompt"] = (
    f"IMPORTANT: The environment MUST stay the SAME across all scenes. "
    f"Theme: {campaign_theme}. Decorations must remain consistent.\n"
    f"IMPORTANT: The person MUST wear the SAME outfit in ALL scenes: {locked_outfit}. "
    f"Do NOT change clothing, colors, fabric, or style.\n\n"
    f"{final_prompt}"
)

                updated_scenes.append(scene_data)

            
            scenes = updated_scenes
            

        else:
            raise HTTPException(400, f"Business type '{business_type}' not supported")



        
        
        # Saving campaign to database
        campaign = Campaign(
            id=campaign_id,
            user_id=None,
            product_image_url=None,
            character_image_url=character_url,
            user_prompt=f"{business_type} {campaign_theme} professional {num_scenes}-scene campaign",
            num_scenes=num_scenes,
            product_type="beauty",
            campaign_theme=f"{business_type.title()} {campaign_theme}",
            scene_scripts=scenes,
            status="character_generated"
        )
        db.add(campaign)
        
        # Saving individual scenes
        for scene_data in scenes:
            scene = CampaignScene(
                id=f"scene_{uuid.uuid4().hex[:12]}",
                campaign_id=campaign_id,
                scene_number=scene_data["scene_number"],
                scene_title=scene_data["title"],
                visual_prompt=scene_data["prompt"],
                camera_movement=scene_data["camera_angle"],
                lighting=scene_data.get("lighting", "natural"),
                caption_text=scene_data["title"],
                hashtags=[f"#{campaign_theme}", f"#{business_type.replace(' ', '')}"],
                video_duration=5,
                status="pending"
            )
            db.add(scene)
        
        db.commit()
        
        # STEP 3: Generate all scene images
        print(f"\n STEP 3: Generating 5 professional scenes...")
        
        all_scenes_data = []
        total_images = 0
        
        for scene_data in scenes:
            scene_num = scene_data["scene_number"]
            print(f"\n{'='*70}")
            print(f" Scene {scene_num}/5: {scene_data['title']}")
            print(f" Camera: {scene_data['camera_angle']}")
            print(f"{'='*70}")
            
            try:
                # Generate with professional specs
                image_url = await nano_banana_generator.generate_scene_with_character(
                    visual_prompt=scene_data["prompt"],
                    character_image_url=character_url,
                    outfit_reference_url=character_url,
                    scene_number=scene_num,
                    campaign_id=campaign_id,
                    product_type="beauty",
                    camera_angle=scene_data["camera_angle"]
                )
                
                # Update database
                scene_record = db.query(CampaignScene).filter(
                    CampaignScene.campaign_id == campaign_id,
                    CampaignScene.scene_number == scene_num
                ).first()
                
                if scene_record:
                    scene_record.generated_images = [image_url]
                    scene_record.selected_image_url = image_url
                    scene_record.status = "image_selected"
                    db.commit()
                
                all_scenes_data.append({
                    "scene_number": scene_num,
                    "title": scene_data["title"],
                    "camera": scene_data["camera_angle"],
                    "image": image_url,
                    "status": "completed"
                })
                
                total_images += 1
                print(f" Scene {scene_num} complete!")
                
            except Exception as e:
                print(f" Scene {scene_num} failed: {e}")
                all_scenes_data.append({
                    "scene_number": scene_num,
                    "title": scene_data["title"],
                    "camera": scene_data["camera_angle"],
                    "image": None,
                    "status": "failed"
                })
        
        campaign.status = "images_generated"
        db.commit()
        
        print(f"\n{'='*80}")
        print(f" {business_type.upper()} CAMPAIGN COMPLETE!")
        print(f"{'='*80}")
        print(f"Campaign ID: {campaign_id}")
        print(f"Total Images: {total_images}/5")
        print(f"Character Consistency: SAME PERSON + OUTFIT")
        print(f"{'='*80}\n")
        
        return {
                "status": "images_generated",
                "campaign_id": campaign_id,
                "next_step": f"/api/campaign/generate_campaign_videos/{campaign_id}",
                "business_type": business_type,
                "character_reference_url": character_url,
                "scenes": all_scenes_data,
                "total_images": total_images,
                "message": (
                    "Images generated successfully. "
                    "Use the SAME campaign_id for video generation."
                    )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n CRITICAL ERROR: {str(e)}\n")
        
        raise HTTPException(500, f"Campaign failed: {str(e)}")

