from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base


class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    name_ar = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    geometry = Column(Geometry('POLYGON', srid=4326), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    buildings = relationship("Building", back_populates="area")
    complaints = relationship("Complaint", back_populates="area")
    tasks = relationship("Task", back_populates="area")


class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    building_number = Column(String(20), nullable=True)
    floors = Column(Integer, nullable=True)
    geometry = Column(Geometry('POINT', srid=4326), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    area = relationship("Area", back_populates="buildings")


class Street(Base):
    __tablename__ = "streets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    geometry = Column(Geometry('LINESTRING', srid=4326), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
