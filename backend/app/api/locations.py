from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.location import Area, Building, Street
from app.models.user import User
from app.schemas.location import (
    AreaCreate,
    AreaUpdate,
    AreaResponse,
    BuildingCreate,
    BuildingResponse,
    StreetCreate,
    StreetResponse,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/locations", tags=["locations"])


@router.post("/areas", response_model=AreaResponse)
def create_area(
    area: AreaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_area = Area(**area.model_dump())
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    return db_area


@router.get("/areas", response_model=List[AreaResponse])
def list_areas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    areas = db.query(Area).offset(skip).limit(limit).all()
    return areas


@router.get("/areas/{area_id}", response_model=AreaResponse)
def get_area(area_id: int, db: Session = Depends(get_db)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return area


@router.put("/areas/{area_id}", response_model=AreaResponse)
def update_area(
    area_id: int,
    area_update: AreaUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    
    update_data = area_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(area, field, value)
    
    db.commit()
    db.refresh(area)
    return area


@router.post("/buildings", response_model=BuildingResponse)
def create_building(
    building: BuildingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_building = Building(**building.model_dump())
    db.add(db_building)
    db.commit()
    db.refresh(db_building)
    return db_building


@router.get("/buildings", response_model=List[BuildingResponse])
def list_buildings(
    skip: int = 0,
    limit: int = 100,
    area_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(Building)
    if area_id:
        query = query.filter(Building.area_id == area_id)
    buildings = query.offset(skip).limit(limit).all()
    return buildings


@router.post("/streets", response_model=StreetResponse)
def create_street(
    street: StreetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_street = Street(**street.model_dump())
    db.add(db_street)
    db.commit()
    db.refresh(db_street)
    return db_street


@router.get("/streets", response_model=List[StreetResponse])
def list_streets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    streets = db.query(Street).offset(skip).limit(limit).all()
    return streets
