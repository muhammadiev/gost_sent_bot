import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from docx import Document
import asyncio

# Bot configuration
TELEGRAM_BOT_TOKEN = "7063427428:AAEvheXmzXp8RbfMgLz0M-zQ3u2xS8-amN8"  # Replace with your bot token
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)

dp = Dispatcher(storage=MemoryStorage())

MAX_OPTION_LENGTH = 100  # Telegram's maximum allowed length for poll options

bot = Bot(token=TELEGRAM_BOT_TOKEN, request_timeout=60)


def load_questions_from_docx(docx_path):
    """Load questions and answers from a .docx file."""
    questions = []
    try:
        document = Document(docx_path)
        for table in document.tables:
            for row in table.rows[1:]:  # Skip the header row
                cells = row.cells
                if len(cells) >= 5:
                    question_text = cells[1].text.strip()
                    correct_answer = cells[2].text.strip()
                    options = [
                        cells[2].text.strip(),  # Correct answer
                        cells[3].text.strip(),
                        cells[4].text.strip(),
                        cells[5].text.strip(),
                    ]

                    # Truncate only options exceeding MAX_OPTION_LENGTH
                    options = [opt if len(opt) <= MAX_OPTION_LENGTH else opt[:MAX_OPTION_LENGTH-10] + "..." for opt in options]

                    # Truncate correct answer if necessary
                    correct_answer = correct_answer if len(correct_answer) <= MAX_OPTION_LENGTH else correct_answer[:MAX_OPTION_LENGTH-10] + "..."

                    if question_text and correct_answer and all(options):
                        random.shuffle(options)  # Shuffle the options
                        questions.append({
                            "question": question_text,
                            "correct": correct_answer,
                            "options": options,
                        })
                    else:
                        logging.warning("Skipped a question with missing text or correct answer.")
        logging.info(f"{len(questions)} questions loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading questions from .docx: {e}")
    return questions


questions = load_questions_from_docx("quiz.docx")  # Replace with your .docx file path
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
