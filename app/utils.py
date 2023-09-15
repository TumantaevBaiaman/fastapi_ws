import jwt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from fastapi import Depends, WebSocket, WebSocketDisconnect, HTTPException
from jwt import PyJWTError, InvalidTokenError
from .config import settings
from .database import User

SECRET_KEY = settings.ACCESS_TOKEN_EXPIRES_IN
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)


def decode_token(token):
    try:
        # Декодирование токена с использованием секретного ключа
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        # В payload могут быть разные данные, включая идентификатор пользователя
        # Возвращайте те данные, которые вам нужны
        return payload.get("user_id")

    except InvalidTokenError:
        # Обработка ошибки, если токен недействителен
        return None
