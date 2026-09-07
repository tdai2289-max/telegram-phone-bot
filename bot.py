import sqlite3

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8992428607:AAFY0Nc6jhAEgIAuLU6v3gfWxIW4bp3RNW4"
ADMIN_ID = 5257699798


conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = KeyboardButton(
        "📱 Chia sẻ số điện thoại",
        request_contact=True
    )

    keyboard = ReplyKeyboardMarkup(
        [[button]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(
        "Bấm nút bên dưới để chia sẻ số điện thoại:",
        reply_markup=keyboard
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"ID Telegram của bạn: {update.effective_user.id}"
    )


async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact

    if contact.user_id != user.id:
        await update.message.reply_text(
            "❌ Vui lòng chia sẻ số điện thoại của chính bạn."
        )
        return

    cursor.execute("""
        INSERT INTO users (
            telegram_id,
            username,
            first_name,
            last_name,
            phone
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            phone = excluded.phone
    """, (
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        contact.phone_number
    ))

    conn.commit()

    await update.message.reply_text(
        "✅ 🎮 Bạn cần gửi tên nhân vật và game mình chơi để nhận code..",
        reply_markup=ReplyKeyboardRemove()
    )


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Không có quyền.")
        return

    cursor.execute("""
        SELECT telegram_id, username, first_name, phone, created_at
        FROM users
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("Chưa có ai chia sẻ SĐT.")
        return

    text = f"📋 Tổng: {len(rows)} người\n\n"

    for telegram_id, username, first_name, phone, created_at in rows:
        text += (
            f"👤 {first_name or 'Không tên'}\n"
            f"🆔 {telegram_id}\n"
            f"🔗 @{username if username else 'không có'}\n"
            f"📱 {phone}\n"
            f"🕒 {created_at}\n"
            "────────────\n"
        )

        if len(text) > 3500:
            await update.message.reply_text(text)
            text = ""

    if text:
        await update.message.reply_text(text)


async def count_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Không có quyền.")
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    await update.message.reply_text(
        f"👥 Có {count} người đã chia sẻ SĐT."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("count", count_users))
    app.add_handler(MessageHandler(filters.CONTACT, get_contact))

    print("Bot đang chạy...")

    app.run_polling()


if __name__ == "__main__":
    main()