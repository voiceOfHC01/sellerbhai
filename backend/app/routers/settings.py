from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schema import Setting
from app.routers.auth import get_current_admin
from app.core.config import settings as app_settings

router = APIRouter(prefix="/settings", tags=["Settings"])

class SettingItem(BaseModel):
    key: str
    value: str
    description: str = ""

class SettingsUpdatePayload(BaseModel):
    settings: Dict[str, str]

@router.get("")
async def get_all_settings(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(Setting))
    db_settings = {s.key: s.value for s in res.scalars().all()}

    # Merge with defaults
    defaults = {
        "store_name": app_settings.STORE_NAME,
        "brand_tone": app_settings.STORE_TONE,
        "delivery_inside_dhaka": str(app_settings.DEFAULT_DELIVERY_INSIDE_DHAKA),
        "delivery_outside_dhaka": str(app_settings.DEFAULT_DELIVERY_OUTSIDE_DHAKA),
        "llm_provider": app_settings.LLM_PROVIDER,
        "embedding_provider": app_settings.EMBEDDING_PROVIDER,
    }
    defaults.update(db_settings)
    return defaults

@router.put("")
async def update_settings(
    payload: SettingsUpdatePayload,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    for key, val in payload.settings.items():
        res = await db.execute(select(Setting).where(Setting.key == key))
        s = res.scalars().first()
        if s:
            s.value = str(val)
        else:
            s = Setting(key=key, value=str(val))
            db.add(s)

    await db.commit()
    return {"status": "success", "message": "Settings updated successfully"}
