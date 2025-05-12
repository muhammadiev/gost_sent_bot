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
TELEGRAM_BOT_TOKEN = "7088052971:AAGQuQad0WCIyiw8p_YG50okXQDrUVewGFw"  # Replace with your token
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN, request_timeout=60)
dp = Dispatcher(storage=MemoryStorage())

MAX_OPTION_LENGTH = 100  # Telegram max option length

# User and group states
user_scores = {}  # key: (chat_id, user_id), value: {'score': x, 'amount': y}
user_current_question = {}  # key: (chat_id, user_id)

# Decode base64 if needed
# def decode_base64(encoded_str):
#     try:
#         return base64.b64decode(encoded_str).decode('utf-8')
#     except Exception as e:
#         logging.error(f"Error decoding base64 string: {e} (data preview: {encoded_str[:30]}...)")
#         return ""


import base64
import logging
import re


def decode_base64(encoded_str):
    try:
        decoded_bytes = base64.b64decode(encoded_str.strip())

        # First, try UTF-8 decode
        try:
            decoded_text = decoded_bytes.decode('utf-8')
            return decoded_text
        except UnicodeDecodeError:
            pass

        # Try to identify format if not UTF-8
        decoded_preview = decoded_bytes[:1000]  # limit to check
        decoded_str_preview = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in decoded_preview)

        # Check if it looks like RTF
        if decoded_str_preview.startswith('{\\rtf'):
            logging.info("Detected RTF format.")
            return "[RTF FORMAT] Save to file and open with Word or WordPad."

        # Check for LaTeX patterns
        if re.search(rb'\\(?:frac|sum|int|sqrt|begin\{equation\})', decoded_bytes):
            return "[LaTeX] content detected."

        # Check for MathML
        if b"<math" in decoded_bytes:
            return "[MathML] content detected."

        return "[Binary/Unknown Format] Save to file for inspection."

    except Exception as e:
        logging.error(f"Error decoding base64 string: {e} (data preview: {encoded_str[:30]}...)")
        return ""

def extract_text_from_node(plain_elem, base64_elem, label=""):
    plain_text = plain_elem.text.strip() if plain_elem is not None and plain_elem.text else ""
    decoded_text = ""

    if base64_elem is not None and base64_elem.text:
        raw = decode_base64(base64_elem.text.strip())
        decoded_text = ''.join(c for c in raw if c.isprintable()).strip()

    if plain_text and decoded_text and plain_text != decoded_text:
        # If both exist but are different, combine or prioritize
        return f"{plain_text} ({label or 'extra content'})"
    elif plain_text:
        return plain_text
    elif decoded_text:
        return decoded_text
    return ""


# Load questions from XML
def load_questions_from_xml(xml_path):
    questions = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for q_elem in root.findall(".//QuestionBlock"):
            question_text_elem = q_elem.find(".//Content/PlainText")
            base64_question_elem = q_elem.find(".//Content/RichViewFormatBASE64")

            question_text = extract_text_from_node(question_text_elem, base64_question_elem, label="math/extra")

            if not question_text:
                continue  # Skip if no valid question

            answers = []
            correct_answer = None

            for answer_elem in q_elem.findall(".//Answers/Answer"):
                answer_text_elem = answer_elem.find(".//Content/PlainText")
                base64_elem = answer_elem.find(".//RichViewFormatBASE64")

                answer_text = extract_text_from_node(answer_text_elem, base64_elem, label="math")

                if not answer_text:
                    continue

                is_correct = answer_elem.get("IsCorrect") == "Yes"
                if is_correct:
                    correct_answer = answer_text

                answers.append(answer_text)

            # Ensure correct is in options
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
from aiogram import types
from aiogram.filters import Command

@dp.message(Command("start"))
async def start_quiz(message: types.Message):
    chat = message.chat
    user = message.from_user

    # Create a key based on chat and user for score tracking
    key = (chat.id, user.id)
    user_scores[key] = {"score": 0, "amount": 0}

    if chat.type == "private":
        await message.answer("📚 Quiz boshlandi! Har bir to‘g‘ri javob 1 ball.\n/help buyrug‘i yordam beradi.")
        await send_question(chat.id, user.id, chat.type)
    elif chat.type in ["group", "supergroup"]:
        await message.reply("📚 Guruhdagi viktorina boshlandi! Har bir to‘g‘ri javob 1 ball.")
        await send_question(chat.id, user.id,chat.type)
    else:
        await message.reply("Bu buyruq faqat shaxsiy yoki guruh chatda ishlaydi.")



# END Command
@dp.message(Command("end"))
async def end_quiz(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    key = (chat_id, user_id)

    if message.chat.type == 'private':
        # Private chat: show only this user's result
        if key in user_scores:
            score = user_scores[key]["score"]
            total = user_scores[key]["amount"]
            del user_scores[key]
            user_current_question.pop(key, None)

            await message.reply(f"✅ Quiz tugadi! Yakuniy natija: {score}/{total} \nBoshlash uchun /start ni bosing")
            await bot.send_message(
                5910341036,
                f'{message.from_user.first_name} ({user_id}) quizni {score}/{total} bilan tugatdi.'
            )
        else:
            await message.reply("Siz hali quizni boshlamagansiz. Boshlash uchun /start ni bosing.")

    else:
        # Group chat: show all users’ results in this chat
        scores_in_chat = [
            (uid, data["score"], data["amount"])
            for (cid, uid), data in user_scores.items()
            if cid == chat_id
        ]

        if not scores_in_chat:
            await message.reply("Hali hech kim quizni yakunlamagan.Boshlash uchun /start ni bosing")
            return

        # Sort by score descending
        sorted_scores = sorted(scores_in_chat, key=lambda x: (-x[1], x[0]))

        result_text = "📊 *Quiz yakunlari:*\n\n"
        for idx, (uid, score, total) in enumerate(sorted_scores, start=1):
            user = await bot.get_chat_member(chat_id, uid)
            name = user.user.first_name
            result_text += f"{idx}. {name} — {score}/{total}\n"

            # Optionally delete each after showing
            user_scores.pop((chat_id, uid), None)
            user_current_question.pop((chat_id, uid), None)

        await message.answer(result_text, parse_mode="Markdown")


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
async def send_question(chat_id, user_id, chat_type):
    if chat_type != 'private':
        await asyncio.sleep(2)
    key = (chat_id, user_id)
    if key not in user_scores:
        return

    question = random.choice(questions)
    if not question["question"] or not all(question["options"]):
        await send_question(chat_id, user_id)

        return

    user_current_question[key] = question

    try:
        # Truncate each option to 100 characters
        options = [opt[:100] for opt in question["options"]]

        await bot.send_poll(
            chat_id=chat_id,
            question=question["question"][:300],  # optional: truncate question too
            options=options,
            type="quiz",
            correct_option_id=options.index(question["correct"][:100]),
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

    # Find the chat this user belongs to (brute search)
    for (chat_id, uid), data in user_scores.items():
        if uid == user_id:
            key = (chat_id, user_id)
            break
    else:
        return  # User not found in active scores

    if key not in user_current_question:
        return

    question = user_current_question[key]
    selected_option = poll_answer.option_ids[0]

    # Update total attempted
    user_scores[key]["amount"] += 1

    # Check if correct
    if question["options"][selected_option] == question["correct"]:
        user_scores[key]["score"] += 1

    # Guessing the chat type: if chat_id is positive, it's private chat; if negative, it's a group or supergroup
    chat_type = "private" if key[0] > 0 else "group"

    # Continue to next question
    await asyncio.sleep(1.5)
    await send_question(key[0], user_id, chat_type)



# Start polling
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
