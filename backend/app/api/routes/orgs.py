from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.db.models import Organization
from datetime import datetime
import uuid

router = APIRouter()


class OrgCreate(BaseModel):
    name: str


class OrgResponse(BaseModel):
    id: str
    name: str
    created_at: str

    class Config:
        from_attributes = True


@router.post("/orgs", response_model=OrgResponse)
def create_org(org: OrgCreate, db: Session = Depends(get_db)):
    db_org = Organization(name=org.name)
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    
    created_at = db_org.created_at or datetime.now()
    
    return OrgResponse(
        id=str(db_org.id),
        name=db_org.name,
        created_at=created_at.isoformat()
    )


@router.get("/orgs/{org_id}", response_model=OrgResponse)
def get_org(org_id: str, db: Session = Depends(get_db)):
    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid org_id format")
    
    org = db.query(Organization).filter(Organization.id == org_uuid).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    created_at = org.created_at or datetime.now()
    
    return OrgResponse(
        id=str(org.id),
        name=org.name,
        created_at=created_at.isoformat()
    )
