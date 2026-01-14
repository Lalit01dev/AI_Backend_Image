from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== REQUEST SCHEMAS ====================


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


# ==================== RESPONSE SCHEMAS ====================


class SceneScript(BaseModel):
    """Individual scene description"""
    scene_number: int
    title: str
    visual_prompt: str  # For Midjourney
    camera_movement: str
    lighting: str
    background: str
    caption_text: str
    hashtags: List[str]
    duration: int = 5  # Default 5 seconds
    
    class Config:
        json_schema_extra = {
            "example": {
                "scene_number": 1,
                "title": "Golden Hour Hero Shot",
                "visual_prompt": "Ultra-realistic close-up of gourmet ice cream bowl...",
                "camera_movement": "Slow push-in zoom",
                "lighting": "Warm golden hour, soft backlight",
                "background": "Blurred outdoor cafe setting",
                "caption_text": "Pure Indulgence Begins Here ✨",
                "hashtags": ["#IceCreamLovers", "#GoldenHour", "#DessertGoals"],
                "duration": 5
            }
        }


class CampaignScriptResponse(BaseModel):
    """Complete campaign script with all scenes"""
    status: str
    campaign_id: str
    campaign_theme: str
    color_palette: List[str]
    scenes: List[SceneScript]
    estimated_duration: int  # Total seconds
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "scripts_generated",
                "campaign_id": "camp_abc123",
                "campaign_theme": "Golden Hour Indulgence",
                "color_palette": ["#FFD700", "#FFA500", "#FFFFFF"],
                "scenes": [],
                "estimated_duration": 20,
                "message": "Campaign scripts generated successfully"
            }
        }


# ==================== PHASE 2: IMAGE GENERATION ====================


class ImageGenerationRequest(BaseModel):
    """Request to generate images for a campaign - always generates 4 images per scene"""
    campaign_id: str = Field(..., description="Campaign ID from Phase 1")
    
    class Config:
        json_schema_extra = {
            "example": {
                "campaign_id": "camp_abc123"
            }
        }


class SceneImageResponse(BaseModel):
    """Response for a single scene's generated images"""
    scene_number: int
    scene_title: str
    generated_images: List[str]  # S3 URLs (always 4 images)
    status: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "scene_number": 1,
                "scene_title": "Hero Close-up Shot",
                "generated_images": [
                    "https://ai-images-2.s3.amazonaws.com/scene1_option1.png",
                    "https://ai-images-2.s3.amazonaws.com/scene1_option2.png",
                    "https://ai-images-2.s3.amazonaws.com/scene1_option3.png",
                    "https://ai-images-2.s3.amazonaws.com/scene1_option4.png"
                ],
                "status": "completed"
            }
        }


class ImageGenerationResponse(BaseModel):
    """Response after generating all scene images"""
    status: str
    campaign_id: str
    scenes: List[SceneImageResponse]
    total_images: int
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "images_generated",
                "campaign_id": "camp_abc123",
                "scenes": [],
                "total_images": 16,
                "message": "All scene images generated successfully"
            }
        }


class ImageSelectionRequest(BaseModel):
    """Request to select image for video generation"""
    campaign_id: str
    scene_number: int
    selected_image_url: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "campaign_id": "camp_abc123",
                "scene_number": 1,
                "selected_image_url": "https://ai-images-2.s3.amazonaws.com/scene1_option2.png"
            }
        }


# ==================== PHASE 3: VIDEO GENERATION ====================


class VideoGenerationRequest(BaseModel):
    """Request to generate videos for a campaign"""
    campaign_id: str = Field(..., description="Campaign ID from Phase 2")
    
    class Config:
        json_schema_extra = {
            "example": {
                "campaign_id": "camp_abc123"
            }
        }


class SceneVideoResponse(BaseModel):
    """Response for a single scene's generated video"""
    scene_number: int
    scene_title: str
    video_prompt: str
    video_url: Optional[str] = None
    status: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "scene_number": 1,
                "scene_title": "Hero Shot",
                "video_prompt": "Camera slowly zooms in, man smiles...",
                "video_url": "https://ai-images-2.s3.amazonaws.com/campaigns/camp_xxx/scene_1_video.mp4",
                "status": "completed"
            }
        }


class VideoGenerationResponse(BaseModel):
    """Response after generating all scene videos"""
    status: str
    campaign_id: str
    scenes: List[SceneVideoResponse]
    total_videos: int
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "videos_generated",
                "campaign_id": "camp_abc123",
                "scenes": [],
                "total_videos": 4,
                "message": "All scene videos generated successfully"
            }
        }
