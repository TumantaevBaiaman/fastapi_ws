import uuid

from typing import Annotated, List
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

# ---------------------------------   CHAT WEBSOCKET  -----------------------------------------


class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, group_id: str):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)

    def disconnect(self, websocket: WebSocket, group_id: str):
        if group_id in self.active_connections:
            self.active_connections[group_id].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, websocket: WebSocket, message: str, add_to_db: bool, group_id: str, client_id: str):
        if add_to_db:
            await self.add_messages_to_database(message, group_id, client_id)
        if group_id in self.active_connections:
            for connection in self.active_connections[group_id]:
                await connection.send_text(message)

    @staticmethod
    async def add_messages_to_database(message: str, group_id: str, client_id: str):
        inserted_message = Chat.message.insert_one({
            "user_id": client_id,
            "group_id": group_id,
            "message": message
        })

        if not inserted_message.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to create the group")


manager = ConnectionManager()


@router.get("/last_message/{group_id}")
def get_last_message(request: Request, group_id: str):
    messages: list = [
        {
            "group_id": i["group_id"],
            "message": i["message"],
            "user_id": i["user_id"]
        }
        for i in Chat.message.find() if i["group_id"] == group_id]
    return messages


@router.get("/{group_id}")
def get_chat_page(request: Request, group_id: str):
    group = Chat.groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No Group'
        )
    return templates.TemplateResponse("chat.html", {"request": request, "group_id": group_id})


@router.websocket("/ws/{id_client}/{group_id}")
async def websocket_endpoint(websocket: WebSocket, id_client: str, group_id: str):
    await manager.connect(websocket, group_id=group_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(websocket, f"{data}", add_to_db=True, group_id=group_id, client_id=id_client)
    except WebSocketDisconnect:
        manager.disconnect(websocket, group_id=group_id)
        await manager.broadcast(websocket, f"{id_client} left the chat", add_to_db=False, group_id=group_id, client_id=id_client)


