import os
import asyncio
import aiosqlite
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)

# === ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===
load_dotenv()

# === ГЛОБАЛЬНЫЕ КОНСТАНТЫ ===
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError(
        "❌ Переменная TELEGRAM_TOKEN не задана.\n"
        "Создайте файл .env в корне проекта со строкой:\n"
        "TELEGRAM_TOKEN=ваш_токен_от_BotFather"
    )

DB_PATH = "users.db"
NAME, AGE = range(2)


# === ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ===
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL
            )
        """)
        await db.commit()


# === КОМАНДЫ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот с сохранением в базу.\n"
        "Используй:\n"
        "/reg — начать регистрацию\n"
        "/me — посмотреть свои данные"
    )


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Как тебя зовут?")
    return NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Имя не может быть пустым. Попробуй ещё раз:")
        return NAME
    context.user_data["name"] = name
    await update.message.reply_text("Сколько тебе лет?")
    return AGE


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age_text = update.message.text.strip()
    if not age_text.isdigit():
        await update.message.reply_text("Пожалуйста, введи возраст числом:")
        return AGE
    age = int(age_text)
    if age < 0 or age > 150:
        await update.message.reply_text("Возраст должен быть от 0 до 150. Попробуй снова:")
        return AGE

    user_id = update.effective_user.id
    name = context.user_data.get("name", "Неизвестно")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (telegram_id, name, age) VALUES (?, ?, ?)",
            (user_id, name, age)
        )
        await db.commit()

    await update.message.reply_text(f"Отлично! Регистрация завершена, {name}!")
    return ConversationHandler.END


async def show_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT name, age FROM users WHERE telegram_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()

    if row:
        name, age = row
        await update.message.reply_text(f"Тебя зовут {name}, тебе {age} лет.")
    else:
        await update.message.reply_text("Ты ещё не зарегистрирован. Напиши /reg.")


# === ОСНОВНАЯ ФУНКЦИЯ ===
async def main():
    await init_db()

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("reg", start_registration)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("me", show_me))
    app.add_handler(conv_handler)

    print("✅ Бот Stage 3 (с SQLite и .env) запущен! Нажми Ctrl+C для остановки.")
    await app.run_polling()


# === ТОЧКА ВХОДА ===
if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен вручную.")
    finally:
        pass