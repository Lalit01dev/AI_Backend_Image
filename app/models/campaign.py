from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Boolean
from app.database import Base
from datetime import datetime


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)  
    
    # Input data
    product_image_url = Column(String, nullable=True) 
    character_image_url = Column(String, nullable=True)
    user_prompt = Column(Text, nullable=False)
    num_scenes = Column(Integer, default=4)
    product_type = Column(String, default="default")  
    
    # Generated data
    campaign_theme = Column(String, nullable=True)
    scene_scripts = Column(JSON, nullable=True)  
    
    # Video output
    final_video_url = Column(String, nullable=True)
    generation_error = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String, default="pending")  
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
    visual_prompt = Column(Text, nullable=True)  
    camera_movement = Column(String, nullable=True)
    lighting = Column(String, nullable=True)
    
    # Generated images
    generated_images = Column(JSON, nullable=True)  
    selected_image_url = Column(String, nullable=True)  
    
    # Video data
    video_prompt = Column(Text, nullable=True)  
    video_duration = Column(Integer, default=5)  
    video_url = Column(String, nullable=True)  
    runway_task_id = Column(String, nullable=True)  
    
    # Captions
    caption_text = Column(String, nullable=True)
    hashtags = Column(JSON, nullable=True)  
    
    # Status
    status = Column(String, default="pending")  
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CampaignOutput(Base):
    __tablename__ = "campaign_outputs"
    
    id = Column(String, primary_key=True)
    campaign_id = Column(String, nullable=False)
    
    # Individual scene videos
    scene_video_urls = Column(JSON, nullable=True)  
    
    # Merged final ad
    final_ad_url = Column(String, nullable=True)
    final_ad_duration = Column(Integer, nullable=True)
    
    # Status
    status = Column(String, default="pending")  
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
