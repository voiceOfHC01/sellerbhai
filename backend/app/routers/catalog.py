from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.schema import Product, ProductVariant
from app.routers.auth import get_current_admin

router = APIRouter(prefix="/catalog", tags=["Catalog"])

# Pydantic Schemas
class VariantCreate(BaseModel):
    sku: str
    title: str
    price: float
    stock: int = 0
    color: Optional[str] = None
    size: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True

class VariantUpdate(BaseModel):
    sku: Optional[str] = None
    title: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    color: Optional[str] = None
    size: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    sku: str
    title: str
    price: float
    stock: int
    color: Optional[str]
    size: Optional[str]
    image_url: Optional[str]
    is_active: bool

class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    base_price: float
    image_url: Optional[str] = None
    is_active: bool = True
    variants: Optional[List[VariantCreate]] = []

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    base_price: Optional[float] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    base_price: float
    image_url: Optional[str]
    is_active: bool
    variants: List[VariantResponse] = []

@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(Product).options(selectinload(Product.variants)).order_by(Product.id.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    product = Product(
        title=data.title,
        description=data.description,
        category=data.category,
        base_price=data.base_price,
        image_url=data.image_url,
        is_active=data.is_active
    )
    db.add(product)
    await db.flush()

    # Add variants if supplied
    if data.variants:
        for v in data.variants:
            variant = ProductVariant(
                product_id=product.id,
                sku=v.sku,
                title=v.title,
                price=v.price,
                stock=v.stock,
                color=v.color,
                size=v.size,
                image_url=v.image_url or product.image_url,
                is_active=v.is_active
            )
            db.add(variant)
    else:
        # Create default variant matching base price
        default_variant = ProductVariant(
            product_id=product.id,
            sku=f"SKU-{product.id}-DEF",
            title=f"{product.title} - Standard",
            price=product.base_price,
            stock=10,
            image_url=product.image_url,
            is_active=True
        )
        db.add(default_variant)

    await db.commit()

    # Reload with variants
    res = await db.execute(select(Product).options(selectinload(Product.variants)).where(Product.id == product.id))
    return res.scalars().first()

@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(Product).options(selectinload(Product.variants)).where(Product.id == product_id))
    product = res.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(product, field, val)

    await db.commit()
    await db.refresh(product)
    return product

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(Product).where(Product.id == product_id))
    product = res.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
    return {"status": "success", "message": f"Product #{product_id} deleted"}

@router.post("/products/{product_id}/variants", response_model=VariantResponse)
async def add_variant(
    product_id: int,
    data: VariantCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(Product).where(Product.id == product_id))
    product = res.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    variant = ProductVariant(
        product_id=product_id,
        sku=data.sku,
        title=data.title,
        price=data.price,
        stock=data.stock,
        color=data.color,
        size=data.size,
        image_url=data.image_url or product.image_url,
        is_active=data.is_active
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return variant

@router.put("/variants/{variant_id}", response_model=VariantResponse)
async def update_variant(
    variant_id: int,
    data: VariantUpdate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
    variant = res.scalars().first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(variant, field, val)

    await db.commit()
    await db.refresh(variant)
    return variant

@router.delete("/variants/{variant_id}")
async def delete_variant(
    variant_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
    variant = res.scalars().first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    await db.delete(variant)
    await db.commit()
    return {"status": "success", "message": f"Variant #{variant_id} deleted"}
