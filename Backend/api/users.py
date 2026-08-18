from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from models.database import get_db, User
from api.deps import get_current_user, require_role
from core.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

VALID_ROLES = ("admin", "recruiter", "viewer")


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "recruiter"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


def _user_out(u: User) -> dict:
    return {
        "id": u.id, "name": u.name, "email": u.email,
        "role": u.role, "is_active": u.is_active, "org_id": u.org_id,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("/")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ("admin", "owner"):
        users = db.query(User).filter(User.org_id == current_user.org_id).all()
    else:
        users = [current_user]
    return [_user_out(u) for u in users]


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        **_user_out(current_user),
        "org_name": current_user.organization.name if current_user.organization else None,
    }


@router.post("/", status_code=201)
def create_user(
    req: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    if req.role not in VALID_ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {VALID_ROLES}")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already exists")
    user = User(
        org_id=current_user.org_id,
        name=req.name, email=req.email,
        hashed_password=hash_password(req.password),
        role=req.role, is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    req: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    user = db.query(User).filter(
        User.id == user_id, User.org_id == current_user.org_id
    ).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "owner" and current_user.role != "owner":
        raise HTTPException(403, "Cannot modify owner")

    if req.name is not None:
        user.name = req.name
    if req.email is not None:
        existing = db.query(User).filter(User.email == req.email, User.id != user_id).first()
        if existing:
            raise HTTPException(400, "Email already in use")
        user.email = req.email
    if req.role is not None:
        if req.role not in VALID_ROLES:
            raise HTTPException(400, f"Invalid role")
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.password is not None:
        user.hashed_password = hash_password(req.password)

    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    user = db.query(User).filter(
        User.id == user_id, User.org_id == current_user.org_id
    ).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "owner":
        raise HTTPException(403, "Cannot delete owner")
    if user.id == current_user.id:
        raise HTTPException(403, "Cannot delete yourself")
    db.delete(user)
    db.commit()
