from datetime import datetime
from typing import List, Union

from fastapi.openapi.models import Schema
from pydantic import BaseModel, EmailStr, constr
from bson.objectid import ObjectId


class UserBaseSchema(BaseModel):
    name: str
    email: str
    photo: str
    role: Union[str, None] = None
    created_at: Union[datetime, None] = None
    updated_at: Union[datetime, None] = None

    class Config:
        orm_mode = True


class CreateUserSchema(UserBaseSchema):
    password: constr(min_length=8)
    passwordConfirm: str
    verified: bool = False


class LoginUserSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)


class UserResponseSchema(UserBaseSchema):
    id: str
    pass


class UserResponse(BaseModel):
    status: str
    user: UserResponseSchema


class FilteredUserResponse(UserBaseSchema):
    id: str


class PostBaseSchema(BaseModel):
    title: str
    content: str
    category: str
    image: str
    created_at: Union[datetime, None] = None
    updated_at: Union[datetime, None] = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CreatePostSchema(PostBaseSchema):
    user: ObjectId = None
    pass


class PostResponse(PostBaseSchema):
    id: str
    user: FilteredUserResponse
    created_at: datetime
    updated_at: datetime


class UpdatePostSchema(BaseModel):
    title: Union[str, None] = None
    content: Union[str, None] = None
    category: Union[str, None] = None
    image: Union[str, None] = None
    user: Union[str, None] = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ListPostResponse(BaseModel):
    status: str
    results: int
    posts: List[PostResponse]


class Message(BaseModel):
    user: str
    message: str


class Group(BaseModel):
    name: str
    members: List[str] = []


class AddMembersRequest(BaseModel):
    group_id: str
    members: List[str]


# Модель данных для групп
class GroupModel:
    def __init__(self, name, members=[]):
        self.name = name
        self.members = members

    def to_dict(self):
        return {"name": self.name, "members": self.members}
