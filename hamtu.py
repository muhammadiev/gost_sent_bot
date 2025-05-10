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


def load_questions_from_docx(docx_path):
    """Load questions and answers from a .docx file."""
    questions = []
    try:
        document = Document(docx_path)
        for table in document.tables:
            for row in table.rows[0:]:  # Skip the header row
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

                    if question_text and correct_answer:
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


# Command to start the quiz
@dp.message(Command("start"))
async def start_quiz(message: types.Message):
    user_scores[message.from_user.id] = {"score": 0, "index": 0}  # Initialize user score
    await message.answer(
        "Welcome to the Quiz Bot! Let's get started.\nType /help for commands."
    )
    await send_question(message.from_user.id)


# Command to display help
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "Commands:\n/start - Start the quiz\n/help - Show help"
    )


# Send a question to the user
async def send_question(user_id):
    if user_id not in user_scores:
        return

    user_data = user_scores[user_id]
    question_index = user_data["index"]

    if question_index >= len(questions):
        # Quiz completed
        await bot.send_message(
            user_id, f"Quiz completed! 🎉\nYour final score: {user_data['score']} / {len(questions)}"
        )
        del user_scores[user_id]  # Clear user data
        return

    # Send the current question
    question = questions[question_index]
    await bot.send_poll(
        chat_id=user_id,
        question=question["question"],
        options=question["options"],
        type="quiz",
        correct_option_id=question["options"].index(question["correct"]),
        is_anonymous=False,
    )


# Handle poll answers
@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    if user_id not in user_scores:
        return

    user_data = user_scores[user_id]
    question_index = user_data["index"]
    question = questions[question_index]

    # Check if the answer is correct
    selected_option = poll_answer.option_ids[0] if poll_answer.option_ids else None
    if selected_option is not None:
        if question["options"][selected_option] == question["correct"]:
            user_data["score"] += 1

    # Move to the next question
    user_data["index"] += 1
    await send_question(user_id)


# Main entry point to start the bot
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())