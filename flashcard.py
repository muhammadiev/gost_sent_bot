import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram import Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import BaseMiddleware
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from docx import Document

API_TOKEN = "6320765562:AAHTfyPpJ3262UidBv2aG9HY18w-DU1yuhc"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def load_flashcards_from_docx(docx_path: str):
    flashcards = []
    try:
        document = Document(docx_path)
        for table in document.tables:
            for row in table.rows[1:]:
                cells = row.cells
                if len(cells) < 3:
                    continue
                question = cells[1].text.strip()
                answer = cells[2].text.strip()
                if question and answer:
                    flashcards.append({"question": question, "answer": answer})
        logging.info(f"Loaded {len(flashcards)} flashcards.")
    except Exception as e:
        logging.error(f"Error loading flashcards: {e}")
    return flashcards

flashcards = load_flashcards_from_docx("questionsofflash.docx")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("👋 Welcome to Flashcard Bot!\nSend /flashcard to get a flashcard.")


import uuid

# Global dict to hold answers temporarily
answer_cache = {}


@dp.message(Command("flashcard"))
async def cmd_flashcard(message: Message):
    if not flashcards:
        await message.answer("No flashcards available.")
        return

    card = random.choice(flashcards)

    # Generate a unique ID for this flashcard answer
    card_id = str(uuid.uuid4())
    answer_cache[card_id] = card["answer"]

    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Show Answer", callback_data=card_id)
    keyboard = kb.as_markup()

    await message.answer(f"🧠 Question:\n\n{card['question']}", reply_markup=keyboard)


@dp.callback_query(F.data)
async def show_answer(callback: CallbackQuery):
    card_id = callback.data
    answer = answer_cache.get(card_id, "Answer not found or expired.")
    await callback.message.answer(f"✅ Answer:\n\n{answer}")
    await callback.answer()


if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
