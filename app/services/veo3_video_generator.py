from google import genai
from google.genai import types
import os
import time
import asyncio
from typing import Optional, Dict
import boto3
from botocore.config import Config
import io
from PIL import Image as PILImage
from urllib.parse import urlparse


class VEO3VideoGenerator:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("GEMINI_API_KEY not found")

        self.client = genai.Client(api_key=api_key)
        self.model_name = "veo-3.1-generate-preview"

        self.s3_bucket = os.getenv("S3_CAMPAIGN_BUCKET", "ai-images-2")
        self.s3_region = os.getenv("AWS_REGION", "us-east-1")

        self.s3_client = boto3.client(
            "s3",
            region_name=self.s3_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
        )

        print(" VEO 3.1 Generator Loaded — RAW IMAGE BYTES MODE")

    # ------------------------------------------------------------------
    # IMAGE LOADER — S3 → JPEG BYTES (VEO SAFE)
    # ------------------------------------------------------------------
    def _get_image_bytes_from_s3(self, s3_key: str) -> bytes:
        response = self.s3_client.get_object(
            Bucket=self.s3_bucket,
            Key=s3_key
        )
        raw_bytes = response["Body"].read()

        img = PILImage.open(io.BytesIO(raw_bytes))

        # Ensure RGB (important for PNG / CMYK safety)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize to VEO-friendly size (keeps payload small)
        img.thumbnail((1280, 720))

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    # MAIN VIDEO GENERATION
    # ------------------------------------------------------------------
    async def generate_video_with_text(
        self,
        scene_image_url: str,   # can be S3 key or full S3 URL
        motion_prompt: str,
        text_overlays: Dict,
        campaign_id: str,
        scene_number: int,
        business_info: Optional[Dict] = None,
        product_type: str = "beauty",
    ) -> str:

        print(f"\n🎬 Generating Scene {scene_number}")

        # Accept both full URL or key
        if scene_image_url.startswith("http"):
            parsed_url = urlparse(scene_image_url)
            s3_key = parsed_url.path.lstrip("/")

            # Handle path-style URLs (safety)
            if s3_key.startswith(f"{self.s3_bucket}/"):
                s3_key = s3_key.replace(f"{self.s3_bucket}/", "", 1)
        else:
            s3_key = scene_image_url

        print(f" Corrected S3 Key: {s3_key}")

        #  KEY CHANGE: load bytes, not URL
        image_bytes = self._get_image_bytes_from_s3(s3_key)

        reference_image = types.VideoGenerationReferenceImage(
            image=types.Image(
            image_bytes=image_bytes,
            mime_type="image/jpeg"  
        ),
        reference_type="asset",
        )

        final_prompt = self._build_veo_prompt(
            motion_prompt,
            text_overlays,
            business_info
        )

        operation = await asyncio.to_thread(
            self.client.models.generate_videos,
            model=self.model_name,
            prompt=final_prompt,
            config=types.GenerateVideosConfig(
                reference_images=[reference_image],
                aspect_ratio="16:9",
            ),
        )

        print(" Operation started:", getattr(operation, "name", "N/A"))

        start = time.time()
        while not operation.done:
            elapsed = int(time.time() - start)
            print(f"   [{elapsed}s] VEO generating...")
            await asyncio.sleep(10)
            operation = await asyncio.to_thread(
                self.client.operations.get, operation
            )
            if elapsed > 480:
                raise Exception("VEO generation timed out")

        if getattr(operation, "error", None):
            raise Exception(f"VEO Error: {operation.error}")

        videos = operation.response.generated_videos
        if not videos:
            raise Exception("No videos generated")

        video_obj = videos[0].video
        video_bytes = await asyncio.to_thread(
            self.client.files.download,
            file=video_obj
        )

        url = await self._upload_to_s3(
            video_bytes, campaign_id, scene_number, product_type
        )

        print(" VIDEO READY →", url)
        return url

    # ------------------------------------------------------------------
    # PROMPT BUILDER — SCENE LOCKED
    # ------------------------------------------------------------------
    def _build_veo_prompt(self, motion_prompt, text_overlays, business_info):
        parts = [
            "Animate this exact image.",
            "Keep the same person, same outfit, same background.",
            motion_prompt,
        ]

        if text_overlays:
            if text_overlays.get("headline"):
                parts.append(f"Show text '{text_overlays['headline']}' centered.")
            if text_overlays.get("subtext"):
                parts.append(f"Show subtext '{text_overlays['subtext']}'.")
            if text_overlays.get("cta"):
                parts.append(f"Show CTA '{text_overlays['cta']}' bottom.")

        if business_info and business_info.get("name"):
            parts.append(
                f"Add small watermark '{business_info['name']}' bottom-left."
            )

        parts.append("No camera shake. No blur. Subtle natural movement only.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # S3 VIDEO UPLOAD (UNCHANGED)
    # ------------------------------------------------------------------
    async def _upload_to_s3(
        self, video_bytes, campaign_id, scene_number, product_type
    ):
        key = f"campaigns/{product_type}/{campaign_id}/scene_{scene_number}_video.mp4"

        await asyncio.to_thread(
            self.s3_client.put_object,
            Bucket=self.s3_bucket,
            Key=key,
            Body=video_bytes,
            ContentType="video/mp4",
        )

        return f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{key}"


# Singleton
veo3_video_generator = VEO3VideoGenerator()
