import os
import ast
import operator
import asyncio
import random
import json
import subprocess
import urllib.parse
import urllib.request
import speech_recognition as sr
import random
import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    Bot,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from google import genai
from google.genai import types
from mistralai.client import Mistral


# =========================================================
# 🔑 API KEYLAR
# =========================================================

TELEGRAM_TOKEN = "..."

GEMINI_API_KEY = "..."

LOG_BOT_TOKEN = "..."

MISTRAL_API_KEY = "..."

# 👇 BU YERGA O'Z TELEGRAM ID'ingNI YOZ
ADMIN_ID = ...


# =========================================================
# 📁 PAPKA
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_FILE = os.path.join(
    BASE_DIR,
    "bot_data.json"
)


# =========================================================
# 🤖 AI CLIENT
# =========================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)

mistral_client = Mistral(
    api_key=MISTRAL_API_KEY
)


# =========================================================
# 💾 DATA
# =========================================================

def load_data():

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if "users" not in data:
                data["users"] = {}

            return data

    except Exception:

        return {
            "users": {}
        }


DATA = load_data()


def save_data():

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                DATA,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print(
            "SAVE ERROR:",
            e
        )


# =========================================================
# 👤 USER
# =========================================================

def ensure_user(user):

    uid = str(user.id)

    if uid not in DATA["users"]:

        DATA["users"][uid] = {

            "name":
                user.first_name or "User",

            "username":
                user.username or "",

            "xp": 0,
            "coins": 0,

            "text": 0,
            "voice": 0,
            "image": 0,

            "games": 0,
            "wins": 0,

            "jokes": 0,

            "daily": 0,
            "streak": 0,

            "last_daily": "",

            "inventory": [],

            "achievements": [],

            "work_count": 0,

        }

    u = DATA["users"][uid]

    # Eski bot_data.json uchun
    defaults = {

        "name": user.first_name or "User",
        "username": user.username or "",

        "xp": 0,
        "coins": 0,

        "text": 0,
        "voice": 0,
        "image": 0,

        "games": 0,
        "wins": 0,

        "jokes": 0,

        "daily": 0,
        "streak": 0,
        "last_daily": "",

        "inventory": [],
        "achievements": [],

        "work_count": 0,
    }

    for key, value in defaults.items():

        if key not in u:

            u[key] = value

    u["name"] = (
        user.first_name
        or u.get("name", "User")
    )

    u["username"] = (
        user.username
        or u.get("username", "")
    )

    return u


def get_level(xp):

    return (
        xp // 100
    ) + 1


def add_xp(user, amount):

    u = ensure_user(user)

    old_level = get_level(
        u["xp"]
    )

    u["xp"] += amount

    new_level = get_level(
        u["xp"]
    )

    save_data()

    if new_level > old_level:

        return new_level

    return None


def add_coins(user, amount):

    u = ensure_user(user)

    u["coins"] += amount

    save_data()


# =========================================================
# 🏆 ACHIEVEMENTS
# =========================================================

def check_achievements(user):

    u = ensure_user(user)

    achievements = []

    if u["games"] >= 1:
        achievements.append("🎮 Gamer")

    if u["games"] >= 10:
        achievements.append("🎮 Gamer Pro")

    if u["wins"] >= 5:
        achievements.append("🏆 Winner")

    if u["wins"] >= 25:
        achievements.append("🏆 Champion")

    if u["xp"] >= 100:
        achievements.append("⭐ Level 2")

    if u["xp"] >= 500:
        achievements.append("⭐ Level 6")

    if u["coins"] >= 100:
        achievements.append("🪙 Rich")

    if u["daily"] >= 7:
        achievements.append("🔥 Daily Master")

    if u["streak"] >= 7:
        achievements.append("🔥 Streak Master")

    if u["jokes"] >= 50:
        achievements.append("😂 Comedian")

    if u["text"] >= 100:
        achievements.append("💬 Chatterbox")

    if u["voice"] >= 20:
        achievements.append("🎤 Voice Master")

    if u["image"] >= 20:
        achievements.append("🖼️ Vision Master")

    new_achievements = []

    for achievement in achievements:

        if achievement not in u["achievements"]:

            u["achievements"].append(
                achievement
            )

            new_achievements.append(
                achievement
            )

    save_data()

    return new_achievements


# =========================================================
# 🤖 AI
# =========================================================

async def ask_ai(prompt):

    # Gemini
    try:

        response = await asyncio.to_thread(

            client.interactions.create,

            model="gemini-3.6-flash",

            input=prompt

        )

        if response.output_text:

            return response.output_text

    except Exception as e:

        print(
            "GEMINI ERROR:",
            e
        )


    # Mistral fallback
    try:

        response = await asyncio.to_thread(

            mistral_client.chat.complete,

            model="mistral-small-latest",

            messages=[

                {
                    "role": "user",
                    "content": prompt
                }

            ]

        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if isinstance(
            content,
            str
        ):

            return content

        return str(content)

    except Exception as e:

        print(
            "MISTRAL ERROR:",
            e
        )

    return None


# =========================================================
# 👑 ADMIN LOG
# =========================================================

async def notify_new_user(update):

    if not LOG_BOT_TOKEN or ADMIN_ID == 0:
        return

    user = update.effective_user

    username = (

        f"@{user.username}"

        if user.username

        else "username yo‘q"

    )

    message = (

        "🔔 BOTGA USER KIRDI!\n\n"

        f"👤 Ism: "
        f"{user.first_name or 'Nomaʼlum'}\n"

        f"🔗 Username: "
        f"{username}\n"

        f"🆔 User ID: "
        f"{user.id}"

    )

    try:

        async with Bot(
            token=LOG_BOT_TOKEN
        ) as log_bot:

            await log_bot.send_message(

                chat_id=ADMIN_ID,

                text=message

            )

    except Exception as e:

        print(
            "LOG ERROR:",
            e
        )


# =========================================================
# 🕐 TOSHKENT
# =========================================================

def get_tashkent_time():

    return datetime.now(
        ZoneInfo(
            "Asia/Tashkent"
        )
    )


# =========================================================
# 🌤️ WEATHER
# =========================================================

CITIES = [

    "Tashkent",
    "Samarkand",
    "Bukhara",
    "Andijan",
    "Namangan",
    "Fergana",
    "Nukus",
    "Khiva",
    "Jizzakh",
    "Qarshi",
    "Termez",
    "Urgench",

    "Moscow",
    "London",
    "Dubai",
    "Istanbul",
    "Seoul",
    "Tokyo",
    "Beijing",

]


def get_city_from_text(text):

    lower = text.lower()

    for city in CITIES:

        if city.lower() in lower:

            return city

    return "Tashkent"


def geocode_city(city):

    try:

        url = (

            "https://geocoding-api.open-meteo.com/v1/search?"

            +

            urllib.parse.urlencode({

                "name": city,

                "count": 1,

                "language": "en",

                "format": "json"

            })

        )

        with urllib.request.urlopen(

            url,

            timeout=10

        ) as response:

            data = json.load(
                response
            )

        if not data.get("results"):

            return None

        result = data["results"][0]

        return (

            result["latitude"],

            result["longitude"],

            result.get(
                "name",
                city
            )

        )

    except Exception as e:

        print(
            "GEOCODE ERROR:",
            e
        )

        return None


def weather_description(code):

    return {

        0: "☀️ Ochiq osmon",

        1: "🌤️ Asosan ochiq",

        2: "⛅ Qisman bulutli",

        3: "☁️ Bulutli",

        45: "🌫️ Tuman",

        48: "🌫️ Qirovli tuman",

        51: "🌦️ Yengil yomg‘ir",

        53: "🌦️ O‘rtacha yomg‘ir",

        55: "🌧️ Kuchli yomg‘ir",

        61: "🌧️ Yomg‘ir",

        63: "🌧️ Yomg‘ir",

        65: "🌧️ Kuchli yomg‘ir",

        71: "🌨️ Yengil qor",

        73: "🌨️ Qor",

        75: "❄️ Kuchli qor",

        80: "🌦️ Yomg‘ir",

        81: "🌧️ Kuchli yom‘ir",

        82: "🌧️ Juda kuchli yomg‘ir",

        95: "⛈️ Momaqaldiroq",

        96: "⛈️ Do‘l bilan momaqaldiroq",

        99: "⛈️ Kuchli do‘l",

    }.get(
        code,
        "🌥️ Nomaʼlum"
    )


def get_weather(city):

    location = geocode_city(
        city
    )

    if not location:

        return None

    lat, lon, name = location

    try:

        url = (

            "https://api.open-meteo.com/v1/forecast?"

            +

            urllib.parse.urlencode({

                "latitude": lat,

                "longitude": lon,

                "current":
                    "temperature_2m,"
                    "apparent_temperature,"
                    "weather_code,"
                    "wind_speed_10m",

                "timezone": "auto"

            })

        )

        with urllib.request.urlopen(

            url,

            timeout=10

        ) as response:

            data = json.load(
                response
            )

        current = data["current"]

        return (

            f"🌤️ {name}\n\n"

            f"🌡️ Harorat: "
            f"{current['temperature_2m']}°C\n"

            f"🤏 His qilinishi: "
            f"{current['apparent_temperature']}°C\n"

            f"{weather_description(current['weather_code'])}\n"

            f"💨 Shamol: "
            f"{current['wind_speed_10m']} km/h"

        )

    except Exception as e:

        print(
            "WEATHER ERROR:",
            e
        )

        return None


# =========================================================
# 🔎 QUESTION CHECKERS
# =========================================================

def is_date_question(text):

    text = text.lower()

    return any(

        x in text

        for x in [

            "bugun sana",
            "bugungi sana",
            "qaysi sana",
            "sana nima"

        ]

    )


def is_time_question(text):

    text = text.lower()

    return any(

        x in text

        for x in [

            "soat nechi",
            "soat nechchi",
            "hozir soat",
            "vaqt nechi"

        ]

    )


def is_weather_question(text):

    text = text.lower()

    return any(

        x in text

        for x in [

            "ob havo",
            "ob-havo",
            "obhavo",
            "weather",
            "harorat"

        ]

    )


# =========================================================
# 😂 1000 HAZIL
# =========================================================

def generate_jokes():

    things = [

        "telefon",
        "kompyuter",
        "Wi-Fi",
        "Minecraft",
        "Roblox",
        "printer",
        "sichqoncha",
        "klaviatura",
        "internet",
        "charger",
        "quloqchin",
        "Telegram",
        "YouTube",
        "noutbuk",
        "kalkulyator",
        "muzlatkich",
        "televizor",
        "soat",
        "maktab",
        "uy vazifasi"

    ]

    reasons = [

        "chunki u ham dam olmoqchi edi",
        "chunki batareyasi 1% edi",
        "chunki Wi-Fi uni tashlab ketdi",
        "chunki u update kutayotgan edi",
        "chunki hech kim uni tushunmadi",
        "chunki internet sekin edi",
        "chunki u bugun ishlashni xohlamadi",
        "chunki parolini unutdi",
        "chunki signal yo‘q edi",
        "chunki u Minecraft o‘ynayotgan edi",
        "chunki Windows yana yangilanayotgan edi",
        "chunki sichqoncha charchadi",
        "chunki klaviatura taʼtilga chiqdi",
        "chunki server javob bermadi",
        "chunki u loadingda qolib ketdi"

    ]

    jokes = [

        "😂 O‘qituvchi: Uy vazifang qani? O‘quvchi: Kompyuterda. O‘qituvchi: Unda och. O‘quvchi: Kompyuter ochilmayapti 😂",

        "🤣 Wi-Fi o‘chib qolsa, uyda hamma birdan bir-birini taniy boshlaydi.",

        "😂 Noutbuk: Men qizimayapman. Ventilyator: Men esa seni umuman tanimayman.",

        "🤣 Minecraftdagi eng kuchli mob — lag.",

        "😂 Telefon 1% bo‘lganda odam undan million dollarlik texnika kabi ehtiyot bo‘ladi."

    ]

    used = set(jokes)

    for thing in things:

        for reason in reasons:

            joke = (

                f"😂 Nega {thing} "
                f"bugun ishlamadi? "
                f"{reason.capitalize()}."

            )

            if joke not in used:

                jokes.append(joke)

                used.add(joke)

    return jokes[:1000]


JOKES = generate_jokes()


async def joke_command(update, context):

    user = ensure_user(
        update.effective_user
    )

    user["jokes"] += 1

    add_xp(
        update.effective_user,
        3
    )

    check_achievements(
        update.effective_user
    )

    await update.message.reply_text(

        random.choice(JOKES)

    )


# =========================================================
# 🎮 GAMES
# =========================================================

async def games_command(update, context):

    await update.message.reply_text(

        "🎮 O‘YINLAR\n\n"

        "/game — 🔢 Son topish\n"
        "/dicegame — 🎲 Kubik jangi\n"
        "/rps — ✊ Tosh-qaychi-qog‘oz\n"
        "/mathgame — 🧮 Matematik o‘yin\n"
        "/scramble — 🔤 So‘z topish\n"
        "/quiz — 🧠 Quiz\n"
        "/dice — 🎲 Kubik\n"
        "/coin — 🪙 Tanga"

    )


# =========================================================
# 🔢 NUMBER GAME
# =========================================================

async def game_command(update, context):

    user = ensure_user(
        update.effective_user
    )

    user["games"] += 1

    context.user_data["number_game"] = random.randint(
        1,
        100
    )

    context.user_data["game_attempts"] = 0

    save_data()

    await update.message.reply_text(

        "🎮 SON TOPISH\n\n"

        "Men 1 dan 100 gacha "
        "son o‘yladim.\n\n"

        "Topishga harakat qil! 😈"

    )


async def check_number_game(
    update,
    text,
    context
):

    if "number_game" not in context.user_data:

        return False

    try:

        guess = int(text)

    except ValueError:

        await update.message.reply_text(
            "🔢 Faqat son yoz!"
        )

        return True

    target = context.user_data[
        "number_game"
    ]

    context.user_data[
        "game_attempts"
    ] += 1

    attempts = context.user_data[
        "game_attempts"
    ]

    if guess < target:

        await update.message.reply_text(

            f"⬆️ Kattaroq!\n"
            f"🎯 Urinish: {attempts}"

        )

    elif guess > target:

        await update.message.reply_text(

            f"⬇️ Kichikroq!\n"
            f"🎯 Urinish: {attempts}"

        )

    else:

        user = ensure_user(
            update.effective_user
        )

        user["wins"] += 1

        user["coins"] += 10

        level_up = add_xp(
            update.effective_user,
            25
        )

        save_data()

        text = (

            f"🎉 TOPDING!\n\n"

            f"🔢 Son: {target}\n"

            f"🎯 Urinish: {attempts}\n\n"

            f"🏆 +25 XP\n"
            f"🪙 +10 coin"

        )

        if level_up:

            text += (
                f"\n\n🎉 LEVEL UP!"
                f"\n⭐ Level {level_up}"
            )

        await update.message.reply_text(text)

        context.user_data.pop(
            "number_game",
            None
        )

        context.user_data.pop(
            "game_attempts",
            None
        )

        check_achievements(
            update.effective_user
        )

    return True


# =========================================================
# 🎲 DICE
# =========================================================

async def dice_command(update, context):

    number = random.randint(
        1,
        6
    )

    await update.message.reply_text(

        f"🎲 Kubik: {number}"

    )


async def dicegame_command(update, context):

    user_number = random.randint(
        1,
        6
    )

    bot_number = random.randint(
        1,
        6
    )

    user = ensure_user(
        update.effective_user
    )

    user["games"] += 1

    if user_number > bot_number:

        user["wins"] += 1

        user["coins"] += 5

        add_xp(
            update.effective_user,
            10
        )

        result = (
            "🏆 SEN YUTDING!\n"
            "🪙 +5 coin"
        )

    elif user_number < bot_number:

        result = "🤖 Bot yutdi!"

    else:

        result = "🤝 Durrang!"

    save_data()

    await update.message.reply_text(

        "🎲 DICE GAME\n\n"

        f"👤 Sen: {user_number}\n"
        f"🤖 Bot: {bot_number}\n\n"

        f"{result}"

    )


# =========================================================
# 🪙 COIN
# =========================================================

async def coin_command(update, context):

    result = random.choice(

        [
            "🪙 Gerb",
            "🪙 Raqam"
        ]

    )

    await update.message.reply_text(

        f"🪙 Natija: {result}"

    )


# =========================================================
# ✊ RPS
# =========================================================

async def rps_command(update, context):

    choices = [

        "✊ Tosh",
        "✋ Qog‘oz",
        "✌️ Qaychi"

    ]

    user_choice = random.choice(
        choices
    )

    bot_choice = random.choice(
        choices
    )

    wins = {

        (
            "✊ Tosh",
            "✌️ Qaychi"
        ),

        (
            "✋ Qog‘oz",
            "✊ Tosh"
        ),

        (
            "✌️ Qaychi",
            "✋ Qog‘oz"
        )

    }

    user = ensure_user(
        update.effective_user
    )

    user["games"] += 1

    if user_choice == bot_choice:

        result = "🤝 Durrang!"

    elif (
        user_choice,
        bot_choice
    ) in wins:

        user["wins"] += 1

        user["coins"] += 5

        add_xp(
            update.effective_user,
            10
        )

        result = (
            "🏆 SEN YUTDING!\n"
            "🪙 +5 coin"
        )

    else:

        result = "🤖 Bot yutdi!"

    save_data()

    await update.message.reply_text(

        f"👤 Sen: {user_choice}\n"
        f"🤖 Bot: {bot_choice}\n\n"
        f"{result}"

    )


# =========================================================
# 🧮 MATH GAME
# =========================================================

async def mathgame_command(update, context):

    a = random.randint(
        2,
        30
    )

    b = random.randint(
        2,
        20
    )

    op = random.choice(
        [
            "+",
            "-",
            "*"
        ]
    )

    if op == "+":

        answer = a + b

    elif op == "-":

        answer = a - b

    else:

        answer = a * b

    context.user_data[
        "math_answer"
    ] = answer

    await update.message.reply_text(

        f"🧮 TEZ MISOL!\n\n"
        f"❓ {a} {op} {b} = ?"

    )


async def check_mathgame(
    update,
    text,
    context
):

    if "math_answer" not in context.user_data:

        return False

    try:

        answer = int(text)

    except ValueError:

        return True

    correct = context.user_data.pop(
        "math_answer"
    )

    if answer == correct:

        user = ensure_user(
            update.effective_user
        )

        user["wins"] += 1

        user["coins"] += 5

        add_xp(
            update.effective_user,
            10
        )

        save_data()

        await update.message.reply_text(

            "🎉 TO‘G‘RI!\n\n"
            "🏆 +10 XP\n"
            "🪙 +5 coin"

        )

    else:

        await update.message.reply_text(

            f"❌ Noto‘g‘ri.\n"
            f"✅ Javob: {correct}"

        )

    return True


# =========================================================
# 🔤 SCRAMBLE
# =========================================================

WORDS = [

    "minecraft",
    "telegram",
    "kompyuter",
    "internet",
    "python",
    "roblox",
    "telefon",
    "klaviatura",
    "monitor",
    "keyboard",
    "server",
    "windows",
    "android",
    "youtube",
    "programming",
    "javascript",
    "telegram",
    "gaming"

]


async def scramble_command(update, context):

    word = random.choice(
        WORDS
    )

    letters = list(word)

    random.shuffle(
        letters
    )

    scrambled = "".join(
        letters
    )

    context.user_data[
        "scramble_answer"
    ] = word

    await update.message.reply_text(

        "🔤 SO‘ZNI TOP!\n\n"

        f"🧩 {scrambled}\n\n"

        "Javobni yoz 👇"

    )


async def check_scramble(
    update,
    text,
    context
):

    if "scramble_answer" not in context.user_data:

        return False

    answer = context.user_data.pop(
        "scramble_answer"
    )

    if text.lower().strip() == answer:

        user = ensure_user(
            update.effective_user
        )

        user["wins"] += 1

        user["coins"] += 5

        add_xp(
            update.effective_user,
            10
        )

        save_data()

        await update.message.reply_text(

            "🎉 TO‘G‘RI!\n\n"
            "🏆 +10 XP\n"
            "🪙 +5 coin"

        )

    else:

        await update.message.reply_text(

            f"❌ Noto‘g‘ri.\n"
            f"✅ Javob: {answer}"

        )

    return True


# =========================================================
# 🧠 QUIZ
# =========================================================

QUIZES = [

    ("2^10 nechaga teng?", ["1024"]),
    ("10! nechaga teng?", ["3628800"]),
    ("144 ning kvadrat ildizi nechaga teng?", ["12"]),
    ("17 × 19 nechaga teng?", ["323"]),
    ("625 ning kvadrat ildizi nechaga teng?", ["25"]),
    ("3^5 nechaga teng?", ["243"]),
    ("999 + 999 nechaga teng?", ["1998"]),
    ("15% ning 200 ga teng qiymati nechaga teng?", ["30"]),
    ("Agar 2x + 7 = 31 bo‘lsa, x nechaga teng?", ["12"]),
    ("7² + 24² nechaga teng?", ["625"]),
    ("1 dan 100 gacha nechta tub son bor?", ["25"]),
    ("2^15 nechaga teng?", ["32768"]),
    ("1000 ning 3/4 qismi nechaga teng?", ["750"]),
    ("48 × 25 nechaga teng?", ["1200"]),
    ("9999 - 8888 nechaga teng?", ["1111"]),
    ("9 × 9 × 9 nechaga teng?", ["729"]),
    ("81 ning kvadrat ildizi nechaga teng?", ["9"]),
    ("5! nechaga teng?", ["120"]),
    ("1/2 + 1/4 nechaga teng?", ["3/4"]),
    ("0.25 × 400 nechaga teng?", ["100"]),

    ("3, 6, 12, 24, 48, ? keyingi son?", ["96"]),
    ("2, 6, 12, 20, 30, ? keyingi son?", ["42"]),
    ("1, 4, 9, 16, 25, ? keyingi son?", ["36"]),
    ("5, 10, 20, 40, ? keyingi son?", ["80"]),
    ("100, 90, 81, 73, ? keyingi son?", ["66"]),
    ("1, 1, 2, 3, 5, 8, ? keyingi son?", ["13"]),
    ("2, 3, 5, 8, 13, ? keyingi son?", ["21"]),
    ("10, 20, 40, 80, ? keyingi son?", ["160"]),
    ("64, 32, 16, 8, ? keyingi son?", ["4"]),
    ("7, 14, 28, 56, ? keyingi son?", ["112"]),
    ("Bir haftada nechta kun bor?", ["7"]),
    ("2 ta ota va 2 ta o‘g‘il 3 ta olma oldi. Har biri bittadan oldi. Qanday?", ["3 kishi"]),
    ("5 ta shamdan 2 tasi o‘chirildi. Oxirida nechta sham qoladi?", ["2"]),
    ("Soat 12:00 da 12 ta uradi. 6:00 da nechta uradi?", ["6"]),
    ("Bir sonning yarmi 25 bo‘lsa, son nechaga teng?", ["50"]),

    ("1 byte nechta bitdan iborat?", ["8"]),
    ("IPv4 manzilida nechta bit bor?", ["32"]),
    ("IPv6 manzilida nechta bit bor?", ["128"]),
    ("CPU nimani anglatadi?", ["central processing unit"]),
    ("GPU nimani anglatadi?", ["graphics processing unit"]),
    ("RAM nimani anglatadi?", ["random access memory"]),
    ("HTML nimani anglatadi?", ["hypertext markup language"]),
    ("CSS nimani anglatadi?", ["cascading style sheets"]),
    ("HTTP nimani anglatadi?", ["hypertext transfer protocol"]),
    ("HTTPS nimani anglatadi?", ["hypertext transfer protocol secure"]),
    ("Python'da ro‘yxatning oxirgi indeksiga qanday murojaat qilinadi?", ["-1"]),
    ("Python'da kommentariya belgisi nima?", ["#"]),
    ("Python'da 2 ** 3 nechaga teng?", ["8"]),
    ("Binary tizimda 10 soni decimalda nechaga teng?", ["2"]),
    ("Binary 1010 decimalda nechaga teng?", ["10"]),
    ("Hexadecimal FF decimalda nechaga teng?", ["255"]),
    ("1 KB odatda nechta byte?", ["1024"]),
    ("1 MB odatda nechta KB?", ["1024"]),
    ("1 GB odatda nechta MB?", ["1024"]),
    ("Git'da o‘zgarishlarni saqlash uchun qaysi buyruq ishlatiladi?", ["git commit"]),

    ("Dunyodagi eng katta okean qaysi?", ["tinch okeani"]),
    ("Dunyodagi eng katta qit’a qaysi?", ["osiyo"]),
    ("Yerning tabiiy yo‘ldoshi nima?", ["oy"]),
    ("O‘zbekiston poytaxti qaysi shahar?", ["toshkent"]),
    ("Eng katta davlat qaysi?", ["rossiya"]),
    ("Eng kichik davlat qaysi?", ["vatikan"]),
    ("Nil daryosi qaysi qit’ada?", ["afrika"]),
    ("Sahara cho‘li qaysi qit’ada?", ["afrika"]),
    ("Everest qaysi tog‘ tizmasida?", ["himolay"]),
    ("Yer nechta asosiy okeanga bo‘linadi?", ["5"]),
    ("O‘zbekiston nechta davlat bilan chegaradosh?", ["5"]),
    ("Amazonka daryosi qaysi qit’ada?", ["janubiy amerika"]),
    ("Dunyodagi eng katta orol qaysi?", ["grenlandiya"]),
    ("Yerning eng chuqur okean nuqtasi nima?", ["mariana botig‘i"]),
    ("Qaysi sayyora Quyoshga eng yaqin?", ["merkuri"]),

    ("Suvning kimyoviy formulasi nima?", ["h2o"]),
    ("Kislorodning kimyoviy belgisi nima?", ["o"]),
    ("Oltinning kimyoviy belgisi nima?", ["au"]),
    ("Temirning kimyoviy belgisi nima?", ["fe"]),
    ("Karbonat angidrid formulasi nima?", ["co2"]),
    ("Yer atmosferasida eng ko‘p qaysi gaz bor?", ["azot"]),
    ("Qon haydaydigan organ qaysi?", ["yurak"]),
    ("Fotosintezda o‘simliklar qaysi gazni yutadi?", ["karbonat angidrid"]),
    ("Elektr tok kuchining birligi nima?", ["amper"]),
    ("Kuchlanishning birligi nima?", ["volt"]),
    ("Qarshilikning birligi nima?", ["om"]),
    ("Quvvatning birligi nima?", ["vatt"]),
    ("Yorug‘lik vakuumda taxminan qanday tezlikda tarqaladi?", ["300000 km/s"]),
    ("Suv normal bosimda necha °C da qaynaydi?", ["100"]),
    ("Suv necha °C da muzlaydi?", ["0"]),

    ("Agar x + 1/x = 5 bo‘lsa, x² + 1/x² nechaga teng?", ["23"]),
    ("3 ta mashina 3 daqiqada 3 ta detal ishlab chiqarsa, 100 ta mashina 100 ta detalni necha daqiqada ishlab chiqaradi?", ["3"]),
    ("5 ishchi ishni 12 kunda tugatsa, 10 ishchi necha kunda tugatadi?", ["6"]),
    ("1 dan 100 gacha '9' raqami necha marta uchraydi?", ["20"]),
    ("2^20 nechaga teng?", ["1048576"]),
    ("13² nechaga teng?", ["169"]),
    ("19² nechaga teng?", ["361"]),
    ("23² nechaga teng?", ["529"]),
    ("29² nechaga teng?", ["841"]),
    ("31² nechaga teng?", ["961"]),
    ("Agar a=3, b=4 bo‘lsa, a²+b² nechaga teng?", ["25"]),
    ("Agar 20% = 50 bo‘lsa, 100% nechaga teng?", ["250"]),
    ("360° ning 1/8 qismi nechaga teng?", ["45"]),
    ("2, 4, 8, 16, 32, ? keyingi son?", ["64"]),
    ("1, 3, 6, 10, 15, ? keyingi son?", ["21"]),
    ("4, 9, 16, 25, 36, ? keyingi son?", ["49"]),
    ("1000 ning 10% i nechaga teng?", ["100"]),
    ("250 ning 20% i nechaga teng?", ["50"]),
    ("7 × 8 + 4 nechaga teng?", ["60"]),
    ("100 - 25 × 2 nechaga teng?", ["50"]),

]


def normalize_answer(text):

    return (
        text
        .lower()
        .strip()
        .replace("’", "'")
        .replace("`", "'")
    )


async def quiz_command(update, context):

    question, answers = random.choice(
        QUIZES
    )

    context.user_data[
        "quiz_answers"
    ] = answers

    await update.message.reply_text(

        "🧠 INSANE QUIZ 🔥\n\n"

        f"❓ {question}\n\n"

        "Javobni yoz 👇"

    )


async def check_quiz(
    update,
    text,
    context
):

    if "quiz_answers" not in context.user_data:

        return False

    answers = context.user_data.pop(
        "quiz_answers"
    )

    user_answer = normalize_answer(
        text
    )

    correct = False

    for answer in answers:

        if user_answer == normalize_answer(
            answer
        ):

            correct = True
            break

    if correct:

        user = ensure_user(
            update.effective_user
        )

        user["wins"] += 1

        user["coins"] += 5

        add_xp(
            update.effective_user,
            10
        )

        save_data()

        await update.message.reply_text(

            "🎉 TO‘G‘RI!\n\n"
            "🏆 +10 XP\n"
            "🪙 +5 coin"

        )

    else:

        await update.message.reply_text(

            "❌ Noto‘g‘ri.\n\n"
            f"✅ Javob: {answers[0]}"

        )

    check_achievements(
        update.effective_user
    )

    return True


# =========================================================
# 👤 PROFILE
# =========================================================

async def profile_command(update, context):

    user = ensure_user(
        update.effective_user
    )

    level = get_level(
        user["xp"]
    )

    await update.message.reply_text(

        f"👤 {user['name']}\n\n"

        f"⭐ Level: {level}\n"
        f"✨ XP: {user['xp']}\n"
        f"🪙 Coin: {user['coins']}\n\n"

        f"🎮 O‘yinlar: {user['games']}\n"
        f"🏆 G‘alabalar: {user['wins']}\n"

        f"💬 Text: {user['text']}\n"
        f"🎤 Voice: {user['voice']}\n"
        f"🖼️ Image: {user['image']}\n"

        f"😂 Hazillar: {user['jokes']}\n"
        f"🎁 Daily: {user['daily']}\n"
        f"🔥 Streak: {user['streak']}"

    )


# =========================================================
# 🥇 TOP
# =========================================================

async def top_command(update, context):

    users = list(
        DATA["users"].values()
    )

    users.sort(

        key=lambda x: x.get(
            "xp",
            0
        ),

        reverse=True

    )

    lines = [
        "🏆 TOP 10\n"
    ]

    for index, user in enumerate(
        users[:10],
        1
    ):

        lines.append(

            f"{index}. "
            f"{user.get('name', 'User')} — "
            f"⭐ Level "
            f"{get_level(user.get('xp', 0))} "
            f"({user.get('xp', 0)} XP)"

        )

    await update.message.reply_text(

        "\n".join(lines)

    )


# =========================================================
# 🎁 DAILY + STREAK
# =========================================================

async def daily_command(update, context):

    user = ensure_user(
        update.effective_user
    )

    today = get_tashkent_time().date()

    last = user.get(
        "last_daily",
        ""
    )

    if last == str(today):

        await update.message.reply_text(

            "⏳ Bugungi Daily rewardni "
            "olib bo‘lgansan.\n\n"

            f"🔥 Streak: {user['streak']} kun\n"

            "🌅 Ertaga yana kel!"

        )

        return

    yesterday = today - timedelta(
        days=1
    )

    if last == str(yesterday):

        user["streak"] += 1

    else:

        user["streak"] = 1

    coins = random.randint(
        20,
        50
    )

    xp = random.randint(
        10,
        25
    )

    user["coins"] += coins

    user["xp"] += xp

    user["daily"] += 1

    user["last_daily"] = str(today)

    save_data()

    await update.message.reply_text(

        "🎁 DAILY REWARD!\n\n"

        f"🪙 +{coins} coin\n"
        f"⭐ +{xp} XP\n"
        f"🔥 Streak: {user['streak']} kun\n\n"

        "🌅 Ertaga yana kel!"

    )

    check_achievements(
        update.effective_user
    )


# =========================================================
# 🪙 BALANCE
# =========================================================

async def balance_command(update, context):

    user = ensure_user(
        update.effective_user
    )

    await update.message.reply_text(

        f"🪙 Balansing: "
        f"{user['coins']} coin"

    )


# =========================================================
# 💼 WORK
# =========================================================

async def work_command(update, context):

    user = ensure_user(
        update.effective_user
    )

    reward = random.randint(
        10,
        40
    )

    jobs = [

        "💻 Dasturchi bo‘lib ishlading",

        "📦 Buyurtma yetkazding",

        "🛠️ Kompyuter tuzatding",

        "🎮 Gamer bo‘lib ishlading",

        "🧹 Uy ishlariga yordam berding",

        "📱 Telefon sozlading",

    ]

    job = random.choice(
        jobs
    )

    user["coins"] += reward

    user["work_count"] += 1

    add_xp(
        update.effective_user,
        5
    )

    save_data()

    await update.message.reply_text(

        f"{job}.\n\n"

        f"🪙 +{reward} coin\n"
        "⭐ +5 XP"

    )


# =========================================================
# 🛒 SHOP
# =========================================================

SHOP = {

    "apple":
        {
            "name": "🍎 Olma",
            "price": 20
        },

    "sword":
        {
            "name": "⚔️ Sword",
            "price": 100
        },

    "diamond":
        {
            "name": "💎 Diamond",
            "price": 250
        },

    "trophy":
        {
            "name": "🏆 Trophy",
            "price": 500
        },

}


async def shop_command(update, context):

    text = "🛒 SHOP\n\n"

    for item_id, item in SHOP.items():

        text += (

            f"/buy {item_id} "
            f"— {item['name']} "
            f"({item['price']} 🪙)\n"

        )

    await update.message.reply_text(
        text
    )


async def buy_command(update, context):

    if not context.args:

        await update.message.reply_text(

            "🛒 Masalan:\n"
            "/buy diamond"

        )

        return

    item_id = context.args[0].lower()

    if item_id not in SHOP:

        await update.message.reply_text(

            "❌ Bunday item yo‘q."

        )

        return

    item = SHOP[item_id]

    user = ensure_user(
        update.effective_user
    )

    if user["coins"] < item["price"]:

        await update.message.reply_text(

            "❌ Coin yetarli emas.\n\n"

            f"💰 Kerak: {item['price']}\n"
            f"🪙 Senda: {user['coins']}"

        )

        return

    user["coins"] -= item["price"]

    user["inventory"].append(
        item_id
    )

    save_data()

    await update.message.reply_text(

        "✅ SOTIB OLINDI!\n\n"

        f"{item['name']}\n"
        f"🪙 -{item['price']} coin"

    )


# =========================================================
# 🎒 INVENTORY
# =========================================================

async def inventory_command(update, context):

    user = ensure_user(
        update.effective_user
    )

    inventory = user["inventory"]

    if not inventory:

        await update.message.reply_text(

            "🎒 Inventory bo‘sh."

        )

        return

    counts = {}

    for item_id in inventory:

        counts[item_id] = (
            counts.get(item_id, 0) + 1
        )

    text = "🎒 INVENTORY\n\n"

    for item_id, count in counts.items():

        item = SHOP.get(
            item_id
        )

        if item:

            text += (

                f"{item['name']} × {count}\n"

            )

    await update.message.reply_text(
        text
    )


# =========================================================
# 🏆 ACHIEVEMENTS
# =========================================================

async def achievements_command(update, context):

    user = ensure_user(
        update.effective_user
    )

    check_achievements(
        update.effective_user
    )

    if not user["achievements"]:

        await update.message.reply_text(

            "🏆 Hali achievement yo‘q.\n\n"
            "Ko‘proq o‘yna, XP yig‘ va Daily ol!"

        )

        return

    text = "🏆 ACHIEVEMENTS\n\n"

    for achievement in user["achievements"]:

        text += f"✅ {achievement}\n"

    await update.message.reply_text(
        text
    )


# =========================================================
# 🧮 CALCULATOR
# =========================================================

OPERATORS = {

    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos

}


def safe_calc(node):

    if isinstance(
        node,
        ast.Constant
    ):

        if isinstance(
            node.value,
            (int, float)
        ):

            return node.value

        raise ValueError()

    if isinstance(
        node,
        ast.UnaryOp
    ):

        op = OPERATORS.get(
            type(node.op)
        )

        if not op:
            raise ValueError()

        return op(
            safe_calc(
                node.operand
            )
        )

    if isinstance(
        node,
        ast.BinOp
    ):

        op = OPERATORS.get(
            type(node.op)
        )

        if not op:
            raise ValueError()

        return op(

            safe_calc(
                node.left
            ),

            safe_calc(
                node.right
            )

        )

    raise ValueError()


async def calc_command(update, context):

    expression = " ".join(
        context.args
    )

    if not expression:

        await update.message.reply_text(

            "🧮 Masalan:\n"
            "/calc 25*4+10"

        )

        return

    try:

        tree = ast.parse(
            expression,
            mode="eval"
        )

        result = safe_calc(
            tree.body
        )

        await update.message.reply_text(

            f"🧮 Javob: {result}"

        )

    except Exception:

        await update.message.reply_text(

            "❌ Misol noto‘g‘ri."

        )


# =========================================================
# 🎯 RANDOM
# =========================================================

async def random_command(update, context):

    try:

        if len(context.args) >= 2:

            a = int(
                context.args[0]
            )

            b = int(
                context.args[1]
            )

        else:

            a = 1
            b = 100

        if a > b:

            a, b = b, a

        result = random.randint(
            a,
            b
        )

        await update.message.reply_text(

            f"🎯 Random: {result}"

        )

    except Exception:

        await update.message.reply_text(

            "❌ Masalan:\n"
            "/random 1 100"

        )


# =========================================================
# 💡 FACT
# =========================================================

FACTS = [

    "💡 Ahtapotlarning uchta yuragi bor.",

    "💡 Saturnning o‘rtacha zichligi suvnikidan kichik.",

    "💡 Yer yuzasining katta qismini okeanlar qoplaydi.",

    "💡 Venerada bir kun uning bir yilidan uzunroq.",

    "💡 Asalarilar bir-biri bilan raqs orqali aloqa qila oladi.",

    "💡 Yerdagi eng katta okean Tinch okeanidir.",

]


async def fact_command(update, context):

    await update.message.reply_text(

        random.choice(
            FACTS
        )

    )


# =========================================================
# 🪪 ID
# =========================================================

async def id_command(update, context):

    await update.message.reply_text(

        f"🪪 Telegram ID:\n"
        f"{update.effective_user.id}"

    )


# =========================================================
# ℹ️ ABOUT
# =========================================================

async def about_command(update, context):

    await update.message.reply_text(

        "🤖 AI + GAME BOT\n\n"

        "💬 AI Chat\n"
        "🎤 Voice AI\n"
        "🖼️ Image AI\n"
        "🎮 Mini Games\n"
        "🏆 XP / Level\n"
        "🪙 Coins\n"
        "🎁 Daily + Streak\n"
        "🛒 Shop\n"
        "🎒 Inventory\n"
        "🏆 Achievements\n"
        "😂 1000 Hazil\n"
        "🌤️ Weather\n"
        "🧮 Calculator"

    )


# =========================================================
# 📱 MENU
# =========================================================

def get_menu():

    return ReplyKeyboardMarkup(

        [

            ["🤖 AI", "🎮 O‘yinlar"],

            ["👤 Profil", "🏆 Reyting"],

            ["🎁 Daily", "🛒 Shop"],

            ["🎒 Inventory", "🏅 Achievements"],

            ["💼 Work", "🪙 Balance"],

            ["😂 Hazil", "🌤️ Ob-havo"],

            ["📚 Yordam"],

        ],

        resize_keyboard=True

    )


async def menu_command(update, context):

    await update.message.reply_text(

        "📱 ASOSIY MENYU",

        reply_markup=get_menu()

    )


# =========================================================
# 📚 HELP
# =========================================================

async def help_command(update, context):

    await update.message.reply_text(

        "📚 BOT KOMANDALARI\n\n"

        "🤖 AI\n"
        "Oddiy matn → AI\n"
        "🎤 Ovoz → AI\n"
        "🖼️ Rasm → AI\n"
        "/translate text\n\n"

        "🎮 O‘YINLAR\n"
        "/games\n"
        "/game\n"
        "/dicegame\n"
        "/rps\n"
        "/mathgame\n"
        "/scramble\n"
        "/quiz\n"
        "/dice\n"
        "/coin\n\n"

        "🏆 PROFIL\n"
        "/profile\n"
        "/top\n"
        "/achievements\n\n"

        "💰 ECONOMY\n"
        "/daily\n"
        "/balance\n"
        "/work\n"
        "/shop\n"
        "/buy item\n"
        "/inventory\n\n"

        "😂 FUN\n"
        "/joke\n"
        "/fact\n"
        "/random\n\n"

        "🧮 /calc\n"
        "🌤️ /weather\n"
        "🕐 /time\n"
        "📅 /date\n"
        "🪪 /id\n"
        "📱 /menu\n"
        "ℹ️ /about"

    )


# =========================================================
# 🌤️ WEATHER COMMAND
# =========================================================

async def weather_command(update, context):

    city = (

        " ".join(
            context.args
        )

        if context.args

        else "Tashkent"

    )

    result = await asyncio.to_thread(

        get_weather,
        city

    )

    if result:

        await update.message.reply_text(
            result
        )

    else:

        await update.message.reply_text(

            "❌ Bu shaharning "
            "ob-havosini topa olmadim."

        )


# =========================================================
# 🕐 TIME
# =========================================================

async def time_command(update, context):

    now = get_tashkent_time()

    await update.message.reply_text(

        "🕐 Toshkent vaqti:\n\n"

        f"{now.strftime('%H:%M:%S')}"

    )


# =========================================================
# 📅 DATE
# =========================================================

async def date_command(update, context):

    now = get_tashkent_time()

    await update.message.reply_text(

        "📅 Bugungi sana:\n\n"

        f"{now.strftime('%d.%m.%Y')}"

    )


# =========================================================
# 🌐 TRANSLATE
# =========================================================

async def translate_command(update, context):

    text = " ".join(
        context.args
    )

    if not text:

        await update.message.reply_text(

            "🌐 Masalan:\n"
            "/translate Hello world"

        )

        return

    waiting = await update.message.reply_text(

        "🌐 Tarjima qilinyapti..."

    )

    result = await ask_ai(

        f"""

Translate this text into Uzbek.

Only give the translation.

Text:
{text}

"""

    )

    if result:

        await waiting.edit_text(
            result
        )

    else:

        await waiting.edit_text(

            "❌ Tarjima qilishda xatolik."

        )


# =========================================================
# 🎁 START
# =========================================================

async def start(update, context):

    ensure_user(
        update.effective_user
    )

    save_data()

    await notify_new_user(
        update
    )

    await update.message.reply_text(

        "🤖 SALOM!\n\n"

        "Men AI + GAME botman 😎\n\n"

        "💬 Matn → AI\n"
        "🎤 Ovoz → AI\n"
        "🖼️ Rasm → AI\n\n"

        "🎮 /games\n"
        "👤 /profile\n"
        "🥇 /top\n"
        "🎁 /daily\n"
        "🪙 /balance\n"
        "🛒 /shop\n"
        "🏆 /achievements\n\n"

        "📱 /menu\n"
        "📚 /help\n\n"

        "👑 Creator: Sultan",

        reply_markup=get_menu()

    )


# =========================================================
# 💬 TEXT CHAT
# =========================================================

async def chat(update, context):

    user = update.effective_user

    text = update.message.text.strip()

    user_data = ensure_user(
        user
    )

    user_data["text"] += 1

    save_data()


    # MENU BUTTONLARI

    if text == "🎮 O‘yinlar":

        await games_command(
            update,
            context
        )

        return


    if text == "👤 Profil":

        await profile_command(
            update,
            context
        )

        return


    if text == "🏆 Reyting":

        await top_command(
            update,
            context
        )

        return


    if text == "🎁 Daily":

        await daily_command(
            update,
            context
        )

        return


    if text == "🛒 Shop":

        await shop_command(
            update,
            context
        )

        return


    if text == "🎒 Inventory":

        await inventory_command(
            update,
            context
        )

        return


    if text == "🏅 Achievements":

        await achievements_command(
            update,
            context
        )

        return


    if text == "💼 Work":

        await work_command(
            update,
            context
        )

        return


    if text == "🪙 Balance":

        await balance_command(
            update,
            context
        )

        return


    if text == "😂 Hazil":

        await joke_command(
            update,
            context
        )

        return


    if text == "🌤️ Ob-havo":

        await weather_command(
            update,
            context
        )

        return


    if text == "📚 Yordam":

        await help_command(
            update,
            context
        )

        return


    if text == "🤖 AI":

        await update.message.reply_text(

            "🤖 AI tayyor!\n\n"
            "Savolingni yoz 👇"

        )

        return


    # 🎮 O'YIN CHECK

    if await check_number_game(
        update,
        text,
        context
    ):

        return


    if await check_mathgame(
        update,
        text,
        context
    ):

        return


    if await check_scramble(
        update,
        text,
        context
    ):

        return


    if await check_quiz(
        update,
        text,
        context
    ):

        return


    # 📅 DATE

    if is_date_question(text):

        now = get_tashkent_time()

        await update.message.reply_text(

            f"📅 Bugungi sana: "
            f"{now.strftime('%d.%m.%Y')}"

        )

        return


    # 🕐 TIME

    if is_time_question(text):

        now = get_tashkent_time()

        await update.message.reply_text(

            f"🕐 Toshkent vaqti: "
            f"{now.strftime('%H:%M:%S')}"

        )

        return


    # 🌤️ WEATHER

    if is_weather_question(text):

        city = get_city_from_text(
            text
        )

        waiting = await update.message.reply_text(

            "🌤️ Ob-havo tekshirilmoqda..."

        )

        result = await asyncio.to_thread(

            get_weather,
            city

        )

        if result:

            await waiting.edit_text(
                result
            )

        else:

            await waiting.edit_text(

                "❌ Ob-havoni topa olmadim."

            )

        return


    # 🤖 AI

    waiting = await update.message.reply_text(

        "⏳ O‘ylayapman..."

    )

    prompt = f"""

Sen Telegramdagi AI yordamchisan.

Foydalanuvchi qaysi tilda yozsa,
o‘sha tilda javob ber.

O‘zbekcha bo‘lsa tabiiy o‘zbekcha yoz.

Jiddiy savollarga aniq va foydali javob ber.

Oddiy suhbatlarda yengil hazil qilishing mumkin.

Foydalanuvchi:

{text}

"""

    answer = await ask_ai(
        prompt
    )

    if answer:

        level_up = add_xp(
            user,
            5
        )

        new_achievements = check_achievements(
            user
        )

        if level_up:

            answer += (

                f"\n\n🎉 LEVEL UP!\n"
                f"⭐ Endi Level {level_up}!"

            )

        if new_achievements:

            answer += (

                "\n\n🏆 Yangi achievement:\n"
                + "\n".join(
                    new_achievements
                )

            )

        await waiting.edit_text(
            answer
        )

    else:

        await waiting.edit_text(

            "😕 AI xizmatida vaqtinchalik "
            "muammo bor."

        )


# =========================================================
# 🎤 VOICE
# =========================================================

async def voice(update, context):

    user = update.effective_user

    voice_file = os.path.join(
        BASE_DIR,
        "voice.ogg"
    )

    wav_file = os.path.join(
        BASE_DIR,
        "voice.wav"
    )

    try:

        waiting = await update.message.reply_text(

            "🎤 Ovoz qayta ishlanmoqda..."

        )

        tg_file = await (
            update.message
            .voice
            .get_file()
        )

        await tg_file.download_to_drive(
            voice_file
        )

        subprocess.run(

            [

                "ffmpeg",
                "-y",
                "-i",
                voice_file,
                "-ar",
                "16000",
                "-ac",
                "1",
                wav_file

            ],

            stdout=subprocess.DEVNULL,

            stderr=subprocess.DEVNULL

        )

        recognizer = sr.Recognizer()

        with sr.AudioFile(
            wav_file
        ) as source:

            audio = recognizer.record(
                source
            )

        text = recognizer.recognize_google(

            audio,

            language="uz-UZ"

        )

        user_data = ensure_user(
            user
        )

        user_data["voice"] += 1

        save_data()


        if is_date_question(text):

            now = get_tashkent_time()

            await waiting.edit_text(

                f"📅 "
                f"{now.strftime('%d.%m.%Y')}"

            )

            return


        if is_time_question(text):

            now = get_tashkent_time()

            await waiting.edit_text(

                f"🕐 "
                f"{now.strftime('%H:%M:%S')}"

            )

            return


        if is_weather_question(text):

            city = get_city_from_text(
                text
            )

            result = await asyncio.to_thread(

                get_weather,
                city

            )

            await waiting.edit_text(

                result
                or
                "❌ Ob-havo topilmadi."

            )

            return


        answer = await ask_ai(

            f"""

Foydalanuvchi ovozda shuni aytdi:

{text}

O‘zbek tilida tabiiy javob ber.

"""

        )

        if answer:

            add_xp(
                user,
                5
            )

            check_achievements(
                user
            )

            await waiting.edit_text(
                answer
            )

        else:

            await waiting.edit_text(

                "😕 AI xizmatida muammo bor."

            )


    except Exception as e:

        print(
            "VOICE ERROR:",
            e
        )

        await update.message.reply_text(

            "❌ Ovozni tushunishda "
            "xatolik yuz berdi."

        )

    finally:

        for file in [

            voice_file,
            wav_file

        ]:

            try:

                if os.path.exists(file):

                    os.remove(file)

            except Exception:

                pass


# =========================================================
# 🖼️ IMAGE
# =========================================================

async def image_handler(update, context):

    user = update.effective_user

    image_file = os.path.join(
        BASE_DIR,
        "user_image.jpg"
    )

    try:

        waiting = await update.message.reply_text(

            "🖼️ Rasm tahlil qilinmoqda..."

        )

        photo = update.message.photo[-1]

        tg_file = await photo.get_file()

        await tg_file.download_to_drive(
            image_file
        )

        with open(
            image_file,
            "rb"
        ) as f:

            image_bytes = f.read()

        response = await asyncio.to_thread(

            client.models.generate_content,

            model="gemini-3.6-flash",

            contents=[

                types.Part.from_bytes(

                    data=image_bytes,

                    mime_type="image/jpeg"

                ),

                "Bu rasmni o‘zbek tilida tushuntir."

            ]

        )

        user_data = ensure_user(
            user
        )

        user_data["image"] += 1

        add_xp(
            user,
            5
        )

        save_data()

        await waiting.edit_text(

            response.text
            or
            "😕 Rasmni tahlil qila olmadim."

        )

    except Exception as e:

        print(
            "IMAGE ERROR:",
            e
        )

        await update.message.reply_text(

            "❌ Rasmni tahlil qilishda "
            "xatolik."

        )

    finally:

        try:

            if os.path.exists(
                image_file
            ):

                os.remove(
                    image_file
                )

        except Exception:

            pass


# =========================================================
# 🚀 MAIN
# =========================================================

def main():

    app = (

        Application
        .builder()
        .token(
            TELEGRAM_TOKEN
        )
        .build()

    )


    # =========================
    # COMMANDS
    # =========================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    app.add_handler(
        CommandHandler(
            "menu",
            menu_command
        )
    )

    app.add_handler(
        CommandHandler(
            "games",
            games_command
        )
    )

    app.add_handler(
        CommandHandler(
            "weather",
            weather_command
        )
    )

    app.add_handler(
        CommandHandler(
            "time",
            time_command
        )
    )

    app.add_handler(
        CommandHandler(
            "date",
            date_command
        )
    )

    app.add_handler(
        CommandHandler(
            "joke",
            joke_command
        )
    )

    app.add_handler(
        CommandHandler(
            "game",
            game_command
        )
    )

    app.add_handler(
        CommandHandler(
            "dicegame",
            dicegame_command
        )
    )

    app.add_handler(
        CommandHandler(
            "dice",
            dice_command
        )
    )

    app.add_handler(
        CommandHandler(
            "coin",
            coin_command
        )
    )

    app.add_handler(
        CommandHandler(
            "rps",
            rps_command
        )
    )

    app.add_handler(
        CommandHandler(
            "mathgame",
            mathgame_command
        )
    )

    app.add_handler(
        CommandHandler(
            "scramble",
            scramble_command
        )
    )

    app.add_handler(
        CommandHandler(
            "quiz",
            quiz_command
        )
    )

    app.add_handler(
        CommandHandler(
            "profile",
            profile_command
        )
    )

    app.add_handler(
        CommandHandler(
            "top",
            top_command
        )
    )

    app.add_handler(
        CommandHandler(
            "daily",
            daily_command
        )
    )

    app.add_handler(
        CommandHandler(
            "balance",
            balance_command
        )
    )

    app.add_handler(
        CommandHandler(
            "work",
            work_command
        )
    )

    app.add_handler(
        CommandHandler(
            "shop",
            shop_command
        )
    )

    app.add_handler(
        CommandHandler(
            "buy",
            buy_command
        )
    )

    app.add_handler(
        CommandHandler(
            "inventory",
            inventory_command
        )
    )

    app.add_handler(
        CommandHandler(
            "achievements",
            achievements_command
        )
    )

    app.add_handler(
        CommandHandler(
            "random",
            random_command
        )
    )

    app.add_handler(
        CommandHandler(
            "calc",
            calc_command
        )
    )

    app.add_handler(
        CommandHandler(
            "fact",
            fact_command
        )
    )

    app.add_handler(
        CommandHandler(
            "translate",
            translate_command
        )
    )

    app.add_handler(
        CommandHandler(
            "id",
            id_command
        )
    )

    app.add_handler(
        CommandHandler(
            "about",
            about_command
        )
    )


    # =========================
    # 🖼️ IMAGE
    # =========================

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            image_handler
        )
    )


    # =========================
    # 🎤 VOICE
    # =========================

    app.add_handler(
        MessageHandler(
            filters.VOICE,
            voice
        )
    )


    # =========================
    # 💬 TEXT
    # =========================

    app.add_handler(
        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            chat

        )
    )


    print(
        "🤖 BOT ISHLAYAPTI..."
    )

    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# ▶️ START
# =========================================================

if __name__ == "__main__":

    main()
