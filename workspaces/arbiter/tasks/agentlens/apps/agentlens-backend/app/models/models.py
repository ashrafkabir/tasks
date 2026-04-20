from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    intents = relationship("Intent", back_populates="brand")

class Intent(Base):
    __tablename__ = "intents"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"))
    query = Column(String, nullable=False)
    category = Column(String, nullable=True)
    
    # Store raw JSON results from search/reddit
    raw_data = Column(JSON, nullable=True)
    
    # Derived reasoning/metrics
    visibility_score = Column(Integer, default=0)
    sentiment_score = Column(Integer, default=0)
    
    brand = relationship("Brand", back_populates="intents")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
