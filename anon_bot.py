import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# === Sozlamalar ===
BOT_TOKEN = "8001374574:AAFyfXejjMfrynxAA4Oa9zQPLkxUOPI_7H0"
CHANNEL_ID = -1003299368748   # to‘liq kanal ID
ADMINS = {2055121156}         # o‘zingning Telegram ID

DB_PATH = "anon.db"

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Ma’lumotlar bazasi ===
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        anon_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message_text TEXT NOT NULL,
        timestamp INTEGER DEFAULT (strftime('%s','now'))
    )
    """)
    con.commit()
    con.close()

def save_feedback(user_id: int, text: str) -> int:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO feedback (user_id, message_text) VALUES (?, ?)", (user_id, text))
    anon_id = cur.lastrowid
    con.commit()
    con.close()
    return anon_id

# === Start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Bu anonim shikoyat bot.\n"
        "Xabaringizni shu yerga yozing, biz uni anonim tarzda ko‘rib chiqamiz."
    )

# === Shaxsiy xabarni qabul qilish ===
async def private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    text = update.message.text
    user_id = update.effective_user.id
    anon_id = save_feedback(user_id, text)

    channel_text = f"📩 Yangi anonim xabar #{anon_id}:\n\n{text}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Javob berish", callback_data=f"reply:{anon_id}")]
    ])

    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=channel_text, reply_markup=keyboard)
        await update.message.reply_text("✅ Xabaringiz anonim tarzda yuborildi.")
    except Exception as e:
        logger.exception("Kanalga yuborishda xato:")
        await update.message.reply_text("⚠️ Kanalga yuborib bo‘lmadi. Admin bilan bog‘laning.")

# === Callback (javob berish) ===
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("reply:"):
        return

    anon_id = int(data.split(":")[1])
    user = update.effective_user

    if user.id not in ADMINS:
        await query.message.reply_text("⛔ Bu tugma faqat adminlar uchun.")
        return

    await context.bot.send_message(
        chat_id=user.id,
        text=f"Anon #{anon_id} ga javob yozish uchun:\n\n/send {anon_id} <xabar matni>"
    )

# === Admin javobi ===
async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMINS:
        await update.message.reply_text("⛔ Faqat adminlar uchun.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Foydalanish: /send <anon_id> <xabar>")
        return

    anon_id = int(context.args[0])
    reply_text = " ".join(context.args[1:])

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT user_id FROM feedback WHERE anon_id = ?", (anon_id,))
    row = cur.fetchone()
    con.close()

    if not row:
        await update.message.reply_text("Bunday ID topilmadi.")
        return

    user_id = row[0]
    try:
        await context.bot.send_message(chat_id=user_id, text=f"📬 Admin javobi:\n\n{reply_text}")
        await update.message.reply_text("✅ Javob yuborildi.")
    except Exception as e:
        await update.message.reply_text("⚠️ Foydalanuvchiga javob yuborib bo‘lmadi.")

# === Asosiy ===
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send", send_reply))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, private_message))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
