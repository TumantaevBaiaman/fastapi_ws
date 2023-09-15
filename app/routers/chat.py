import uuid

from typing import Annotated
import jwt
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.templating import Jinja2Templates
from starlette import status
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.config import settings
from app.database import Chat, User
from app.schemas import Group, Message
from app.serializers.chatSerializers import GroupSerializer
from app.utils import decode_token, oauth2_scheme

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


@router.get("/{group_id}")
def get_chat_page(request: Request, group_id):
    return templates.TemplateResponse("chat.html", {"request": request, "group_id": group_id})


@router.post("/create_group/", response_model=Group)
async def create_group(group: Group):
    group_id = str(uuid.uuid4())
    group.id = group_id

    db = Chat
    inserted_group = db.groups.insert_one(group.dict())

    if not inserted_group.acknowledged:
        raise HTTPException(status_code=500, detail="Failed to create the group")

    return group


@router.get("/info_group/{id}")
async def create_group(id: str):
    group = Chat.groups.find_one({"id": id})
    if not group:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='No Group')
    else:
        return GroupSerializer(group)


async def authenticate_user_from_token(websocket: WebSocket):
    try:
        token = websocket.headers.get("Authorization")

        if not token:
            raise WebSocketDisconnect
        user_id = decode_token(token)
        print(user_id)

        if not user_id:
            raise WebSocketDisconnect

        # Получите пользователя из базы данных или другого хранилища
        user = User.find_one(user_id)

        if not user:
            raise WebSocketDisconnect

        # Сохраните пользователя в состоянии WebSocket-соединения
        websocket.state.user = user

    except WebSocketDisconnect:
        await websocket.close()
        return websocket

    return websocket


# Зависимость для аутентификации пользователя по токену
async def get_user_from_token(websocket: WebSocket = Depends(authenticate_user_from_token)):
    return websocket.state.user


def get_user_from_access_token(access_token: str):
    SECRET_KEY = settings.JWT_PUBLIC_KEY
    try:
        decoded_token = jwt.decode(access_token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token.get("sub")
        return user_id

    except jwt.ExpiredSignatureError:
        return None

    except jwt.InvalidTokenError:
        return None


@router.websocket("/ws/{access_token}")
async def websocket_endpoint(websocket: WebSocket, access_token: str):
    active_groups = {i["id"]: i for i in Chat.groups.find()}
    await websocket.accept()
    group_id = 1
    user = get_user_from_access_token(access_token)
    if group_id not in active_groups:
        active_groups[group_id] = {"members": []}

    active_groups[group_id]["members"].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = Message(user=websocket.client.host, message=data)

            for connection in active_groups[group_id]["members"]:
                await connection.send_text(message.json())

    except WebSocketDisconnect:
        active_groups[group_id]["members"].remove(websocket)

        if not active_groups[group_id]["members"]:
            del active_groups[group_id]


