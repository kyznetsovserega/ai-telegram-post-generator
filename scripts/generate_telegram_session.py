from __future__ import annotations

import asyncio

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

from app.config import TELEGRAM_API_HASH, TELEGRAM_API_ID, TELEGRAM_SESSION_STRING


async def main() -> None:
    if not TELEGRAM_API_ID:
        raise RuntimeError("TELEGRAM_API_ID is not configured")

    if not TELEGRAM_API_HASH:
        raise RuntimeError("TELEGRAM_API_HASH is not configured")

    # Берём текущее значение TELEGRAM_SESSION_STRING из конфига.
    # Если в .env строка пустая, будет создана новая сессия.
    # Если строка уже есть, Telethon попытается использовать её повторно.
    client = TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING),
        int(TELEGRAM_API_ID),
        TELEGRAM_API_HASH,
    )

    await client.connect()

    if not await client.is_user_authorized():
        phone = input("Введите телефон: ").strip()
        await client.send_code_request(phone)

        code = input("Введите код: ").strip()

        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            password = input("Введите 2FA password: ").strip()
            await client.sign_in(password=password)

    print("\n===== Сохраните эту строку в TELEGRAM_SESSION_STRING =====")
    print(client.session.save())
    print("==========================================================\n")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
