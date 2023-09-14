import uuid

from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from starlette import status
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.database import Chat
from app.schemas import Group, Message
from app.serializers.chatSerializers import GroupSerializer

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

active_groups = {}


@router.get("/{group_id}")
def get_chat_page(request: Request, group_id):
    return templates.TemplateResponse("chat.html", {"request": request, "group_id": group_id})


@router.post("/create_group/", response_model=Group)
async def create_group(group: Group):
    group_id = str(uuid.uuid4())
    group.id = group_id

    # Подключаемся к MongoDB и вставляем новую группу
    db = Chat
    inserted_group = db.groups.insert_one(group.dict())

    # Проверяем, что группа была успешно вставлена
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

