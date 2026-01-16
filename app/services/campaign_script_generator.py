class BeautyPromptGenerator:
    """
    Generates photorealistic scene prompts optimized for Gemini image generation
    and stable VEO 3.1 video motion.

    - Clean framing
    - No blur / no bokeh
    - Face always visible
    - Hands never blocking face
    - VEO-safe layouts for stable video animation
    """

    def __init__(self):
        print("Beauty Prompt Generator initialized")

    def generate_scene_prompt(
        self,
        scene_data: dict,
        business_type: str,
        campaign_theme: str,
        character_image_url: str
    ) -> str:
        """
        Convert script scene to a VEO-safe Gemini image prompt.

        Args:
            scene_data: Parsed scene from your script generator
            business_type: nail salon, hair salon, spa, etc.
            campaign_theme: Christmas, Valentine’s, Summer, etc.
            character_image_url: S3 character reference (for consistency)

        Returns:
            A clean, safe, realistic prompt for image generation.
        """

        scene_num = scene_data["scene_number"]
        mood = scene_data["mood"]

        
        # VEO-SAFE SCENE PROMPTS
       
        scene_prompts = {
            1: (
                "Wide shot of the woman entering a modern nail salon. "
                "Full body visible, natural step forward, warm smile. "
                "Face clearly visible and sharp. "
                "Bright clean lighting with a simple background."
            ),

            2: (
                "Medium shot of the woman standing at the reception desk. "
                "Waist-up framing, friendly expression. "
                "Face fully visible with soft warm lighting. "
                "Background clean and minimal, no clutter, no blur."
            ),

            3: (
                "Medium close-up of the woman at a manicure station. "
                "Hands resting naturally on a cushion, not too close to the camera. "
                "Face visible in clear focus. "
                "Soft even lighting. No blur, no bokeh."
            ),

            4: (
                "Medium close-up of the woman gently showing her finished nails. "
                "Hands at chest height, not blocking the face. "
                "Face fully visible and sharp. "
                "Clean festive background with subtle decorations."
            ),

            5: (
                "Portrait shot of the woman smiling with one hand near her face. "
                "Shoulders-up framing. "
                "Face clearly visible with warm balanced lighting. "
                "Clean festive background with gentle glow."
            ),
        }

        # Select prompt for the scene
        veo_scene_description = scene_prompts.get(scene_num)

        
        # Base prompt (optimized for Gemini)
    
        final_prompt = f"""
Photorealistic commercial beauty photograph.

SCENE DESCRIPTION:
{veo_scene_description}

THEME:
Subtle {campaign_theme} decorations and ambience.

BUSINESS TYPE:
{business_type}

MOOD:
{mood}

VISUAL REQUIREMENTS:
- Real human appearance with natural skin texture
- Face fully visible and sharp
- Clear eyes and natural expression
- Balanced soft lighting (no harsh shadows)
- Clean background with minimal elements
- No extreme poses
- No blur, no bokeh, no cinematic depth-of-field
- No artistic filters or stylization
- Realistic hair, clothing, and environment

AVOID:
- Hands covering the face
- Overly dramatic lighting
- Extreme close-ups
- CGI, cartoon, unrealistic skin
- Any soft-focus or fake blur

Maintain consistent appearance using this reference:
{character_image_url}
"""

        return final_prompt.strip()


# Singleton instance
beauty_prompt_generator = BeautyPromptGenerator()
