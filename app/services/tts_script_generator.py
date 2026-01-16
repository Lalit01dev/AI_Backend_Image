"""
tts_script_generator.py

Generates short, professional voiceover scripts for ads.
Optimized for ElevenLabs (natural, human-like narration).
Visuals and audio are fully decoupled (no lip-sync).
"""

import random
from typing import Dict


class TTSScriptGenerator:
    """
    Generates narration text based on business type and campaign theme.
    Output is intentionally short, natural, and ad-friendly.
    """

    def __init__(self):
        print("TTS Script Generator initialized (ElevenLabs mode)")

    def generate_narration(
        self,
        business_type: str,
        campaign_theme: str,
        duration_seconds: int = 12
    ) -> Dict[str, str]:
        """
        Generate a short narration script.

        Returns:
            {
                "text": "...",
                "style": "calm / confident / elegant",
                "estimated_duration_sec": int
            }
        """

        bt = business_type.lower()

        if "nail" in bt:
            lines = [
                "Beautiful nails begin with expert care and attention.",
                "Step into a space where detail, comfort, and elegance come together.",
                "Because your nails deserve professional care and a perfect finish."
            ]
            style = "warm, confident, elegant"

        elif "hair" in bt:
            lines = [
                "Every great style starts with expert hands and creative vision.",
                "Discover a look that reflects confidence and individuality.",
                "Because great hair is more than style. It’s a statement."
            ]
            style = "confident, modern, stylish"

        elif "spa" in bt:
            lines = [
                "Relax, unwind, and let your senses reset.",
                "Experience calm, care, and comfort designed just for you.",
                "Because true beauty begins with relaxation."
            ]
            style = "calm, soothing, gentle"

        else:
            lines = [
                "Experience professional care crafted with attention and quality.",
                "A place where comfort meets expertise.",
                "Designed to help you look and feel your best."
            ]
            style = "neutral, professional"

        # Pick 2 lines → short, ad-friendly
        selected = random.sample(lines, k=2)

        #  Duration-safe narration (prevents voice overlap)
        
        words_per_sec = 2.2  # natural speaking rate
        max_words = int(duration_seconds * words_per_sec)

        narration_words = " ".join(selected).split()
        narration_text = " ".join(narration_words[:max_words])

        return {
            "text": narration_text,
            "style": style,
            "estimated_duration_sec": duration_seconds
        }




tts_script_generator = TTSScriptGenerator()
