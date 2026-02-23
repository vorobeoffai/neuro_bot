import asyncio
import os
import logging
import docx
import PyPDF2
import httpx 
import io 
from urllib.parse import quote 
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
BOT_USERNAME = "neuro_fast_bot" 

# 🛡 ПРОКСИ
PROXY_URL = "socks5://rP4AjF:Q9TK72@45.145.57.210:11121"

# 👑 ТВОЙ ID АДМИНА
ADMIN_ID = 480469657

DB_FILE = "users.txt"
DONATE_LINK = "https://yoomoney.ru/to/410014132410583"

# Модели
MODEL_TEXT = "llama-3.3-70b-versatile" 
MODEL_AUDIO = "whisper-large-v3"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 🔌 ИНИЦИАЛИЗАЦИЯ ---
try:
    timeout_config = httpx.Timeout(connect=20.0, read=600.0, write=60.0, pool=600.0)
    
    proxy_client = httpx.Client(
        proxy=PROXY_URL, 
        timeout=timeout_config,
        http2=False 
    )
    
    groq_client = Groq(api_key=GROQ_KEY, http_client=proxy_client)
    
    if PROXY_URL:
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=API_TOKEN, session=session)
        logger.info("✅ Бот запущен (Стабильная версия: Word, PDF, Голос)")
    else:
        bot = Bot(token=API_TOKEN)
        
    dp = Dispatcher()
except Exception as e:
    logger.critical(f"Start Error: {e}")
    exit(1)

user_history = {}

# --- ФУНКЦИИ ---
def add_user_to_db(user_id):
    users = get_all_users()
    if str(user_id) not in users:
        with open(DB_FILE, "a") as f: f.write(f"{user_id}\n")

def get_all_users():
    if not os.path.exists(DB_FILE): return []
    with open(DB_FILE, "r") as f: return [line.strip() for line in f.readlines()]

def count_users(): return len(get_all_users())

# 🔥 СИСТЕМНЫЙ ПРОМПТ
def get_system_prompt(user_name):
    current_date = datetime.now().strftime("%d.%m.%Y")
    return (
        f"Ты — NEURO. Собеседник: {user_name}.\n"
        f"📅 {current_date}.\n\n"
        "🧠 ТВОЯ ЗАДАЧА — РАБОТАТЬ С КОНТЕКСТОМ:\n"
        "1. Если тебе прислали текст документа — отвечай **СТРОГО** по этому тексту.\n"
        "2. Если в документе нет ответа на вопрос — так и скажи.\n\n"
        "🎭 ОФОРМЛЕНИЕ:\n"
        "1. ⛔️ **БЕЗ ЖИРНОГО ШРИФТА**: Не используй звездочки (**текст**).\n"
        "2. 🎨 **ЭМОДЗИ**: Используй эмодзи в начале строк вместо маркеров списка.\n"
        "3. **Структура:** Подробный ответ по пунктам."
    )

def get_persistent_menu():
    kb = [
        [KeyboardButton(text="🗑 Новая тема"), KeyboardButton(text="❤️ Поблагодарить создателя", web_app=WebAppInfo(url=DONATE_LINK))],
        [KeyboardButton(text="📱 Другие сервисы"), KeyboardButton(text="📢 Поделиться")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_ecosystem_keyboard():
    kb = [
        [InlineKeyboardButton(text="🔐 Сервис на 3 буквы", url="https://t.me/neuroai_vpn_bot")],
        [InlineKeyboardButton(text="🎮 Steam", url="https://t.me/neuro_steam_bot")],
        [InlineKeyboardButton(text="🚀 PR", url="https://t.me/neuropromoution_bot")],
        [InlineKeyboardButton(text="🌐 eSIM", url="https://t.me/neuroesim_bot")],
        [InlineKeyboardButton(text="❤️ Friends", url="https://t.me/neuro_friends_bot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_share_keyboard():
    bot_url = f"https://t.me/{BOT_USERNAME}"
    text_to_share = "Попробуй этого бота! 🚀"
    share_url = f"https://t.me/share/url?url={bot_url}&text={quote(text_to_share)}"
    
    kb = [[InlineKeyboardButton(text="↗️ Отправить другу", url=share_url)]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def send_safe_message(message, text):
    try: await message.answer(text, parse_mode=ParseMode.MARKDOWN)
    except: await message.answer(text, parse_mode=None)

# --- 📂 ЧИТАЛКА ФАЙЛОВ (ТОЛЬКО БАЗОВАЯ) ---
def read_any_document(file_stream, file_name):
    text = ""
    file_ext = os.path.splitext(file_name)[1].lower()
    
    try:
        # 1. DOCX (Word)
        if file_ext == '.docx':
            doc = docx.Document(file_stream)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        
        # 2. PDF
        elif file_ext == '.pdf':
            reader = PyPDF2.PdfReader(file_stream)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        
        # 3. Текстовые файлы
        else:
            raw_data = file_stream.read()
            try:
                text = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = raw_data.decode('cp1251')
                except UnicodeDecodeError:
                    text = raw_data.decode('latin-1', errors='ignore')

        return text.strip()
    except Exception as e:
        logger.error(f"Ошибка чтения файла: {e}")
        return ""

# --- ЗАПРОСЫ К НЕЙРОСЕТЯМ ---
async def transcribe_audio(file_bytes):
    try:
        transcription = groq_client.audio.transcriptions.create(
            file=("voice.ogg", file_bytes),
            model=MODEL_AUDIO,
            response_format="text"
        )
        return transcription
    except Exception as e:
        logger.error(f"Ошибка аудио: {e}")
        return ""

async def query_groq(messages, model=MODEL_TEXT):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            completion = groq_client.chat.completions.create(
                model=model, messages=messages, temperature=0.5, max_tokens=4000
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.warning(f"Error (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                return "Связь немного барахлит. Нажми '🗑 Новая тема' и спроси снова."

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"📊 Статистика:\n👥 Всего пользователей: **{count_users()}**")

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    add_user_to_db(message.from_user.id)
    user_history[message.chat.id] = [{"role": "system", "content": get_system_prompt(message.from_user.first_name)}]
    
    text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я NEURO — твой умный аналитик.\n\n"
        "🎙 Я ПОНИМАЮ ГОЛОСОВЫЕ!\n"
        "📄 ЧИТАЮ ДОКУМЕНТЫ (Word, PDF, Txt)\n\n"
        "👇 Отправь мне файл или запиши вопрос!"
    )
    await message.answer(text, reply_markup=get_persistent_menu())

@dp.message(F.text == "🗑 Новая тема")
async def menu_new_topic(message: types.Message):
    user_history[message.chat.id] = [{"role": "system", "content": get_system_prompt(message.from_user.first_name)}]
    await message.answer("👌 Память очищена.\n\n🎙 Жду новый вопрос или файл!", reply_markup=get_persistent_menu())

@dp.message(F.text == "📱 Другие сервисы")
async def menu_services(message: types.Message):
    text = (
        "🤖 Экосистема NEURO\n\n"
        "Ознакомьтесь с другими сервисами NEURO\n\n"
        "🔐 Сервис на 3 буквы\n"
        "🎮 Steam — пополнение баланса без проблем\n"
        "🚀 PR — мощное продвижение в соцсетях\n"
        "🌐 eSIM — интернет в любой точке мира\n"
        "❤️ Friends — интересные знакомства\n\n"
        "👇 Выбирай нужный сервис:"
    )
    await message.answer(text, reply_markup=get_ecosystem_keyboard())

@dp.message(F.text == "📢 Поделиться")
async def menu_share(message: types.Message):
    await message.answer("📲 Отправь другу:", reply_markup=get_share_keyboard())

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    add_user_to_db(message.from_user.id)
    await bot.send_chat_action(message.chat.id, action="upload_voice")
    
    file = await bot.get_file(message.voice.file_id)
    file_data = io.BytesIO()
    await bot.download_file(file.file_path, file_data)
    file_data.seek(0)
    
    text = await transcribe_audio(file_data.read())
    if not text:
        await message.answer("👂 Не удалось разобрать голосовое.")
        return

    await message.reply(f"🎤 Вы сказали:\n_{text}_", parse_mode=ParseMode.MARKDOWN)

    uid = message.chat.id
    if uid not in user_history: 
        user_history[uid] = [{"role": "system", "content": get_system_prompt(message.from_user.first_name)}]
    
    user_history[uid].append({"role": "user", "content": text})
    if len(user_history[uid]) > 12: 
        user_history[uid] = [user_history[uid][0]] + user_history[uid][-10:]

    await bot.send_chat_action(uid, action="typing")
    answer = await query_groq(user_history[uid])
    
    user_history[uid].append({"role": "assistant", "content": answer})
    await send_safe_message(message, answer)


# 🔥 ОБРАБОТЧИК ФАЙЛОВ
@dp.message(F.document)
async def handle_doc(message: types.Message):
    add_user_to_db(message.from_user.id)
    
    file = await bot.get_file(message.document.file_id)
    file_data = io.BytesIO()
    await bot.download_file(file.file_path, file_data)
    file_data.seek(0)
    
    # Читаем
    text = read_any_document(file_data, message.document.file_name)
    
    if not text or len(text) < 10: 
        await message.answer(
            "⚠️ Файл пуст или содержит только картинки (сканы).\n"
            "Я умею читать только текстовые слои. Пожалуйста, пришли файл, из которого можно скопировать текст."
        )
        return
    
    await message.answer("🧐 Анализирую документ...")
    
    prompt = (
        "⚠️ ИНСТРУКЦИЯ: Проведи глубокий анализ текста ниже.\n"
        "1. Отвечай ТОЛЬКО на основе этого текста.\n"
        "2. Выдели суть и ключевые моменты.\n\n"
        "📄 === НАЧАЛО ДОКУМЕНТА ===\n"
        f"{text[:30000]}\n"
        "📄 === КОНЕЦ ДОКУМЕНТА ==="
    )
    
    uid = message.chat.id
    if uid not in user_history:
        user_history[uid] = [{"role": "system", "content": get_system_prompt(message.from_user.first_name)}]
        
    messages = [
        {"role": "system", "content": get_system_prompt(message.from_user.first_name)},
        {"role": "user", "content": prompt}
    ]
    
    await bot.send_chat_action(message.chat.id, action="typing")
    answer = await query_groq(messages)
    await send_safe_message(message, answer)

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text in ["🗑 Новая тема", "❤️ Поблагодарить создателя", "📱 Другие сервисы", "📢 Поделиться"]: return
    add_user_to_db(message.from_user.id)
    uid = message.chat.id
    
    if uid not in user_history: 
        user_history[uid] = [{"role": "system", "content": get_system_prompt(message.from_user.first_name)}]
    
    user_history[uid].append({"role": "user", "content": message.text})
    if len(user_history[uid]) > 12: 
        user_history[uid] = [user_history[uid][0]] + user_history[uid][-10:]

    await bot.send_chat_action(uid, action="typing")
    answer = await query_groq(user_history[uid])
    
    user_history[uid].append({"role": "assistant", "content": answer})
    await send_safe_message(message, answer)

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await message.answer("👀 Вижу картинку. Пришли лучше файл с текстом (Word, PDF).")

async def main():
    logger.info("🚀 BOT STARTED")
    if not os.path.exists(DB_FILE): open(DB_FILE, "w").close()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
