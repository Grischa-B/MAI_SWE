from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta

app = FastAPI()

class LoginData(BaseModel):
    username: str
    password: str

# Ключ и алгоритм для JWT
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"

app = FastAPI(title="Сервис пользователей")

# Мастер-пользователь: admin / secret
users_db = {
    "admin": {
        "username": "admin",
        "password": "secret",
        "full_name": "Администратор"
    }
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class User(BaseModel):
    username: str
    full_name: str = None

class UserInDB(User):
    password: str

def authenticate_user(username: str, password: str):
    user = users_db.get(username)
    if not user or user["password"] != password:
        return None
    return UserInDB(**user)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=30)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    user = users_db.get(username)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return UserInDB(**user)

@app.post("/token")
def login(login_data: LoginData):
    if login_data.username != "admin" or login_data.password != "secret":
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": login_data.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users", response_model=list[User])
def get_users(current_user: User = Depends(get_current_user)):
    return [User(username=u["username"], full_name=u.get("full_name")) for u in users_db.values()]

@app.post("/users", response_model=User)
def create_user(user: UserInDB, current_user: User = Depends(get_current_user)):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    users_db[user.username] = user.dict()
    return User(username=user.username, full_name=user.full_name)
