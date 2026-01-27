"""
Menu input API routes.

Allows restaurant owners to provide their menu via:
- CSV upload
- Manual entry
"""

import csv
import io
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Cycle, OwnerMenuItem

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class MenuItemInput(BaseModel):
    """Single menu item for manual entry."""
    item_name: str = Field(..., min_length=1, max_length=200)
    price: str = Field(..., min_length=1, max_length=20)  # e.g., "$12.99", "12.99"
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class MenuItemResponse(BaseModel):
    """Response for a menu item."""
    id: str
    item_name: str
    price: str
    category: Optional[str]
    description: Optional[str]


class BulkMenuInput(BaseModel):
    """Multiple menu items for bulk manual entry."""
    items: list[MenuItemInput]


class MenuUploadResponse(BaseModel):
    """Response from menu upload/entry."""
    cycle_id: str
    items_added: int
    items_total: int
    message: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/cycles/{cycle_id}/menu/upload", response_model=MenuUploadResponse)
async def upload_menu_csv(
    cycle_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload menu items via CSV file.

    Expected CSV format:
    - Required columns: item_name, price
    - Optional columns: category, description

    Example:
    ```
    item_name,price,category,description
    Pad Thai,$14.99,Mains,Classic Thai noodles
    Spring Rolls,$6.99,Appetizers,Crispy vegetable rolls
    ```
    """
    # Validate cycle_id
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")

    # Check cycle exists
    cycle = db.query(Cycle).filter(Cycle.id == cycle_uuid).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV. Please upload a .csv file."
        )

    # Read and parse CSV
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))

        # Validate required columns
        fieldnames = reader.fieldnames or []
        fieldnames_lower = [f.lower().strip() for f in fieldnames]

        if 'item_name' not in fieldnames_lower and 'name' not in fieldnames_lower:
            raise HTTPException(
                status_code=400,
                detail="CSV must have 'item_name' or 'name' column"
            )
        if 'price' not in fieldnames_lower:
            raise HTTPException(
                status_code=400,
                detail="CSV must have 'price' column"
            )

        # Map column names (handle variations)
        def get_value(row: dict, *keys: str) -> Optional[str]:
            for key in keys:
                for k, v in row.items():
                    if k.lower().strip() == key.lower():
                        return v.strip() if v else None
            return None

        # Clear existing menu items for this cycle
        db.query(OwnerMenuItem).filter(OwnerMenuItem.cycle_id == cycle_uuid).delete()

        # Parse and insert items
        items_added = 0
        for row in reader:
            item_name = get_value(row, 'item_name', 'name', 'item')
            price = get_value(row, 'price')

            if not item_name or not price:
                continue  # Skip rows with missing required fields

            menu_item = OwnerMenuItem(
                cycle_id=cycle_uuid,
                item_name=item_name,
                price=price,
                category=get_value(row, 'category', 'cat', 'type'),
                description=get_value(row, 'description', 'desc'),
            )
            db.add(menu_item)
            items_added += 1

        db.commit()

        # Get total count
        total = db.query(OwnerMenuItem).filter(
            OwnerMenuItem.cycle_id == cycle_uuid
        ).count()

        return MenuUploadResponse(
            cycle_id=cycle_id,
            items_added=items_added,
            items_total=total,
            message=f"Successfully uploaded {items_added} menu items",
        )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Could not decode CSV file. Please ensure it's UTF-8 encoded."
        )
    except Exception as e:
        logger.exception(f"CSV upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")


@router.post("/cycles/{cycle_id}/menu/items", response_model=MenuUploadResponse)
def add_menu_items(
    cycle_id: str,
    items: BulkMenuInput,
    db: Session = Depends(get_db),
):
    """
    Add menu items via manual entry (bulk).

    Send a list of items to add to the menu.
    """
    # Validate cycle_id
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")

    # Check cycle exists
    cycle = db.query(Cycle).filter(Cycle.id == cycle_uuid).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    # Add items
    items_added = 0
    for item in items.items:
        menu_item = OwnerMenuItem(
            cycle_id=cycle_uuid,
            item_name=item.item_name,
            price=item.price,
            category=item.category,
            description=item.description,
        )
        db.add(menu_item)
        items_added += 1

    db.commit()

    # Get total count
    total = db.query(OwnerMenuItem).filter(
        OwnerMenuItem.cycle_id == cycle_uuid
    ).count()

    return MenuUploadResponse(
        cycle_id=cycle_id,
        items_added=items_added,
        items_total=total,
        message=f"Successfully added {items_added} menu items",
    )


@router.get("/cycles/{cycle_id}/menu", response_model=list[MenuItemResponse])
def get_menu_items(
    cycle_id: str,
    db: Session = Depends(get_db),
):
    """
    Get all menu items for a cycle.
    """
    # Validate cycle_id
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")

    # Get items
    items = db.query(OwnerMenuItem).filter(
        OwnerMenuItem.cycle_id == cycle_uuid
    ).all()

    return [
        MenuItemResponse(
            id=str(item.id),
            item_name=item.item_name,
            price=item.price,
            category=item.category,
            description=item.description,
        )
        for item in items
    ]


@router.delete("/cycles/{cycle_id}/menu")
def clear_menu_items(
    cycle_id: str,
    db: Session = Depends(get_db),
):
    """
    Clear all menu items for a cycle.
    """
    # Validate cycle_id
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")

    # Delete items
    deleted = db.query(OwnerMenuItem).filter(
        OwnerMenuItem.cycle_id == cycle_uuid
    ).delete()

    db.commit()

    return {
        "cycle_id": cycle_id,
        "items_deleted": deleted,
        "message": f"Deleted {deleted} menu items",
    }


@router.delete("/cycles/{cycle_id}/menu/{item_id}")
def delete_menu_item(
    cycle_id: str,
    item_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a single menu item.
    """
    # Validate IDs
    try:
        cycle_uuid = uuid.UUID(cycle_id)
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Delete item
    deleted = db.query(OwnerMenuItem).filter(
        OwnerMenuItem.id == item_uuid,
        OwnerMenuItem.cycle_id == cycle_uuid,
    ).delete()

    if not deleted:
        raise HTTPException(status_code=404, detail="Menu item not found")

    db.commit()

    return {"message": "Menu item deleted"}
