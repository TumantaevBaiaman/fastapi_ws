import uuid

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.schemas import Group, Message

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

active_groups = {}


@router.get("/{group_id}")
def get_chat_page(request: Request, group_id):
    return templates.TemplateResponse("chat.html", {"request": request, "group_id": group_id})


@router.post("/create_group/", response_model=Group)
async def create_group(group: Group):
    group_id = str(uuid.uuid4())
    active_groups[group_id] = group
    return group


@router.websocket("/ws/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: str):
    await websocket.accept()

    # Создаем группу, если ее нет
    if group_id not in active_groups:
        active_groups[group_id] = {"members": []}

    # Добавляем текущего участника в список участников группы
    active_groups[group_id]["members"].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = Message(user=websocket.client.host, message=data)

            # Отправляем сообщение всем участникам группы
            for connection in active_groups[group_id]["members"]:
                await connection.send_text(message.json())

    except WebSocketDisconnect:
        # Удаление участника из списка участников группы при отключении
        active_groups[group_id]["members"].remove(websocket)

        # Если в группе больше нет участников, удаляем группу
        if not active_groups[group_id]["members"]:
            del active_groups[group_id]

