import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from docx import Document
import asyncio
import base64
import xml.etree.ElementTree as ET

# Bot configuration
TELEGRAM_BOT_TOKEN = "6792357240:AAGHvSc98g6Lc0hSULk_2ZokY8pIcwg8G5o"  # Replace with your token
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN, request_timeout=60)
dp = Dispatcher(storage=MemoryStorage())

MAX_OPTION_LENGTH = 100  # Telegram max option length

# User and group states
user_scores = {}  # key: (chat_id, user_id), value: {'score': x, 'amount': y}
user_current_question = {}  # key: (chat_id, user_id)

# Decode base64 if needed
def decode_base64(encoded_str):
    try:
        return base64.b64decode(encoded_str).decode('utf-8')
    except Exception as e:
        logging.error(f"Error decoding base64 string: {e}")
        return ""

# Load questions from XML
def load_questions_from_xml(xml_path):
    questions = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for q_elem in root.findall(".//QuestionBlock"):
            question_text_elem = q_elem.find(".//Content/PlainText")
            if question_text_elem is None:
                continue

            question_text = question_text_elem.text.strip() if question_text_elem.text else ""
            answers = []
            correct_answer = None

            for answer_elem in q_elem.findall(".//Answers/Answer"):
                answer_text_elem = answer_elem.find(".//Content/PlainText")
                if answer_text_elem is None:
                    continue

                answer_text = answer_text_elem.text.strip()
                is_correct = answer_elem.get("IsCorrect") == "Yes"

                base64_elem = answer_elem.find(".//RichViewFormatBASE64")
                if base64_elem is not None:
                    answer_text = decode_base64(base64_elem.text.strip())

                if is_correct:
                    correct_answer = answer_text

                answers.append(answer_text)

            if correct_answer and correct_answer not in answers:
                answers.insert(0, correct_answer)

            if question_text and correct_answer and all(answers):
                random.shuffle(answers)
                questions.append({
                    "question": question_text,
                    "correct": correct_answer,
                    "options": answers
                })

        logging.info(f"{len(questions)} questions loaded from XML.")

    except Exception as e:
        logging.error(f"Error loading questions: {e}")
    return questions

questions = load_questions_from_xml("quiz.xml")


# START Command
@dp.message(Command("start"))
async def start_quiz(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    key = (chat_id, user_id)

    user_scores[key] = {"score": 0, "amount": 0}
    await message.reply("📚 Quiz boshlandi! Har bir to‘g‘ri javob 1 ball.\n/help buyrug‘i yordam beradi.")
    await send_question(chat_id, user_id)


# END Command
@dp.message(Command("end"))
async def end_quiz(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    key = (chat_id, user_id)

    if key in user_scores:
        score = user_scores[key]["score"]
        total = user_scores[key]["amount"]
        del user_scores[key]
        user_current_question.pop(key, None)

        await message.reply(f"✅ Quiz tugadi! Yakuniy natija: {score}/{total}")
        await bot.send_message(5910341036, f'{message.from_user.first_name} ({user_id}) quizni {score}/{total} bilan tugatdi.')
    else:
        await message.reply("Siz hali quizni boshlamagansiz. Boshlash uchun /start ni bosing.")


# HELP Command
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.reply(
        "📘 Buyruqlar:\n"
        "/start - Quizni boshlash\n"
        "/help - Yordam\n"
        "/end - Quizni yakunlash"
    )


# Send random question
async def send_question(chat_id, user_id):
    key = (chat_id, user_id)
    if key not in user_scores:
        return

    question = random.choice(questions)
    if not question["question"] or not all(question["options"]):
        await send_question(chat_id, user_id)
        return

    user_current_question[key] = question

    try:
        await bot.send_poll(
            chat_id=chat_id,
            question=question["question"],
            options=question["options"],
            type="quiz",
            correct_option_id=question["options"].index(question["correct"]),
            is_anonymous=False,
        )
    except Exception as e:
        logging.warning(f"Poll sending failed: {e}")
        await bot.send_message(chat_id, "❌ Savolni yuborishda xatolik yuz berdi.")
        return

    await bot.send_message(chat_id, "⏳ Keyingi savol avtomatik yuboriladi. Tugatish: /end")


# Handle answers
@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id

    # Find the active chat the user was in (brute search)
    for key in user_scores:
        if key[1] == user_id:
            chat_id = key[0]
            break
    else:
        return

    key = (chat_id, user_id)
    if key not in user_current_question:
        return

    selected_option = poll_answer.option_ids[0]
    question = user_current_question[key]
    user_scores[key]["amount"] += 1

    if question["options"][selected_option] == question["correct"]:
        user_scores[key]["score"] += 1

    await send_question(chat_id, user_id)


# Start polling
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
