import asyncio
from app.core.database import db_manager

async def check():
    await db_manager.connect()
    user = await db_manager.mongo_db["users"].find_one({"_id": "test_user_002"})
    print("User DNA:", user.get("financial_dna"))
    print("Phone Number:", user.get("phone_number"))

asyncio.run(check())
