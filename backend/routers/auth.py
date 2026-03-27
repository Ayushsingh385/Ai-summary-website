from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import bcrypt
import jwt
from datetime import datetime, timedelta

import models, schemas
from database import get_db

SECRET_KEY = "supersecretkey"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/signin")
router = APIRouter(prefix="/auth", tags=["auth"])

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

def verify_password(plain_password, hashed_password):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_password_hash(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/signup", response_model=schemas.UserResponse)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.user_id == user.user_id) | (models.User.email_id == user.email_id)
    ).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="User with this User ID or Email already exists"
        )
    hashed_pwd = get_password_hash(user.password)
    new_user = models.User(
        user_id=user.user_id,
        employee_id=user.employee_id,
        email_id=user.email_id,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/signin", response_model=schemas.Token)
def signin(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.user_id == user.user_id).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect User ID or Password"
        )
    access_token = create_access_token(data={"sub": db_user.user_id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user
