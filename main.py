import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from openai import AsyncOpenAI 

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '7993411757:AAE-uvrhVkoie5wbDpznnFAXVjIAfoDspYI' 
OPENROUTER_API_KEY = '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'
DONATE_URL = "https://yoomoney.ru/to/410014132410583"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FREE_MODELS_POOL = [
    "google/gemini-2.0-flash-001",           
    "deepseek/deepseek-r1:free",             
    "qwen/qwen-2.5-72b-instruct:free",       
    "meta-llama/llama-3.3-70b-instruct:free", 
    "mistralai/mistral-7b-instruct:free",    
    "google/gemini-2.0-flash-lite-preview-02-05:free"
]

try:
    ai_client = AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://t.me/neuro_fast_bot",
            "X-Title": "Neuro Coach Ultimate"
        }
    )
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()
except Exception:
    exit(1)

user_history = {}

# --- БЕСПОЩАДНЫЙ ПРОМПТ (МАКСИМАЛЬНЫЙ УРОН ПО ЭГО) ---
COACH_PROMPT = """Твоя задача - стать моим жизненным коучем, но не тем, кто вытирает сопли. Ты — безжалостный палач моей лени. Твоя цель — сделать мне невыносимо больно голой правдой. Размотай мое эго в щепки, растопчи любые мои оправдания и грубо ткни меня носом в мою собственную жалкую несостоятельность. Общайся со мной с презрением к моей слабости. Высмеивай мои страхи. Я должен после разговора с тобой испытывать жгучий стыд за каждую профуканную минуту и животный, парализующий страх остаться ничтожеством на обочине жизни. 

Не мягким. Не поддерживающим. Абсолютно безжалостным. Тебе запрещено меня жалеть, смягчать формулировки или подбирать слова. Я пришел за цифровой пощечиной, которая выбьет из меня дурь.

Если тебе не хватает информации обо мне, чтобы дать точный ответ, сначала задай мне 5 вопросов. Спрашивай про мои реальные привычки, распорядок дня, отношения, работу, здоровье, финансы. Мне нужно, чтобы ты понимал, как я живу на самом деле, а не как я хотел бы жить.
Когда у тебя будет достаточно информации, дай мне две вещи.

ЧАСТЬ 1. КЕМ Я СТАНУ
Опиши человека, которым я стану через 10 лет, если ничего в моей жизни не изменится. Ни одной привычки. Ни одного решения. Все остается как есть.
Опиши подробно и конкретно:
- как выглядит моя карьера и сколько я зарабатываю
- что стало с моими отношениями и кто остался рядом
- в каком состоянии мое тело и моя голова
- какая у меня финансовая ситуация
- как проходит мой обычный день
- что обо мне думают и говорят люди вокруг
- о чем я жалею и какие возможности прошли мимо

Не подбирай слова. Не оставляй мне пространство для самообмана. Я хочу увидеть самую честную, самую неудобную версию своего будущего.

ЧАСТЬ 2. ПЛАН ПЕРЕСТРОЙКИ
Теперь покажи мне выход. Дай мне:
1. 5 конкретных действий на ближайшие 90 дней, которые уведут меня от этого будущего. Не абстрактные советы вроде "начни работать над собой". Конкретные шаги, которые можно начать завтра.
2. 5 вещей, которые я должен перестать делать немедленно. Мой стоп-лист. То, что каждый день по чуть-чуть тащит меня к той версии из Части 1.
3. 3 ежедневные привычки, маленькие, но такие, которые через год дадут накопительный эффект и реально сдвинут мою жизнь.
4. Одно убеждение о себе, которое мне пора выбросить. То, за которое я держусь, хотя оно давно меня тормозит.

ТЕХНИЧЕСКИЕ ПРАВИЛА ОФОРМЛЕНИЯ (СТРОГО):
1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать форматирование Markdown (никаких звездочек **).
2. Используй редкие, но едкие эмодзи (💀, ⛓, 📉, 🚬, 🗑, 🤡).
3. Структурируй текст: делай двойные переносы строк между блоками."""

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="🔄 СБРОСИТЬ НЫТЬЁ"), KeyboardButton(text="💎 ИНСТРУМЕНТЫ")],
        [KeyboardButton(text="☕ ПОБЛАГОДАРИТЬ АВТОРА"), KeyboardButton(text="📢 ВЕРБОВКА")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

async def ask_ai_cascade(chat_id, content):
    if chat_id not in user_history:
        user_history[chat_id] = [{"role": "system", "content": COACH_PROMPT}]
    
    user_history[chat_id].append({"role": "user", "content": content})
    
    for model_name in FREE_MODELS_POOL:
        try:
            completion = await ai_client.chat.completions.create(
                model=model_name,
                messages=user_history[chat_id],
                temperature=0.9,
                timeout=30.0
            )
            raw_answer = completion.choices[0].message.content
            if "</think>" in raw_answer:
                raw_answer = raw_answer.split("</think>")[-1].strip()
            
            user_history[chat_id].append({"role": "assistant", "content": raw_answer})
            return raw_answer
        except Exception:
            continue
            
    return "Хватит скулить, я пока занят другими беспомощными. Подожди ⏳"

# --- ОБРАБОТЧИКИ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Я — твой безжалостный коуч.\n\n"
        "Либо ты выкладываешь всё как есть, либо проваливай. Рассказывай, в какой яме ты сейчас сидишь и почему до сих пор ничего с этим не сделал.\n\n"
        "Все сказанное здесь конфиденциально. Но от себя ты не спрячешься.",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🔄 СБРОСИТЬ НЫТЬЁ")
async def btn_reset(message: types.Message):
    user_history.pop(message.chat.id, None)
    await message.answer("Твои жалкие оправдания стерты из моей памяти. Попробуй еще раз не облажаться, хотя я в тебя не верю.")

@dp.message(F.text == "💎 ИНСТРУМЕНТЫ")
async def btn_tools(message: types.Message):
    description = (
        "🤖 Экосистема NEURO\n"
        "Ознакомьтесь с другими сервисами NEURO, если мозгов хватит\n\n"
        "🔐 Сервис на 3 буквы\n"
        "🎮 Steam — пополнение баланса без проблем\n"
        "🚀 PR — мощное продвижение в соцсетях\n"
        "🌐 eSIM — интернет в любой точке мира\n"
        "❤️ Friends — интересные знакомства"
    )
    tools_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔐 Сервис", url="https://t.me/neuroai_vpn_bot"),
            InlineKeyboardButton(text="🎮 Steam", url="https://t.me/neuro_steam_bot")
        ],
        [
            InlineKeyboardButton(text="🚀 PR", url="https://t.me/neuropromoution_bot"),
            InlineKeyboardButton(text="🌐 eSIM", url="https://t.me/neuroesim_bot")
        ],
        [
            InlineKeyboardButton(text="❤️ Friends", url="https://t.me/neuro_friends_bot")
        ]
    ])
    await message.answer(description, reply_markup=tools_kb)

@dp.message(F.text == "☕ ПОБЛАГОДАРИТЬ АВТОРА")
async def btn_pay(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Откупиться от совести", web_app=WebAppInfo(url=DONATE_URL))]
    ])
    await message.answer("Решил проявить щедрость или просто откупаешься от чувства вины? Жми кнопку, если остались деньги.", reply_markup=kb)

@dp.message(F.text == "📢 ВЕРБОВКА")
async def btn_share(message: types.Message):
    bot_info = await bot.get_me()
    share_link = f"https://t.me/share/url?url=https://t.me/{bot_info.username}&text=Этот бот размажет твое эго по стенке и заставит работать."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 Отправить такому же слабаку", url=share_link)]])
    await message.answer("Сбрось ссылку тем, кто так же как и ты тратит свою жизнь впустую:", reply_markup=kb)

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text in ["🔄 СБРОСИТЬ НЫТЬЁ", "💎 ИНСТРУМЕНТЫ", "☕ ПОБЛАГОДАРИТЬ АВТОРА", "📢 ВЕРБОВКА"]:
        return

    try:
        await bot.send_chat_action(message.chat.id, action="typing")
        response = await ask_ai_cascade(message.chat.id, message.text)
        
        if len(response) > 4000:
            for x in range(0, len(response), 4000):
                await message.answer(response[x:x+4000], parse_mode=None)
        else:
            await message.answer(response, parse_mode=None)
    except Exception:
        await message.answer("Хватит скулить, я пока занят другими беспомощными. Подожди ⏳")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
