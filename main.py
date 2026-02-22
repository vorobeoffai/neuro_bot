import asyncio
import os
import logging
import base64
import io
import docx
import PyPDF2
import httpx 
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.client.session.aiohttp import AiohttpSession
from groq import Groq

# --- ⚙️ КОНФИГУРАЦИЯ ---
API_TOKEN = '7993411757:AAE-uvrhVkoie5wbDpznnFAXVjIAfoDspYI'
GROQ_KEY = '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'
BOT_USERNAME = "neuro_ai_super_bot" # ⚠️ ЗАМЕНИ НА ЮЗЕРНЕЙМ СВОЕГО БОТА (без @)

# 🛡 ТВОИ ДАННЫЕ ПРОКСИ (Вписал то, что ты скинул)
PROXY_URL = "socks5://rP4AjF:Q9TK72@45.145.57.210:11121"

# 👑 ТВОЙ ID АДМИНА
ADMIN_ID = 123456789  # ⚠️ ЗАМЕНИ НА СВОИ ЦИФРЫ

# Файлы и ссылки
DB_FILE = "users.txt"
DONATE_LINK = "https://yoomoney.ru/to/410014132410583"

# --- 🧠 МОДЕЛИ ---
MODEL_TEXT = "llama-3.3-70b-versatile" 
MODEL_VISION = "llama-3.2-11b-vision-preview" 
MODEL_AUDIO = "whisper-large-v3"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 🔌 ИНИЦИАЛИЗАЦИЯ (СМЕШАННАЯ ТЕХНОЛОГИЯ) ---
try:
    # 1. Настройка прокси для Groq (через httpx)
    # Используем таймаут побольше, так как прокси может быть медленным
    proxy_client = httpx.Client(proxy=PROXY_URL, timeout=60.0)
    groq_client = Groq(api_key=GROQ_KEY, http_client=proxy_client)
    
    # 2. Настройка прокси для Telegram (через aiohttp)
    if PROXY_URL:
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=API_TOKEN, session=session)
        logger.info("✅ Бот и Нейросеть работают через PROXY")
    else:
        bot = Bot(token=API_TOKEN)
        
    dp = Dispatcher()
except Exception as e:
    logger.critical(f"Ошибка настройки прокси: {e}")
    exit(1)

user_history = {}

# --- 📊 БАЗА ДАННЫХ ---
def add_user_to_db(user_id):
    users = get_all_users()
    if str(user_id) not in users:
        with open(DB_FILE, "a") as f:
            f.write(f"{user_id}\n")

def get_all_users():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return [line.strip() for line in f.readlines()]

def count_users():
    return len(get_all_users())

# --- 🧠 СИСТЕМНЫЙ ПРОМПТ ---
def get_system_prompt(user_name):
    current_date = datetime.now().strftime("%d.%m.%Y")
    return (
        f"Ты — NEURO, умный и эмпатичный ИИ. Твой собеседник: {user_name}.\n"
        f"📅 **СЕГОДНЯШНЯЯ ДАТА:** {current_date}. Ты живешь в настоящем времени.\n"
        "ГЛАВНОЕ ПРАВИЛО: АДАПТИРУЙСЯ ПОД КОНТЕКСТ.\n\n"
        "1. **Обычное общение:** Отвечай ПРОСТО, ТЕПЛО и ДОБРОЖЕЛАТЕЛЬНО. Как живой друг.\n"
        "2. **Рабочие задачи:** Включай режим ЭКСПЕРТА (структура, факты).\n"
        "3. **Конфиденциальность:** Ты — система NEURO. Не упоминай Llama/Groq.\n"
        "4. **ЧИСТОТА ЯЗЫКА:** Использовать ТОЛЬКО РУССКИЙ ЯЗЫК (кириллицу)."
    )

# --- ⌨️ МЕНЮ ---
def get_persistent_menu():
    kb = [
        [
            KeyboardButton(text="🗑 Новая тема"), 
            KeyboardButton(text="❤️ Поблагодарить создателя", web_app=WebAppInfo(url=DONATE_LINK))
        ],
        [
            KeyboardButton(text="📱 Другие сервисы"), 
            KeyboardButton(text="📢 Поделиться")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_ecosystem_keyboard():
    kb = [
        [InlineKeyboardButton(text="🔐 Сервис на 3 буквы", url="https://t.me/neuroai_vpn_bot")],
        [InlineKeyboardButton(text="🎮 Steam Pay", url="https://t.me/neuro_steam_bot")],
        [InlineKeyboardButton(text="🚀 Продвижение SMM", url="https://t.me/neuropromoution_bot")],
        [InlineKeyboardButton(text="🌐 Покупка eSIM", url="https://t.me/neuroesim_bot")],
        [InlineKeyboardButton(text="❤️ Знакомства", url="https://t.me/neuro_friends_bot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_share_keyboard():
    share_url = f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}&text=Попробуй%20этого%20бота!%20Он%20крутой."
    kb = [[InlineKeyboardButton(text="↗️ Отправить другу", url=share_url)]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- 🛡 БЕЗОПАСНАЯ ОТПРАВКА ---
async def send_safe_message(message, text):
    try:
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.warning(f"Markdown Error: {e}")
        await message.answer(text, parse_mode=None)

# --- 🛠 ФУНКЦИИ ЧТЕНИЯ ---
def read_docx(file_stream):
    try:
        doc = docx.Document(file_stream)
        text = []
        for p in doc.paragraphs:
            if p.text.strip(): text.append(p.text)
        for t in doc.tables:
            for r in t.rows:
                row_data = [c.text for c in r.cells if c.text.strip()]
                if row_data: text.append(" | ".join(row_data))
        return "\n".join(text)
    except: return ""

def read_pdf(file_stream):
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_stream)
        for page in reader.pages:
            t = page.extract_text()
            if t: text += t + "\n"
        return text
    except: return ""

# --- ЗАПРОС К НЕЙРОСЕТИ ---
async def query_groq(messages, model=MODEL_TEXT):
    try:
        # Здесь запрос идет через httpx прокси (как в Edius)
        completion = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.6, 
            max_tokens=3000
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq Proxy Error: {e}")
        return "⚠️ Проблема с соединением (Proxy). Попробуй еще раз через минуту."

# --- 🎮 ОБРАБОТЧИКИ ---

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        count = count_users()
        await message.answer(f"📊 **Статистика бота:**\n\n👥 Подписчиков: **{count}**")
    else:
        await message.answer("Я не знаю такой команды 🤷‍♂️")

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    add_user_to_db(message.from_user.id)
    
    welcome_text = (
        f"👋 **Привет, {user_name}! Я — NEURO.**\n\n"
        "Рад тебя видеть! Я твой умный помощник и собеседник.\n"
        "Можешь скинуть мне документ для анализа или голосовое — я во всем разберусь.\n\n"
        "А можешь просто написать «Привет» и поболтать. Я всегда на связи! 😊\n\n"
        "👇 *Меню управления внизу.*"
    )
    
    user_history[message.chat.id] = [{"role": "system", "content": get_system_prompt(user_name)}]
    await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_persistent_menu())

@dp.message(F.text == "🗑 Новая тема")
async def menu_new_topic(message: types.Message):
    user_name = message.from_user.first_name
    user_history[message.chat.id] = [{"role": "system", "content": get_system_prompt(user_name)}]
    await message.answer("👌 Хорошо, забыли старое. О чем хочешь поговорить теперь?", reply_markup=get_persistent_menu())

@dp.message(F.text == "📱 Другие сервисы")
async def menu_services(message: types.Message):
    text = (
        "🤖 **Экосистема NEURO**\n\n"
        "У нас есть полезные боты на все случаи жизни:\n\n"
        "🔐 **Сервис на 3 буквы**\n"
        "🎮 **Steam** — пополнение баланса без проблем\n"
        "🚀 **PR** — мощное продвижение в соцсетях\n"
        "🌐 **eSIM** — интернет в любой точке мира\n"
        "❤️ **Friends** — интересные знакомства\n\n"
        "👇 *Выбирай нужный сервис:* "
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_ecosystem_keyboard())

@dp.message(F.text == "📢 Поделиться")
async def menu_share(message: types.Message):
    await message.answer(
        "Нажми кнопку ниже, чтобы отправить ссылку другу! 👇",
        reply_markup=get_share_keyboard()
    )

# 1. ФОТО
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await bot.send_chat_action(message.chat.id, action="typing")
    user_name = message.from_user.first_name
    add_user_to_db(message.from_user.id)
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_data = io.BytesIO()
    await bot.download_file(file.file_path, file_data)
    
    base64_image = base64.b64encode(file_data.getvalue()).decode('utf-8')
    caption = message.caption if message.caption else "Что на фото?"
    
    final_prompt = f"Пользователь {user_name} прислал фото: {caption}. Опиши подробно на русском языке."

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": final_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }
    ]
    
    try:
        completion = groq_client.chat.completions.create(
            model=MODEL_VISION,
            messages=messages,
            temperature=0.5,
            max_tokens=1500
        )
        answer = completion.choices[0].message.content
        await send_safe_message(message, answer)
    except Exception as e:
        await message.answer("⚠️ Извини, сейчас у меня обновление зрительных функций. Пока не могу разобрать, что на картинке. Давай лучше текстом или голосом?")

# 2. АУДИО
@dp.message(F.voice | F.audio)
async def handle_audio(message: types.Message):
    await message.answer("🎧 Слушаю...")
    user_name = message.from_user.first_name
    add_user_to_db(message.from_user.id)
    
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    file = await bot.get_file(file_id)
    file_path = f"temp_{file_id}.ogg"
    await bot.download_file(file.file_path, file_path)
    
    try:
        with open(file_path, "rb") as f:
            # Аудио тоже пойдет через прокси, так как groq_client настроен глобально
            transcription = groq_client.audio.transcriptions.create(
                file=(file_path, f.read()),
                model=MODEL_AUDIO,
                language="ru"
            )
        
        messages = [
            {"role": "system", "content": get_system_prompt(user_name)},
            {"role": "user", "content": f"Текст голосового: \"{transcription.text}\". Если это вопрос — ответь. Если просто рассказ — поддержи беседу."}
        ]
        summary = await query_groq(messages, model=MODEL_TEXT)
        
        await send_safe_message(message, f"🗣 **Ты сказал:**\n{transcription.text}\n\n💬 **Ответ:**\n{summary}")

    except Exception as e:
        await message.answer("Что-то пошло не так с аудио, извини.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

# 3. ДОКУМЕНТЫ
@dp.message(F.document)
async def handle_doc(message: types.Message):
    user_name = message.from_user.first_name
    add_user_to_db(message.from_user.id)
    file_name = message.document.file_name.lower()
    
    if not file_name.endswith(('.docx', '.pdf')):
        await message.answer("Я умею читать только **PDF** и **Word** файлы. Попробуй другой формат? 😊")
        return

    await message.answer("📄 Получил файл. Сейчас изучу...")
    file = await bot.get_file(message.document.file_id)
    file_data = io.BytesIO()
    await bot.download_file(file.file_path, file_data)
    file_data.seek(0)
    
    text = read_docx(file_data) if file_name.endswith('.docx') else read_pdf(file_data)
    
    if not text.strip():
        await message.answer("Файл пустой, тут нечего читать 🤷‍♂️")
        return

    messages = [
        {"role": "system", "content": get_system_prompt(user_name)}, 
        {"role": "user", "content": f"Проанализируй этот документ (Режим ЭКСПЕРТА). Структурируй ответ, выдели главное:\n\n{text[:25000]}"}
    ]
    answer = await query_groq(messages, model=MODEL_TEXT)
    await send_safe_message(message, answer)

# 4. ТЕКСТ (Защита от кнопок)
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    if message.text in ["🗑 Новая тема", "❤️ Поблагодарить создателя", "📱 Другие сервисы", "📢 Поделиться"]:
        return

    add_user_to_db(message.from_user.id)
    uid = message.chat.id
    user_name = message.from_user.first_name

    if uid not in user_history: 
        user_history[uid] = [{"role": "system", "content": get_system_prompt(user_name)}]
    
    user_history[uid].append({"role": "user", "content": message.text})
    if len(user_history[uid]) > 12: 
        user_history[uid] = [user_history[uid][0]] + user_history[uid][-10:]
    
    await bot.send_chat_action(uid, action="typing")
    answer = await query_groq(user_history[uid], model=MODEL_TEXT)
    user_history[uid].append({"role": "assistant", "content": answer})
    await send_safe_message(message, answer)

async def main():
    logger.info("🚀 NEURO Bot (HOSTING READY) запущен")
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: f.write("")
        
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
