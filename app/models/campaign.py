from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Boolean
from app.database import Base
from datetime import datetime


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)  # No auth for now
    
    # Input data
    product_image_url = Column(String, nullable=True)  # ✅ CHANGED: nullable=True (for beauty campaigns without products)
    character_image_url = Column(String, nullable=True)
    user_prompt = Column(Text, nullable=False)
    num_scenes = Column(Integer, default=4)
    product_type = Column(String, default="default")  # default, beauty, sunglasses, watch, etc.
    
    # Generated data
    campaign_theme = Column(String, nullable=True)
    scene_scripts = Column(JSON, nullable=True)  # Array of scene descriptions
    
    # Status tracking
    status = Column(String, default="pending")  # pending, scripts_generated, character_generated, images_generated, images_partial, videos_generated, completed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CampaignScene(Base):
    __tablename__ = "campaign_scenes"
    
    id = Column(String, primary_key=True)
    campaign_id = Column(String, nullable=False)
    scene_number = Column(Integer, nullable=False)
    
    # Scene data
    scene_title = Column(String, nullable=True)
    visual_prompt = Column(Text, nullable=True)  # For Midjourney
    camera_movement = Column(String, nullable=True)
    lighting = Column(String, nullable=True)
    
    # Generated images
    generated_images = Column(JSON, nullable=True)  # Array of S3 URLs (4 images per scene)
    selected_image_url = Column(String, nullable=True)  # User's choice (1 selected from 4)
    
    # Video data
    video_prompt = Column(Text, nullable=True)  # For Runway
    video_duration = Column(Integer, default=5)  # seconds
    video_url = Column(String, nullable=True)  # Final video S3 URL
    runway_task_id = Column(String, nullable=True)  # Runway job ID for polling
    
    # Captions
    caption_text = Column(String, nullable=True)
    hashtags = Column(JSON, nullable=True)  # Array of hashtags
    
    # Status
    status = Column(String, default="pending")  # pending, images_generated, image_selected, video_generated, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CampaignOutput(Base):
    __tablename__ = "campaign_outputs"
    
    id = Column(String, primary_key=True)
    campaign_id = Column(String, nullable=False)
    
    # Individual scene videos
    scene_video_urls = Column(JSON, nullable=True)  # Array of URLs
    
    # Merged final ad
    final_ad_url = Column(String, nullable=True)
    final_ad_duration = Column(Integer, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, processing, completed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
