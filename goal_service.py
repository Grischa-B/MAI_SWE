import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from pymongo import MongoClient, ASCENDING
from bson import ObjectId
import jwt

# JWT
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8000/token")

# Pydantic-схемы
class GoalIn(BaseModel):
    title: str
    description: Optional[str] = None

class GoalOut(GoalIn):
    id: str = Field(..., alias="_id")
    created_at: datetime

    class Config:
        allow_population_by_field_name = True

# Инициализация FastAPI и MongoDB
app = FastAPI(title="Goal Service (MongoDB)")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
client = MongoClient(MONGO_URL)
db = client["planner"]
goals = db["goals"]

# Индекс для ускоренного поиска по title
goals.create_index([("title", ASCENDING)], background=True)

# Наполнение тестовыми данными при первом запуске
@app.on_event("startup")
def seed_data():
    if goals.count_documents({}) == 0:
        goals.insert_many([
            {"title": "Научиться FastAPI", "description": "Пройти туториал",    "created_at": datetime.utcnow()},
            {"title": "Сделать MVP",       "description": "Первый релиз",       "created_at": datetime.utcnow()},
        ])

# Утилита: приводим ObjectId к строке
def serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc

# Аутентификация по JWT
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# CRUD-эндпоинты
@app.get("/goals", response_model=List[GoalOut])
def list_goals(_: str = Depends(get_current_user)):
    return [serialize(doc) for doc in goals.find()]

@app.post("/goals", response_model=GoalOut, status_code=201)
def create_goal(goal: GoalIn, _: str = Depends(get_current_user)):
    data = goal.dict()
    data["created_at"] = datetime.utcnow()
    res = goals.insert_one(data)
    return serialize(goals.find_one({"_id": res.inserted_id}))

@app.put("/goals/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: str, goal: GoalIn, _: str = Depends(get_current_user)):
    res = goals.update_one({"_id": ObjectId(goal_id)}, {"$set": goal.dict()})
    if res.matched_count == 0:
        raise HTTPException(404, "Goal not found")
    return serialize(goals.find_one({"_id": ObjectId(goal_id)}))

@app.delete("/goals/{goal_id}", response_model=GoalOut)
def delete_goal(goal_id: str, _: str = Depends(get_current_user)):
    doc = goals.find_one_and_delete({"_id": ObjectId(goal_id)})
    if not doc:
        raise HTTPException(404, "Goal not found")
    return serialize(doc)
