"""
Nano Banana Image Generator (FINAL — OUTFIT & FACE LOCKED)
Fully compliant with Nano Banana + VEO requirements.

Key Guarantees:
- SAME face across all scenes
- SAME outfit across all scenes
- Outfit locked via IMAGE, not text
- VEO-safe composition (no occlusion, no close hands)
- Works with beauty_prompt_generator output
"""

from google import genai
from google.genai import types
import os
import asyncio
from typing import Optional
from PIL import Image
from io import BytesIO
import requests
import boto3


class NanoBananaGenerator:
    """Google Nano Banana — VEO-safe Image Generator"""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("GEMINI_API_KEY missing")

        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash-image"

        # S3 setup
        self.s3_bucket = os.getenv("S3_CAMPAIGN_BUCKET", "ai-images-2")
        self.s3_region = os.getenv("AWS_REGION")
        self.s3_client = boto3.client(
            "s3",
            region_name=self.s3_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        print(" Nano Banana (FACE + OUTFIT LOCKED) initialized")

    # -------------------------------------------------------------
    # Utility: Convert Gemini output → PIL image
    # -------------------------------------------------------------
    def _to_pil(self, part) -> Image.Image:
        if part.inline_data is None:
            raise Exception("No inline image data found")
        return Image.open(BytesIO(part.inline_data.data)).convert("RGBA")

    # -------------------------------------------------------------
    # Upload to S3
    # -------------------------------------------------------------
    async def _upload(self, campaign_id: str, filename: str, image: Image.Image, folder: str) -> str:
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)

        key = f"campaigns/{folder}/{campaign_id}/{filename}.png"

        await asyncio.to_thread(
            self.s3_client.upload_fileobj,
            buffer,
            self.s3_bucket,
            key,
            ExtraArgs={"ContentType": "image/png"}
        )

        if self.s3_region:
            return f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{key}"
        return f"https://{self.s3_bucket}.s3.amazonaws.com/{key}"


    # CHARACTER GENERATION (MASTER REFERENCE)
 
    async def generate_character(
        self,
        campaign_id: str,
        age: str,
        gender: str,
        ethnicity: str,
        outfit_prompt: str,   
    ) -> str:
        print("\n================ CHARACTER REFERENCE =================")

        prompt = (
            "CRITICAL CHARACTER + OUTFIT CANONICAL REFERENCE IMAGE.\n\n"

            f"Cinematic medium shot (Cowboy shot) of a {age} {gender} "
            f"with {ethnicity} features.\n\n"

            "OUTFIT — ABSOLUTELY LOCKED:\n"
            f"{outfit_prompt}.\n"
            "This exact outfit must be worn.\n"
            "Do NOT change clothing, color, fabric, neckline, sleeves, or fit.\n"
            "No accessories, no jewelry, no patterns, no logos.\n\n"

            "POSE & FRAMING:\n"
            "- Subject centered with breathing room on sides\n"
            "- Thighs-up visible (Cowboy shot)\n" 
            "- Neutral relaxed posture\n\n"

            "LIGHTING & STYLE:\n"
            "- Soft even studio lighting\n"
            "- Neutral background (blurred studio depth)\n"
            "- Photorealistic, real human\n"
            "- No stylization, no CGI, no AI look\n"
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(response_modalities=["image"],
            image_config=types.ImageConfig(
            aspect_ratio="16:9")                                   
                                               
                                               
                                               ),
        )

        img = None
        for p in response.parts:
            if p.inline_data:
                img = self._to_pil(p)
                break

        if img is None:
            raise Exception("Character image generation failed")

        return await self._upload(
            campaign_id,
            "character_reference",
            img,
            folder="characters"
        )


    # -------------------------------------------------------------
    # SCENE GENERATION (FACE + OUTFIT LOCKED)
    # -------------------------------------------------------------
    async def generate_scene_with_character(
        self,
        visual_prompt: str,
        character_image_url: str,
        scene_number: int,
        campaign_id: str,
        product_type: str = "beauty",
        camera_angle: str = "eye level",
        outfit_reference_url: Optional[str] = None,
    ) -> str:
        """
        Generates scene image with:
        - face locked
        - outfit locked
        - VEO-safe framing
        """

        print(f"\n================ SCENE {scene_number} =================")

        # --------------------------------------------------
        # 1. Download reference images
        # --------------------------------------------------
        ref_face = await asyncio.to_thread(requests.get, character_image_url, timeout=30)
        ref_face.raise_for_status()
        face_img = Image.open(BytesIO(ref_face.content)).convert("RGB")

        outfit_img = None
        if outfit_reference_url:
            ref_outfit = await asyncio.to_thread(requests.get, outfit_reference_url, timeout=30)
            ref_outfit.raise_for_status()
            outfit_img = Image.open(BytesIO(ref_outfit.content)).convert("RGB")

        # --------------------------------------------------
        # 2. VEO-safe concise prompt (TEXT ONLY)
        # --------------------------------------------------
        prompt_text = (
    "CRITICAL IDENTITY + OUTFIT LOCK — NO DEVIATION ALLOWED.\n\n"

    "IDENTITY RULES:\n"
    "- Must be the EXACT SAME PERSON as reference image\n"
    "- Same face, same facial structure, same skin tone\n"
    "- No beautification, no stylization\n\n"

    "OUTFIT RULES:\n"
    "- Wear the EXACT SAME outfit as reference image\n"
    "- Same clothing, same color, same fabric\n"
    "- No changes to neckline, sleeves, or fit\n"
    "- No new accessories\n\n"

    "VISIBILITY RULES:\n"
    "- Face fully visible\n"
    "- No hands near face\n"
    "- No occlusion\n"
    "- No extreme angles\n\n"

    f"Camera angle: {camera_angle}.\n"
    f"{visual_prompt}\n\n"

    "STYLE:\n"
    "Photorealistic professional advertisement photo.\n"
    "Real human, natural lighting, no CGI."
)

        print("Prompt:", prompt_text[:200], "...")

        # --------------------------------------------------
        # 3. Gemini call — IMAGE INGREDIENTS (CRITICAL)
        # --------------------------------------------------
        contents = [prompt_text, face_img]

        #  OUTFIT LOCK — THIS IS THE FIX
        if outfit_img:
            contents.append(outfit_img)

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["image"],
            image_config=types.ImageConfig(
            aspect_ratio="16:9" 
        )
    ),
)
        # --------------------------------------------------
        # 4. Extract image
        # --------------------------------------------------
        img = None
        for part in response.parts:
            if getattr(part, "inline_data", None):
                img = self._to_pil(part)
                break

        if img is None:
            raise Exception("Scene image missing from Gemini response")

        # --------------------------------------------------
        # 5. Upload
        # --------------------------------------------------
        return await self._upload(
            campaign_id,
            f"scene_{scene_number}_image",
            img,
            folder=product_type,
        )


# Singleton
nano_banana_generator = NanoBananaGenerator()
