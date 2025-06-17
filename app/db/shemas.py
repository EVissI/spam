from pydantic import BaseModel

class UserModel(BaseModel):
    id:int
    username:str | None

class UserFilterModel(BaseModel):
    id:int | None = None
    username:str | None = None

class PresetsModel(BaseModel):
    preset_name:str 
    message:str
    target_chats:list[int]
    user_id:int

class PresetsFilterModel(BaseModel):
    id:int | None = None
    preset_name:str | None = None
    message:str | None = None
    target_chats:list[int] | None = None
    user_id:int | None = None

class AccountModel(BaseModel):
    phone:int
    api_id:int
    api_hash:str
    session_path:str
    is_active:bool = True
    proxy:str | None = None
    user_id:int

class AccountFilterModel(BaseModel):
    id:int | None = None
    phone:int | None = None
    api_id:int | None = None
    api_hash:str | None = None
    session_path:str | None = None
    is_active:bool | None = None
    proxy:str | None = None
    user_id:int | None = None