from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class BrandBase(BaseModel):
    name: str
    category: Optional[str] = None

class BrandCreate(BrandBase):
    pass

class Brand(BrandBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class IntentBase(BaseModel):
    query: str
    category: Optional[str] = None

class IntentCreate(IntentBase):
    brand_id: int

class Intent(IntentBase):
    id: int
    brand_id: int
    visibility_score: int
    sentiment_score: int
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
