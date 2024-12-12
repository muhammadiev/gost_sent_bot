import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import requests

# Bot configuration
TELEGRAM_BOT_TOKEN = "7063427428:AAHIiKGXCuMjwgEhz5LeRYQtUXFN7bU4Lws"
FASTAPI_SERVER_URL = "http://127.0.0.1:8000"  # Replace with your FastAPI server URL

# Initialize bot, dispatcher, and router
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Start command handler
@router.message(Command("start"))
async def start_command(message: types.Message):
    telegram_id = message.from_user.id

    # Create "Start Quiz" button linking to FastAPI site
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Start Quiz",
                    url=f"{FASTAPI_SERVER_URL}/?telegram_id={telegram_id}",
                )
            ]
        ]
    )

    # Send a welcome message with the button
    await message.answer(
        "Qiuz gost ga xush kelibsiz!!! Quizni boshlash uchun pastdagi tugmani bosing",
        reply_markup=keyboard,
    )

# Help command handler
@router.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "This bot allows you to take a quiz.\n\nCommands:\n/start - Start the quiz\n/help - Get help"
    )

# Function to send the score to the user
async def send_score(telegram_id: str, score: int, total: int):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    message = f"Your quiz is complete! 🎉\nYou scored: {score} / 30."

    payload = {
        "chat_id": telegram_id,
        "text": message,
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info(f"Score sent to Telegram user {telegram_id}.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send score to Telegram user {telegram_id}: {e}")

# Main entry point to start the bot
async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
