import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

from database import create_document, get_documents, db

app = FastAPI(title="Supermarket API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Root & Health ============
@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or ("✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set")
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Confirm env again
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ============ Schemas for API ============
class ProductIn(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")


class UserIn(BaseModel):
    name: str
    email: EmailStr
    address: str
    age: Optional[int] = Field(None, ge=0, le=120)
    is_active: bool = True


class CartItem(BaseModel):
    id: str
    name: str
    price: float
    qty: int = Field(..., ge=0)


class CartSummary(BaseModel):
    subtotal: float
    tax: float
    shipping: float
    total: float


# ============ Products Endpoints ============
@app.post("/api/products")
def create_product(payload: ProductIn):
    try:
        inserted_id = create_document("product", payload)
        return {"id": inserted_id, "message": "Product created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products")
def list_products(limit: Optional[int] = 50):
    try:
        docs = get_documents("product", limit=limit)
        # Convert ObjectId and timestamps to serializable
        for d in docs:
            d["id"] = str(d.pop("_id", ""))
            if "created_at" in d:
                d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else d["created_at"]
            if "updated_at" in d:
                d["updated_at"] = d["updated_at"].isoformat() if hasattr(d["updated_at"], "isoformat") else d["updated_at"]
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Users Endpoints ============
@app.post("/api/users")
def create_user(payload: UserIn):
    try:
        inserted_id = create_document("user", payload)
        return {"id": inserted_id, "message": "User created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users")
def list_users(limit: Optional[int] = 50):
    try:
        docs = get_documents("user", limit=limit)
        for d in docs:
            d["id"] = str(d.pop("_id", ""))
            if "created_at" in d:
                d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else d["created_at"]
            if "updated_at" in d:
                d["updated_at"] = d["updated_at"].isoformat() if hasattr(d["updated_at"], "isoformat") else d["updated_at"]
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Cart Utilities (Stateless) ============
@app.post("/api/cart/summary", response_model=CartSummary)
def compute_cart_summary(items: List[CartItem]):
    subtotal = sum(i.price * i.qty for i in items)
    shipping = 0.0 if subtotal == 0 or subtotal > 25 else 4.99
    tax = round(subtotal * 0.07, 2)
    total = round(subtotal + tax + shipping, 2)
    return CartSummary(
        subtotal=round(subtotal, 2),
        tax=tax,
        shipping=round(shipping, 2),
        total=total,
    )


# ============ Optional: Expose defined schemas ============
@app.get("/schema")
def get_defined_schemas():
    try:
        from schemas import User, Product  # type: ignore
        return {
            "schemas": {
                "user": User.model_json_schema(),
                "product": Product.model_json_schema(),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
