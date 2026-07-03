from fastapi import FastAPI
from routes.products import router as products_router
from routes.orders import router as orders_router
from routes.inventory import router as inventory_router

app = FastAPI()

app.include_router(products_router)
app.include_router(orders_router)
app.include_router(inventory_router)


@app.get("/")
def home():
    return {"message": "Warehouseops API is running!"}



 