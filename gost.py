import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from docx import Document
import asyncio

# Bot configuration
TELEGRAM_BOT_TOKEN = "6792357240:AAGHvSc98g6Lc0hSULk_2ZokY8pIcwg8G5o"  # Replace with your bot token
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)

dp = Dispatcher(storage=MemoryStorage())

MAX_OPTION_LENGTH = 100  # Telegram's maximum allowed length for poll options

bot = Bot(token=TELEGRAM_BOT_TOKEN, request_timeout=60)

import base64
import xml.etree.ElementTree as ET


def decode_base64(encoded_str):
    """Helper function to decode base64-encoded strings."""
    try:
        return base64.b64decode(encoded_str).decode('utf-8')
    except Exception as e:
        logging.error(f"Error decoding base64 string: {e}")
        return ""


def load_questions_from_xml(xml_path):
    """Load questions and answers from an XML file."""
    questions = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for q_elem in root.findall(".//QuestionBlock"):  # Find all QuestionBlock elements
            question_text_elem = q_elem.find(".//Content/PlainText")
            if question_text_elem is None:
                logging.warning("No question text found, skipping question.")
                continue

            question_text = question_text_elem.text.strip() if question_text_elem.text else ""

            # Extract answers
            answers = []
            correct_answer = None
            for answer_elem in q_elem.findall(".//Answers/Answer"):
                answer_text_elem = answer_elem.find(".//Content/PlainText")
                if answer_text_elem is None:
                    logging.warning("Answer text missing, skipping this answer.")
                    continue

                answer_text = answer_text_elem.text.strip()
                is_correct = answer_elem.get("IsCorrect") == "Yes"

                # Decode the base64 if needed (only if the base64 part is used in the XML)
                if answer_text_elem.find(".//RichViewFormatBASE64") is not None:
                    base64_elem = answer_elem.find(".//RichViewFormatBASE64")
                    answer_text = decode_base64(base64_elem.text.strip()) if base64_elem is not None else answer_text

                if is_correct:
                    correct_answer = answer_text

                answers.append(answer_text)

            # Ensure the correct answer is in the options and shuffle them
            if correct_answer and correct_answer not in answers:
                answers.insert(0, correct_answer)  # Add it to the options list if missing

            if question_text and correct_answer and all(answers):
                random.shuffle(answers)
                questions.append({
                    "question": question_text,
                    "correct": correct_answer,
                    "options": answers
                })
            else:
                logging.warning(f"Skipped an invalid question: {question_text}")

        logging.info(f"{len(questions)} questions loaded successfully from XML.")

    except Exception as e:
        logging.error(f"Error loading questions from XML: {e}")
    return questions


questions = load_questions_from_xml("quiz.xml")  # Replace with your .docx file path
user_scores = {}  # Dictionary to track user scores
user_current_question = {}  # Store the currently asked question


# Command to start the quiz
@dp.message(Command("start"))
async def start_quiz(message: types.Message):
    user_id = message.from_user.id
    user_scores[user_id] = {"score": 0, "amount": 0}  # Initialize user score
    await message.answer("gost quiz botga xush kelibsiz.\nType /help kommadalar haqida.")
    await send_question(user_id)


# Command to end the quiz
@dp.message(Command("end"))
async def end_quiz(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_scores:
        score = user_scores[user_id]["score"]
        total_questions = user_scores[user_id]["amount"]
        del user_scores[user_id]  # Clear user data
        del user_current_question[user_id]  # Remove current question tracking
        await message.answer(f"Quiz ended!! 🎉 Your final score: {score}/{total_questions}\nQayta quizni boshlash uchun /start ni bosing")
        await bot.send_message(5910341036,f'{message.from_user.first_name} ended the quiz and {score}/{total_questions}')
    else:
        await message.answer("You haven't started a quiz yet. Type /start to begin.")


# Command to display help
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "Commands:\n/start - Start the quiz\n/help - Show help\n/end - Quizni tugatish va natijalarni olish"
    )


# Send a question to the user
async def send_question(user_id):
    if user_id not in user_scores:
        return

    # Pick a random question
    question = random.choice(questions)

    # Validate the question and options
    if not question["question"] or not all(question["options"]):
        logging.warning("Skipped sending a question due to missing text or options.")
        await send_question(user_id)  # Send another question
        return

    # Store the question for reference during scoring
    user_current_question[user_id] = question

    # Send the current question
    await bot.send_poll(
        chat_id=user_id,
        question=question["question"],
        options=question["options"],
        type="quiz",
        correct_option_id=question["options"].index(question["correct"]),
        is_anonymous=False,
    )

    await bot.send_message(
        chat_id=user_id,
        text="Press /end to end the quiz."
    )


# Handle poll answers
@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    if user_id not in user_scores or user_id not in user_current_question:
        return

    user_data = user_scores[user_id]
    question = user_current_question[user_id]  # Get the last asked question

    # Check if the answer is correct
    selected_option = poll_answer.option_ids[0] if poll_answer.option_ids else None
    if selected_option is not None:
        user_data["amount"] += 1
        if question["options"][selected_option] == question["correct"]:
            user_data["score"] += 1

    # Move to the next question
    await send_question(user_id)


# Main entry point to start the bot
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
