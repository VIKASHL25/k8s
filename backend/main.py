from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
import pymongo
import os
import time

app = FastAPI(title="MongoDB K8s API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    max_retries = 30
    for attempt in range(max_retries):
        try:
            client = pymongo.MongoClient(
                host=os.environ.get("MONGO_HOST", "mongodb"),
                port=27017,
                username=os.environ.get("MONGO_USER", "root"),
                password=os.environ.get("MONGO_PASSWORD", "password"),
                serverSelectionTimeoutMS=3000
            )
            client.server_info()
            db = client[os.environ.get("MONGO_DB", "appdb")]
            return db
        except Exception as e:
            print(f"Attempt {attempt+1}/{max_retries}: MongoDB not ready ({e})")
            time.sleep(5)
    raise HTTPException(status_code=500, detail="MongoDB connection failed")

class Item(BaseModel):
    name: str
    description: str = ""
    price: float = 0.0

class ItemResponse(BaseModel):
    id: str
    name: str
    description: str
    price: float

@app.get("/")
def root():
    return {
        "message": "FastAPI + MongoDB on Kubernetes!",
        "app": os.environ.get("APP_NAME", "Mongo K8s App"),
        "env": os.environ.get("APP_ENV", "development"),
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/items")
def get_items():
    db = get_db()
    items = list(db.items.find())
    return [{"id": str(i["_id"]), "name": i["name"], 
             "description": i["description"], "price": i["price"]} 
            for i in items]

@app.post("/items")
def create_item(item: Item):
    db = get_db()
    result = db.items.insert_one(item.dict())
    return {"id": str(result.inserted_id), **item.dict()}

@app.put("/items/{item_id}")
def update_item(item_id: str, item: Item):
    db = get_db()
    result = db.items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": item.dict()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item_id, **item.dict()}

@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    db = get_db()
    result = db.items.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": f"Item {item_id} deleted"}