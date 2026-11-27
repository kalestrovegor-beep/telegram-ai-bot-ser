import os
import time
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import pandas as pd
import telebot
from telebot import types

TOKEN = os.environ.get("TOKEN", "ВАШ_ТОКЕН_БОТА").strip()
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(TOKEN, threaded=False)
users = {}

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "coins": 0,
            "tap_power": 1,
            "passive_income": 0,
            "energy": 1000,
            "max_energy": 1000
        }
    return users[user_id]

def get_game_kb():
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🐹 ТАПНУТЬ!", callback_data="tap"))
    kb.row(
        types.InlineKeyboardButton("⚡ +1 к тапу (50 🪙)", callback_data="buy_tap"),
        types.InlineKeyboardButton("📈 +5/мин авто (150 🪙)", callback_data="buy_passive")
    )
    kb.row(
        types.InlineKeyboardButton("🔋 Энергия 100% (100 🪙)", callback_data="buy_energy"),
        types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh")
    )
    return kb

def get_stats_text(user):
    return (
        f"🐹 *HAMSTER CLICKER*\n\n"
        f"💰 Баланс: *{user['coins']}* монет\n"
        f"👆 Сила тапа: *+{user['tap_power']}*\n"
        f"⚙️ Пассивный доход: *+{user['passive_income']}*/мин\n"
        f"⚡ Энергия: *{user['energy']}/{user['max_energy']}*"
    )

@bot.message_handler(commands=['start'])
def cmd_start(message):
    get_user(message.from_user.id)
    text = (
        "👋 *Привет! Я твой облачный бот 24/7 на Render.*\n\n"
        "🎮 *Hamster Clicker:* `/game` — тапай и прокачивайся.\n"
        "🎨 *Генератор картинок:* `/img запрос` (например: `/img золотой хомяк на луне`)\n"
        "📊 *Таблицы Excel:*\n"
        "`/table Товар; Цена\nЯблоки; 100\nБананы; 80`\n"
        "• `/top` — таблица лидеров\n"
        "• `/expenses` — шаблон расходов"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['img'])
def cmd_image(message):
    prompt = message.text.replace("/img", "").strip()
    if not prompt:
        bot.send_message(message.chat.id, "🎨 Пример: `/img неоновый хомяк хакер`", parse_mode="Markdown")
        return

    wait_msg = bot.send_message(message.chat.id, "⏳ Рисую картинку...")
    encoded_prompt = urllib.parse.quote(prompt)
    image_url = f"https://pollinations.ai{encoded_prompt}?width=1024&height=1024&nologo=true"
    
    try:
        bot.send_photo(message.chat.id, image_url, caption=f"✨ Готово: *{prompt}*", parse_mode="Markdown")
        bot.delete_message(message.chat.id, wait_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", message.chat.id, wait_msg.message_id)

@bot.message_handler(commands=['game'])
def cmd_game(message):
    user = get_user(message.from_user.id)
    bot.send_message(message.chat.id, get_stats_text(user), reply_markup=get_game_kb(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user = get_user(call.from_user.id)
    if call.data == "tap":
        if user["energy"] >= user["tap_power"]:
            user["coins"] += user["tap_power"]
            user["energy"] -= user["tap_power"]
            bot.edit_message_text(get_stats_text(user), call.message.chat.id, call.message.message_id, reply_markup=get_game_kb(), parse_mode="Markdown")
            bot.answer_callback_query(call.id, f"+{user['tap_power']} 🪙")
        else:
            bot.answer_callback_query(call.id, "❌ Нет энергии!", show_alert=True)
    elif call.data == "buy_tap":
        if user["coins"] >= 50:
            user["coins"] -= 50
            user["tap_power"] += 1
            bot.edit_message_text(get_stats_text(user), call.message.chat.id, call.message.message_id, reply_markup=get_game_kb(), parse_mode="Markdown")
            bot.answer_callback_query(call.id, "✅ Сила тапа +1!")
        else:
            bot.answer_callback_query(call.id, "❌ Нужно 50 монет!", show_alert=True)
    elif call.data == "buy_passive":
        if user["coins"] >= 150:
            user["coins"] -= 150
            user["passive_income"] += 5
            bot.edit_message_text(get_stats_text(user), call.message.chat.id, call.message.message_id, reply_markup=get_game_kb(), parse_mode="Markdown")
            bot.answer_callback_query(call.id, "✅ Доход +5/мин!")
        else:
            bot.answer_callback_query(call.id, "❌ Нужно 150 монет!", show_alert=True)
    elif call.data == "buy_energy":
        if user["coins"] >= 100:
            user["coins"] -= 100
            user["energy"] = user["max_energy"]
            bot.edit_message_text(get_stats_text(user), call.message.chat.id, call.message.message_id, reply_markup=get_game_kb(), parse_mode="Markdown")
            bot.answer_callback_query(call.id, "✅ Энергия полная!")
        else:
            bot.answer_callback_query(call.id, "❌ Нужно 100 монет!", show_alert=True)
    elif call.data == "refresh":
        bot.edit_message_text(get_stats_text(user), call.message.chat.id, call.message.message_id, reply_markup=get_game_kb(), parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Обновлено")

def passive_worker():
    while True:
        time.sleep(60)
        for user in users.values():
            user["coins"] += user["passive_income"]
            user["energy"] = min(user["max_energy"], user["energy"] + 50)

@bot.message_handler(commands=['table'])
def cmd_table(message):
    raw_text = message.text.replace("/table", "").strip()
    if not raw_text:
        bot.send_message(message.chat.id, "❗ Пример:\n`/table Имя; Город\nИван; Москва\nАнна; Казань`", parse_mode="Markdown")
        return
    try:
        lines = [line.split(";") for line in raw_text.split("\n") if line.strip()]
        df = pd.DataFrame(lines[1:], columns=lines[0])
        file_path = f"table_{message.from_user.id}.xlsx"
        df.to_excel(file_path, index=False)
        with open(file_path, "rb") as f:
            bot.send_document(message.chat.id, f, caption="📊 Ваша таблица готова!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка формата: {e}")

@bot.message_handler(commands=['top'])
def cmd_top(message):
    data = [{"ID": uid, "Монеты": info["coins"], "Тап": info["tap_power"]} for uid, info in users.items()]
    df = pd.DataFrame(data).sort_values(by="Монеты", ascending=False)
    file_path = "top_players.xlsx"
    df.to_excel(file_path, index=False)
    with open(file_path, "rb") as f:
        bot.send_document(message.chat.id, f, caption="🏆 Лидеры кликера")

@bot.message_handler(commands=['expenses'])
def cmd_expenses(message):
    data = [
        {"Дата": "01.11.2026", "Категория": "Продукты", "Сумма": 1500},
        {"Дата": "02.11.2026", "Категория": "Транспорт", "Сумма": 300}
    ]
    df = pd.DataFrame(data)
    file_path = "expenses.xlsx"
    df.to_excel(file_path, index=False)
    with open(file_path, "rb") as f:
        bot.send_document(message.chat.id, f, caption="💰 Шаблон расходов")

# Веб-сервер для приема сообщений напрямую от Telegram (Webhook)
class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        update = telebot.types.Update.de_json(post_data)
        bot.process_new_updates([update])
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

if __name__ == "__main__":
    threading.Thread(target=passive_worker, daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{RENDER_URL}/")
    print("Webhook успешно установлен на", RENDER_URL, flush=True)
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    server.serve_forever()
