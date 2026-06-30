from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    quantity: int = Field(ge=0)
    location: str = Field(min_length=1)
    reorder_level: int = Field(ge=0)


class ProductUpdate(BaseModel):
    sku: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    quantity: int = Field(ge=0)
    location: str = Field(min_length=1)
    reorder_level: int = Field(ge=0)


class QuantityUpdate(BaseModel):
    quantity: int = Field(ge=0)


class QuantityAdjustment(BaseModel):
    change: int
    reason: str = Field(min_length=1)

class InventoryAction(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

class OrderCreate(BaseModel):
    items: list[OrderItemCreate]