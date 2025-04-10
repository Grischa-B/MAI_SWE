from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import jwt

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"

app = FastAPI(title="Сервис целей")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Хранение целей в памяти
goals_db = {}

class Goal(BaseModel):
    id: int = None
    title: str
    description: str = None

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    return username

@app.get("/goals", response_model=list[Goal])
def get_goals(current_user: str = Depends(get_current_user)):
    return list(goals_db.values())

@app.post("/goals", response_model=Goal)
def create_goal(goal: Goal, current_user: str = Depends(get_current_user)):
    goal.id = len(goals_db) + 1
    goals_db[goal.id] = goal
    return goal
