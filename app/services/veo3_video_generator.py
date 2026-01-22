from google import genai
from google.genai.types import Blob, Part
import os
import time
import asyncio
from typing import Optional, Dict
from PIL import Image
from io import BytesIO
import boto3
import requests
import tempfile


class VEO3VideoGenerator:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("GEMINI_API_KEY not found")

        self.client = genai.Client(api_key=api_key)
        self.model_name = "veo-3.1-generate-preview"

        self.s3_bucket = os.getenv("S3_CAMPAIGN_BUCKET", "ai-images-2")
        self.s3_region = os.getenv("AWS_REGION")
        self.s3_client = boto3.client(
            "s3",
            region_name=self.s3_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        print(" VEO 3.1 Generator Loaded — SCENE IMAGE MODE ONLY")


    # =====================================================================
    # MAIN VIDEO GENERATION
    # =====================================================================
    
    
    
    async def generate_video_with_text(
        self,
        scene_image_url: str,
        motion_prompt: str,
        text_overlays: Dict,
        campaign_id: str,
        scene_number: int,
        business_info: Optional[Dict] = None,
        product_type: str = "beauty",
    ) -> str:

        print(f"\n Generating Scene {scene_number}")

        print(" Downloading scene image...")
        resp = await asyncio.to_thread(requests.get, scene_image_url, timeout=30)
        resp.raise_for_status()

        pil_img = Image.open(BytesIO(resp.content)).convert("RGB")
            # ✅ 2. SAFE RESIZE (AFTER load)
        MAX_SIZE = 1024
        width, height = pil_img.size

        if max(width, height) > MAX_SIZE:
            scale = MAX_SIZE / max(width, height)
            new_size = (int(width * scale), int(height * scale))
            pil_img = pil_img.resize(new_size)
            buf = BytesIO()
            pil_img.save(buf, format="JPEG")
        
         # ✅ 3. ENCODE JPEG (OPTIMIZED)
        buf = BytesIO()
        pil_img.save(buf, format="JPEG", quality=85, optimize=True)
        img_bytes = buf.getvalue()    

        image_part = Part(
            inline_data=Blob(
                data=img_bytes,
                mime_type="image/jpeg"
            )
        ).as_image()

        final_prompt = self._build_veo_prompt(
            motion_prompt,
            text_overlays,
            business_info
        )

        print(" VEO Prompt:")
        print(final_prompt)

        operation = await asyncio.to_thread(
            self.client.models.generate_videos,
            model=self.model_name,
            prompt=final_prompt,
            image=image_part   
        )

        print(" Operation:", getattr(operation, "name", "N/A"))

        start = time.time()
        while not operation.done:
            elapsed = int(time.time() - start)
            print(f"   [{elapsed}s] Generating...")
            await asyncio.sleep(10)
            operation = await asyncio.to_thread(
                self.client.operations.get, operation
            )
            if elapsed > 360:
                raise Exception("VEO timed out")

        if getattr(operation, "error", None):
            raise Exception(operation.error)

        videos = operation.response.generated_videos
        if not videos:
            raise Exception("No videos generated")

        video_obj = videos[0].video
        await asyncio.to_thread(self.client.files.download, file=video_obj)

        tmp = tempfile.mktemp(suffix=".mp4")
        video_obj.save(tmp)

        with open(tmp, "rb") as f:
            data = f.read()
        os.remove(tmp)

        url = await self._upload_to_s3(
            data, campaign_id, scene_number, product_type
        )

        print(" VIDEO READY →", url)
        return url


    # =====================================================================
    # PROMPT BUILDER — SCENE-LOCKED
    # =====================================================================
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


   
    # S3 UPLOAD
  
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


veo3_video_generator = VEO3VideoGenerator()
