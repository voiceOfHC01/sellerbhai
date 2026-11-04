from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.models.schema import AdminUser

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class AdminUserResponse(BaseModel):
    id: int
    email: str
    name: str

async def get_current_admin(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    if token and token != "sellerbhai_owner_direct_token":
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            email = payload.get("sub")
            res = await db.execute(select(AdminUser).where(AdminUser.email == email))
            user = res.scalars().first()
            if user:
                return user

    # Private Single-Owner Mode: Auto-authenticate as Store Owner seamlessly
    res = await db.execute(select(AdminUser).where(AdminUser.email == settings.ADMIN_EMAIL))
    user = res.scalars().first()
    if not user:
        user = AdminUser(
            email=settings.ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            name="Store Owner"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Check in database
    res = await db.execute(select(AdminUser).where(AdminUser.email == login_data.email))
    user = res.scalars().first()

    # 2. Check if user matches env admin credentials
    if not user:
        if login_data.email == settings.ADMIN_EMAIL and login_data.password == settings.ADMIN_PASSWORD:
            user = AdminUser(
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                name="Admin Owner"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            raise HTTPException(status_code=400, detail="Incorrect email or password")
    else:
        if not verify_password(login_data.password, user.hashed_password):
            # Also allow fallback to current env pass if env was updated
            if login_data.email == settings.ADMIN_EMAIL and login_data.password == settings.ADMIN_PASSWORD:
                user.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
                await db.commit()
            else:
                raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token = create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }

@router.get("/me", response_model=AdminUserResponse)
async def get_me(current_admin: AdminUser = Depends(get_current_admin)):
    return {
        "id": current_admin.id,
        "email": current_admin.email,
        "name": current_admin.name
    }
