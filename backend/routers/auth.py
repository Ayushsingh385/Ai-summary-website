from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import bcrypt
import jwt
from datetime import datetime, timedelta

import models, schemas
from database import get_db
from config import settings
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter for auth endpoints
limiter = Limiter(key_func=get_remote_address)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/signin")
router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
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
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


@router.post("/signup", response_model=schemas.UserResponse)
@limiter.limit("5/minute")
def signup(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
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
@limiter.limit("5/minute")
def signin(request: Request, user: schemas.UserLogin, db: Session = Depends(get_db)):
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

def get_current_admin(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have enough privileges"
        )
    return current_user

@router.get("/admin/stats")
@limiter.limit("10/minute")
def get_admin_stats(request: Request, current_admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """System-wide statistics for the admin dashboard."""
    total_users = db.query(models.User).count()
    total_cases = db.query(models.CaseDocument).count()
    total_comparisons = db.query(models.CaseComparison).count()
    
    # Let's get the latest 5 users
    recent_users = db.query(models.User).order_by(models.User.id.desc()).limit(5).all()
    recent_users_list = [{"id": u.id, "user_id": u.user_id, "is_admin": u.is_admin} for u in recent_users]
    
    return {
        "total_users": total_users,
        "total_cases_ingested": total_cases,
        "total_comparisons": total_comparisons,
        "recent_users": recent_users_list
    }

