import asyncio
import json


def parse_proxy(text: str):
    if text.strip() == "-":
        return None
    try:
        if "://" in text:
            scheme, rest = text.split("://", 1)
        else:
            scheme, rest = "socks5", text
        if "@" in rest:
            creds, host_port = rest.split("@", 1)
            if ":" in creds:
                username, password = creds.split(":", 1)
            else:
                username, password = creds, ""
        else:
            host_port = rest
            username = password = None
        if ":" in host_port:
            host, port = host_port.split(":")
        else:
            host, port = host_port, 1080
        return {
            "scheme": scheme,
            "hostname": host,
            "port": int(port),
            "username": username,
            "password": password,
        }
    except Exception:
        return None


async def delayed_disconnect(client, delay: int = 10):
    await asyncio.sleep(delay)
    await client.disconnect()

async def save_account_to_db(**kwargs):
    from app.db.dao import AccountDAO
    from app.db.shemas import AccountModel
    from app.db.database import async_session_maker
    
    async with async_session_maker() as session:
        account_model = AccountModel(
            phone=int(kwargs["phone"].replace("+", "")),
            api_id=kwargs["api_id"],
            api_hash=kwargs["api_hash"],
            user_id=kwargs["user_id"],
            session_path=kwargs["session_path"],
            proxy=json.dumps(kwargs.get("proxy")) if kwargs.get("proxy") else None,
        )
        await AccountDAO.add(session, account_model)
