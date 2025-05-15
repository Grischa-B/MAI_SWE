import os, json
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import jwt, redis

from sqlalchemy import create_engine, Column, Integer, String
# from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from passlib.context import CryptContext

# Константы для JWT
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=30)) -> str:
    """
    Генерирует JWT с полем 'sub' и сроком жизни expires_delta.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Подключение к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Redis
REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Хэширование
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# SQLAlchemy-модель пользователя
class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)

# Pydantic-модели
class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

# Модель для обновления (Update) пользователя. Все поля опциональные.
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

app = FastAPI(title="UserService with Redis Cache")

# Ждём старта Postgres
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(UserModel).filter_by(username="admin").first():
        admin = UserModel(
            username="admin",
            full_name="Administrator",
            hashed_password=pwd.hash("secret")
        )
        db.add(admin)
        db.commit()
    db.close()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def create_token(sub: str):
    exp = datetime.utcnow() + timedelta(minutes=30)
    return jwt.encode({"sub": sub, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

def auth_user(token: str = Depends(oauth2_scheme)):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data["sub"]
    except:
        raise HTTPException(401, "Invalid token")

# Настройка хэширования паролей (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Новая Pydantic-модель для JSON-запроса
class LoginData(BaseModel):
    username: str
    password: str

# --- CRUD с кешем ---
@app.post("/token", response_model=Token)
def login(login_data: LoginData, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, _: str = Depends(auth_user), db: Session = Depends(get_db)):
    key = f"user:{user_id}"
    if cached := redis_client.get(key):
        return json.loads(cached)
    user = db.query(UserModel).get(user_id)
    if not user: raise HTTPException(status_code=404, detail="Not found")
    out = UserOut.from_orm(user).dict()
    redis_client.set(key, json.dumps(out))
    return out

@app.get("/users", response_model=List[UserOut])
def list_users(_: str = Depends(auth_user), db: Session = Depends(get_db)):
    key = "users:all"
    if cached := redis_client.get(key):
        return json.loads(cached)
    users = [UserOut.from_orm(u).dict() for u in db.query(UserModel).all()]
    redis_client.set(key, json.dumps(users))
    return users

@app.post("/users", response_model=UserOut, status_code=201)
def create_user(
    user_in: UserCreate,
    _: str = Depends(auth_user),
    db: Session = Depends(get_db)
):
    # проверка на существование
    if db.query(UserModel).filter_by(username=user_in.username).first():
        raise HTTPException(status_code=400, detail="User already exists")
    # создаём ORM-экземпляр
    db_user = UserModel(
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=pwd_context.hash(user_in.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Инвалидация/запись в кеш
    redis_client.delete("users:all")
    # Здесь db_user.id точно существует
    redis_client.set(
        f"user:{db_user.id}",
        json.dumps(UserOut.model_validate(db_user).dict())
    )

    # Возвращаем ORM-модель — FastAPI сам применит response_model=UserOut
    return db_user

@app.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, user_update: UserUpdate, _: str = Depends(auth_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).get(user_id)
    if not user: raise HTTPException(404, "Not found")
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.password is not None:
        user.hashed_password = pwd.hash(user_update.password)
    db.commit()
    db.refresh(user)
    out = UserOut.from_orm(user).dict()
    redis_client.delete("users:all")
    redis_client.set(f"user:{user_id}", json.dumps(out))
    return out

@app.delete("/users/{user_id}", response_model=UserOut)
def delete_user(user_id: int, _: str = Depends(auth_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    out = UserOut.from_orm(user).dict()
    db.delete(user)
    db.commit()
    redis_client.delete("users:all")
    redis_client.delete(f"user:{user_id}")
    return out
