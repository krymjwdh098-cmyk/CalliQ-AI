import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.security import hash_password, verify_password, create_access_token
from models.database import get_db, User, Organization
from utils.rate_limiter import login_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    org_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    org_id: int
    org_name: Optional[str] = None


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _rl: None = Depends(login_limiter),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    slug = req.org_name.lower().replace(" ", "-")[:40] + "-" + secrets.token_hex(3)
    org = Organization(name=req.org_name, slug=slug)
    db.add(org)
    db.flush()
    user = User(
        org_id=org.id,
        email=req.email,
        name=req.name,
        hashed_password=hash_password(req.password),
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        org_id=current_user.org_id,
        org_name=current_user.organization.name if current_user.organization else None,
    )
