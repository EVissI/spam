from app.db.base import BaseDAO
from app.db.models import User, Presets,Accounts


class UserDAO(BaseDAO[User]):
    model = User

class PresetDAO(BaseDAO[Presets]):
    model = Presets

class AccountDAO(BaseDAO[Accounts]):
    model = Accounts

    @classmethod
    async def get_by_user_id(cls, session, user_id: int):
        stmt = cls.model.__table__.select().where(cls.model.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def set_preset(cls, session, account_id: int, preset_id: int):
        account = await cls.find_one_or_none_by_id(data_id=account_id, session=session)
        if account:
            account.preset_id = preset_id
            await session.commit()
            await session.refresh(account)
        return account