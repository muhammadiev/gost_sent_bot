import logging
import random

from aiofiles.os import replace
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from docx import Document
import asyncio

# Bot configuration
TELEGRAM_BOT_TOKEN = "7063427428:AAEvheXmzXp8RbfMgLz0M-zQ3u2xS8-amN8"  # Replace with your bot token
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN, request_timeout=60)
dp = Dispatcher(storage=MemoryStorage())
MAX_OPTION_LENGTH = 100  # Telegram's maximum allowed length for poll options


def format_exponents(expression):
    """Convert '^' notation to Unicode superscript format."""
    superscripts = {
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"
    }
    formatted_expression = []

    for term in expression.split("*"):
        base, exponent = term.split("^")
        formatted_exponent = ''.join(superscripts[digit] for digit in exponent)
        formatted_expression.append(f"{base}{formatted_exponent}")

    return " × ".join(formatted_expression)




# Load questions from docx file
def load_questions_from_docx(docx_path):
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
                    options = [opt if len(opt) <= MAX_OPTION_LENGTH else opt[:MAX_OPTION_LENGTH - 10] + "..." for opt in options]
                    if question_text and correct_answer and all(options):
                        random.shuffle(options)
                        questions.append({"question": question_text, "correct": correct_answer, "options": options})
                    else:
                        logging.warning("Skipped a question due to missing data.")
        logging.info(f"{len(questions)} questions loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading questions from .docx: {e}")
    return questions  # Limit to 50 questions

questions = load_questions_from_docx("quiz.docx")
user_scores = {}
active_quiz_tasks = {}  # Store active timers

# Start quiz command
@dp.message(Command("start"))
async def start_quiz(message: types.Message):
    user_id = message.from_user.id
    user_scores[user_id] = {"score": 0, "index": 0, "amount": 0}
    await message.answer("Gost quiz botga xush kelibsiz. Type /help komandalar haqida.")
    await send_question(user_id)

# End quiz command
@dp.message(Command("end"))
async def end_quiz(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_scores:
        score = user_scores[user_id]["score"]
        total = user_scores[user_id]["amount"]
        del user_scores[user_id]  # Clear user data
        if user_id in active_quiz_tasks:
            active_quiz_tasks[user_id].cancel()  # Cancel the active timer
            del active_quiz_tasks[user_id]
        await message.answer(f"Quiz ended! 🎉 Your final score: {score}/{total}\nQayta boshlash uchun /start ni bosing.")
    else:
        await message.answer("You haven't started a quiz yet. Type /start to begin.")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("Commands:\n/start - Start the quiz\n/help - Show help\n/end - End the quiz and see your score.")

# Function to send questions
async def send_question(user_id):
    if user_id not in user_scores:
        return

    user_data = user_scores[user_id]
    user_data["index"] += 1

    if user_data["index"] > 50:  # End quiz after 50 questions
        await bot.send_message(chat_id=user_id, text="Quiz tugadi! Press /end to see your score.")
        return

    question = random.choice(questions)

    # Send the poll question
    poll_message = await bot.send_poll(
        chat_id=user_id,
        question=question["question"],
        options=question["options"],
        type="quiz",
        correct_option_id=question["options"].index(question["correct"]),
        is_anonymous=True,
        open_period=30  # 30-second timer
    )

    # Start a timer to send the next question if no answer is received
    task = asyncio.create_task(timer_for_next_question(user_id, 30))
    active_quiz_tasks[user_id] = task  # Store active task for cancellation

# Timer to send next question after 30 seconds
async def timer_for_next_question(user_id, timeout):
    await asyncio.sleep(timeout)
    if user_id in user_scores:
        await send_question(user_id)  # Send next question automatically after timeout

# Handle poll answers
@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    if user_id not in user_scores:
        return

    if user_id in active_quiz_tasks:
        active_quiz_tasks[user_id].cancel()  # Cancel the timeout task if the user answers
        del active_quiz_tasks[user_id]  # Remove from active tasks

    user_data = user_scores[user_id]
    selected_option = poll_answer.option_ids[0] if poll_answer.option_ids else None
    user_data["amount"] += 1

    if selected_option is not None:
        question = random.choice(questions)
        if question["options"][selected_option] == question["correct"]:
            user_data["score"] += 1

    await send_question(user_id)  # Send the next question

# Main entry point
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
