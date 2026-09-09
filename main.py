import os
import json
import time
import urllib.request
import urllib.parse
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not TOKEN:
    raise ValueError("Falta TELEGRAM_BOT_TOKEN")

if not API_KEY:
    raise ValueError("Falta TWELVE_DATA_API_KEY")

bot = telebot.TeleBot(TOKEN)

ASSETS = {
    "EUR/USD": "EUR/USD",
    "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY",
    "EUR/JPY": "EUR/JPY",
    "GOLD (XAU/USD)": "XAU/USD"
}

EXPIRIES = [
    "15 segundos",
    "30 segundos",
    "1 minuto",
    "2 minutos",
    "5 minutos"
]


def get_market_data(symbol):
    params = urllib.parse.urlencode({
        "symbol": symbol,
        "interval": "1min",
        "outputsize": 60,
        "apikey": API_KEY
    })

    url = "https://api.twelvedata.com/time_series?" + params

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        data = json.loads(response.read().decode())

    if "values" not in data:
        raise ValueError(data.get("message", "No se recibieron datos"))

    values = list(reversed(data["values"]))

    closes = [float(x["close"]) for x in values]

    return closes


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (price - result) * multiplier + result

    return result


def rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def analyze(values):
    ema20 = ema(values, 20)
    ema50 = ema(values, 50)
    rsi_value = rsi(values, 14)

    if ema20 is None or ema50 is None or rsi_value is None:
        return "SIN SEÑAL", "No hay suficientes datos."

    last_price = values[-1]
    diferencia_ema = abs(ema20 - ema50) / last_price * 100

    if diferencia_ema < 0.005:
        return "SIN SEÑAL", (
            f"EMA20: {ema20:.5f}\n"
            f"EMA50: {ema50:.5f}\n"
            f"RSI: {rsi_value:.1f}\n"
            "Tendencia demasiado débil."
        )
    if ema20 > ema50 and rsi_value > 55 and last_price > ema20:
        return "CALL", (
            f"EMA20 > EMA50\n"
            f"RSI: {rsi_value:.1f}\n"
            f"Precio sobre EMA20"
        )

    if ema20 < ema50 and rsi_value < 45 and last_price < ema20:
        return "PUT", (
            f"EMA20 < EMA50\n"
            f"RSI: {rsi_value:.1f}\n"
            f"Precio bajo EMA20"
        )

    return "SIN SEÑAL", (
        f"EMA20: {ema20:.5f}\n"
        f"EMA50: {ema50:.5f}\n"
        f"RSI: {rsi_value:.1f}\n"
        "Condiciones no suficientemente claras."
    )


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


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("asset|")
)
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


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("expiry|")
)
def signal(call):
    _, asset, expiry = call.data.split("|", 2)

    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        f"🔎 ANALIZANDO...\n\n"
        f"📊 Activo: {asset}\n"
        f"⏱️ Expiración: {expiry}\n\n"
        "⏳ Consultando datos de mercado..."
        ,
        call.message.chat.id,
        call.message.message_id
    )

    try:
        symbol = ASSETS[asset]

        prices = get_market_data(symbol)

        direction, explanation = analyze(prices)

        if direction == "CALL":
            result = "🟢 CALL"
        elif direction == "PUT":
            result = "🔴 PUT"
        else:
            result = "⚪ SIN SEÑAL"

        message_text = (
            "📊 SEÑAL\n\n"
            f"Activo: {asset}\n"
            f"Expiración seleccionada: {expiry}\n\n"
            f"➡️ {result}\n\n"
            "📈 Análisis técnico:\n"
            f"{explanation}\n\n"
            "⚠️ Señal experimental. No garantiza ganancias.\n"
            "Prueba primero en demo."
        )

    except Exception as e:
        message_text = (
            "❌ ERROR AL OBTENER DATOS\n\n"
            f"Activo: {asset}\n"
            f"Expiración: {expiry}\n\n"
            f"Detalle: {str(e)}"
        )

    bot.edit_message_text(
        message_text,
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

print("🤖 Bot funcionando con datos de Twelve Data")

bot.infinity_polling(skip_pending=True)
