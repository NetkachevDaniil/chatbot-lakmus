import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from config import Settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id):
    expire = datetime.now() + timedelta(minutes=Settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        'sub': user_id,
        "exp": expire,
        "type": "access"
    }

    return jwt.encode(payload, Settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id):
    expire = datetime.now() + timedelta(days=Settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        'sub': user_id,
        "exp": expire,
        "type": "refresh"
    }

    return jwt.encode(payload, Settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str):
    return jwt.decode(token, Settings.SECRET_KEY, algorithms="HS256")
