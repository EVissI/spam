from aiogram import Router


from app.aiogram.routers.add_preset_router import add_preset_router
from app.aiogram.routers.add_acount_router import add_account_router
from app.aiogram.routers.start_router import start_router
from app.aiogram.routers.my_accounts import my_accounts_router
from app.aiogram.routers.add_account_tdata import add_tdata_router

init_router = Router()
init_router.include_routers(start_router,my_accounts_router, 
                            add_account_router, add_preset_router,add_tdata_router)