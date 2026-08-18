from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from core.config import get_settings
import bcrypt as _bcrypt

settings = get_settings()


def _pwd_context():
    try:
        from passlib.context import CryptContext
        return CryptContext(schemes=["bcrypt"], deprecated="auto")
    except Exception:
        return None

_ctx = _pwd_context()


def hash_password(password: str) -> str:
    if _ctx:
        try:
            return _ctx.hash(password)
        except Exception:
            pass
    salt = _bcrypt.gensalt()
    return _bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if _ctx:
        try:
            return _ctx.verify(plain, hashed)
        except Exception:
            pass
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")
