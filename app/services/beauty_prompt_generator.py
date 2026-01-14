"""
beauty_prompt_generator.py

Option A + Format 1 (Compact)
- Does NOT overwrite or replace your scene prompt.
- Only adds a short Nano Banana + VEO-safety wrapper.
- Ensures character face visibility, realism, and stable framing.
- Keeps your business_type, theme, outfit, camera-angle EXACT as defined in campaign.py.
"""

from typing import Optional


class BeautyPromptGenerator:
    def __init__(self):
        print("💅 Beauty Prompt Generator (Nano + VEO Safe Wrapper) Loaded")

    def generate_scene_prompt(
        self,
        scene_data: dict,
        business_type: str,
        campaign_theme: str,
        character_image_url: Optional[str] = None,
        aspect_ratio: str = "16:9",
    ) -> str:

        # Your original prompt (exactly as written in campaign.py)
        original_prompt = scene_data.get("prompt", "").strip()

        # ============================
        # Aspect ratio wording (short)
        # ============================
        ar_map = {
            "16:9": "16:9 landscape",
            "9:16": "9:16 vertical",
            "1:1": "1:1 square",
        }
        ar_str = ar_map.get(aspect_ratio, "16:9 landscape")

        # ============================
        # Compact Nano/VEO Safety Add-On
        # (Does NOT overwrite your prompt)
        # ============================
        safety_block = (
            "Photorealistic commercial image. Keep face fully visible and sharp. "
            "No hands blocking face, no distortions, no mirrors, no extra people. "
            "Natural even lighting, stable framing, clean background. "
            f"Composition: {ar_str}. "
            "Real human skin texture, real hair strands, no beauty filters."
        )

        # ===========================================
        # Combine ORIGINAL prompt + compact safe block
        # ===========================================
        final_prompt = f"{original_prompt}\n\n{safety_block}"

        return final_prompt.strip()


# Singleton instance
beauty_prompt_generator = BeautyPromptGenerator()
