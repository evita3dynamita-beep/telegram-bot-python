import os
import time
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("Falta la variable TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

ASSETS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "EUR/JPY",
    "GOLD (XAU/USD)"
]

EXPIRIES = [
    "15 segundos",
    "30 segundos",
    "1 minuto",
    "2 minutos",
    "5 minutos"
]


@bot.message_handler(commands=["start"])
def start(message):
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    for asset in ASSETS:
        button = types.InlineKeyboardButton(
            asset,
            callback_data=f"asset|{asset}"
        )
        keyboard.add(button)

    bot.send_message(
        message.chat.id,
        "📊 BOT DE SEÑALES BINARIAS\n\n"
        "Selecciona el activo que quieres analizar:",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("asset|"))
def choose_expiry(call):
    asset = call.data.split("|", 1)[1]

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    for expiry in EXPIRIES:
        button = types.InlineKeyboardButton(
            expiry,
            callback_data=f"expiry|{asset}|{expiry}"
        )
        keyboard.add(button)

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        f"📈 Activo: {asset}\n\n"
        "⏱️ Selecciona el tiempo de expiración:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("expiry|"))
def signal(call):
    _, asset, expiry = call.data.split("|", 2)

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        f"🔎 ANALIZANDO...\n\n"
        f"📊 Activo: {asset}\n"
        f"⏱️ Expiración: {expiry}\n\n"
        "⏳ Preparando señal...",
        call.message.chat.id,
        call.message.message_id
    )

    time.sleep(2)

    bot.edit_message_text(
        f"📊 ANÁLISIS\n\n"
        f"Activo: {asset}\n"
        f"Expiración: {expiry}\n\n"
        "⚠️ Aún no hay datos de mercado conectados.\n\n"
        "Este bot está preparado para añadir el sistema "
        "de análisis técnico posteriormente.",
        call.message.chat.id,
        call.message.message_id
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Usa /start para abrir el menú de señales."
    )


bot.delete_webhook(drop_pending_updates=True)

print("🤖 Bot funcionando")

bot.infinity_polling(skip_pending=True)
