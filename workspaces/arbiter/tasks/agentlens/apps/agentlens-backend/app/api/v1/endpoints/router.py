from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.session import get_db
from app.models import models
from app.schemas import schemas

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.get("/ping")
async def ping():
    return {"message": "pong"}

# --- Mock Analytics Endpoints for Frontend Development ---

@router.get("/analytics/summary")
async def get_summary_data() -> Dict[str, Any]:
    return {
        "active_agents": 12,
        "insight_confidence": "88.4%",
        "signals_analyzed": 1240,
        "strategic_alignment": "92.1%",
        "trends": [
            {"label": "+2 this hour", "value": "active_agents"},
            {"label": "+4.2% baseline", "value": "insight_confidence"},
            {"label": "+12.4% vs yesterday", "value": "signals_analyzed"},
            {"label": "+1.2% session", "value": "strategic_alignment"}
        ]
    }

@router.get("/analytics/comparison")
async def get_comparison_data() -> List[Dict[str, Any]]:
    return [
        { "name": "AgentLens™ Pro", "type": "Primary", "scores": [95, 92, 88, 98] },
        { "name": "Competitor Alpha", "type": "Legacy", "scores": [65, 70, 60, 55] },
        { "name": "Competitor Beta", "type": "Emerging", "scores": [78, 82, 85, 70] },
        { "name": "Competitor Gamma", "type": "Niche", "scores": [50, 55, 90, 40] },
    ]

@router.get("/analytics/heatmap")
async def get_heatmap_data() -> List[Dict[str, Any]]:
    return [
        { "feature": "Brand Loyalty", "score": 0.85, "correlation": 0.92 },
        { "feature": "Price Sensitivity", "score": 0.45, "correlation": 0.31 },
        { "feature": "Innovation Perception", "score": 0.72, "correlation": 0.88 },
        { "feature": "Ease of Use", "score": 0.61, "correlation": 0.55 },
        { "feature": "Sustainability", "score": 0.33, "correlation": 0.42 },
        { "feature": "Customer Support", "score": 0.91, "correlation": 0.95 },
        { "feature": "Value Proposition", "score": 0.78, "correlation": 0.81 },
        { "feature": "Digital Presence", "score": 0.55, "correlation": 0.48 },
    ]

@router.get("/workflow/status")
async def get_workflow_status() -> List[Dict[str, Any]]:
    return [
        { "id": 'observer', "name": 'Observer', "status": 'completed', "description": 'Data ingestion & monitoring' },
        { "id": 'architect', "name": 'Architect', "status": 'completed', "description": 'Strategy & hypothesis generation' },
        { "id": 'tester', "name": 'Tester', "status": 'current', "description": 'Active execution & validation' },
        { "id": 'analyst', "name": 'Analyst', "status": 'pending', "description": 'Semantic correlation & scoring' },
        { "id": 'optimizer', "name": 'Optimizer', "status": 'pending', "description': 'Feedback loop & refinement' },
    ]

# --- Brand Endpoints ---

@router.post("/brands", response_model=schemas.Brand, status_code=201)
def create_brand(brand: schemas.BrandCreate, db: Session = Depends(get_db)):
    db_brand = models.Brand(**brand.model_dump())
    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)
    return db_brand

@router.get("/brands", response_model=List[schemas.Brand])
def read_brands(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Brand).offset(skip).limit(limit).all()

@router.get("/brands/{brand_id}", response_model=schemas.Brand)
def read_brand(brand_id: int, db: Session = Depends(get_db)):
    db_brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return db_brand

# --- Intent Endpoints ---

@router.post("/intents", response_model=schemas.Intent, status_code=201)
def create_intent(intent: schemas.IntentCreate, db: Session = Depends(get_db)):
    db_intent = models.Intent(**intent.model_dump())
    db.add(db_intent)
    db.commit()
    db.refresh(db_intent)
    return db_intent

@router.get("/intents/brand/{brand_id}", response_model=List[schemas.Intent])
def read_intents_by_brand(brand_id: int, db: Session = Depends(get_db)):
    return db.query(models.Intent).filter(models.Intent.brand_id == brand_id).all()
