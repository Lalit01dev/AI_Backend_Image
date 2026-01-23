from pydantic import BaseModel, Field
from typing import Optional, List



class CampaignCreateRequest(BaseModel):
    """User's initial campaign request"""
    product_image_url: str = Field(..., description="S3 URL of product image")
    character_image_url: Optional[str] = Field(None, description="S3 URL of character/model image")
    user_prompt: str = Field(..., description="User's simple description")
    num_scenes: int = Field(4, ge=2, le=10, description="Number of scenes")
    product_type: str = Field("default", description="Product category for organization (e.g., sunglasses, watch)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_image_url": "https://ai-images-2.s3.amazonaws.com/product.png",
                "character_image_url": "https://ai-images-2.s3.amazonaws.com/model.png",
                "user_prompt": "Create a stylish sunglasses ad with golden hour lighting",
                "num_scenes": 4,
                "product_type": "sunglasses"
            }
        }


class SceneScript(BaseModel):
    """Individual scene description"""
    scene_number: int
    title: str
    visual_prompt: str  
    camera_movement: str
    lighting: str
    background: str
    caption_text: str
    hashtags: List[str]
    duration: int = 5  
    
    class Config:
        json_schema_extra = {
            "example": {
                "scene_number": 1,
                "title": "Golden Hour Hero Shot",
                "visual_prompt": "Ultra-realistic close-up of gourmet ice cream bowl...",
                "camera_movement": "Slow push-in zoom",
                "lighting": "Warm golden hour, soft backlight",
                "background": "Blurred outdoor cafe setting",
                "caption_text": "Pure Indulgence Begins Here ",
                "hashtags": ["#IceCreamLovers", "#GoldenHour", "#DessertGoals"],
                "duration": 5
            }
        }

