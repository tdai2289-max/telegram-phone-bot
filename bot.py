import os
import sqlite3

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 5257699798


# =========================
# DATABASE
# =========================

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    character_name TEXT,
    game_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# Tự thêm cột nếu đang dùng database cũ
try:
    cursor.execute(
        "ALTER TABLE users ADD COLUMN character_name TEXT"
    )
except sqlite3.OperationalError:
    pass

try:
    cursor.execute(
        "ALTER TABLE users ADD COLUMN game_name TEXT"
    )
except sqlite3.OperationalError:
    pass

conn.commit()


# =========================
# /START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
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
        "🎁 Để nhận code, vui lòng chia sẻ số điện thoại của bạn.",
        reply_markup=keyboard
    )


# =========================
# /MYID
# =========================

async def myid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        f"ID Telegram của bạn: {update.effective_user.id}"
    )


# =========================
# NHẬN SỐ ĐIỆN THOẠI
# =========================

async def get_contact(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    contact = update.message.contact

    # Chỉ nhận SĐT của chính người đang dùng bot
    if not contact.user_id or contact.user_id != user.id:
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

    # Đánh dấu bot đang chờ người này gửi tên nhân vật/game
    context.user_data["waiting_game_info"] = True

    await update.message.reply_text(
        "🎮 Bạn cần gửi tên nhân vật và tên game mình chơi để nhận code.\n\n"
        "Gửi theo mẫu:\n"
        "Tên nhân vật / Tên game\n\n"
        "Ví dụ:\n"
        "Ronaldo123 / FC Mobile",
        reply_markup=ReplyKeyboardRemove()
    )


# =========================
# NHẬN TÊN NHÂN VẬT + GAME
# =========================

async def get_game_info(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.user_data.get("waiting_game_info"):
        return

    text = update.message.text.strip()

    if "/" not in text:
        await update.message.reply_text(
            "❌ Sai định dạng.\n\n"
            "Hãy gửi theo mẫu:\n"
            "Tên nhân vật / Tên game\n\n"
            "Ví dụ:\n"
            "Ronaldo123 / FC Mobile"
        )
        return

    character_name, game_name = text.split("/", 1)

    character_name = character_name.strip()
    game_name = game_name.strip()

    if not character_name or not game_name:
        await update.message.reply_text(
            "❌ Bạn cần nhập đầy đủ tên nhân vật và tên game.\n\n"
            "Ví dụ:\n"
            "Ronaldo123 / FC Mobile"
        )
        return

    user = update.effective_user

    cursor.execute("""
        UPDATE users
        SET character_name = ?,
            game_name = ?
        WHERE telegram_id = ?
    """, (
        character_name,
        game_name,
        user.id
    ))

    conn.commit()

    context.user_data["waiting_game_info"] = False

    await update.message.reply_text(
        "✅ Đã nhận thông tin.\n"
        "Vui lòng chờ admin kiểm tra và gửi code."
    )


# =========================
# /USERS - ADMIN
# =========================

async def users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Bạn không có quyền sử dụng lệnh này."
        )
        return

    cursor.execute("""
        SELECT
            telegram_id,
            username,
            first_name,
            last_name,
            phone,
            character_name,
            game_name,
            created_at
        FROM users
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text(
            "Chưa có người dùng nào."
        )
        return

    text = f"📋 Tổng cộng: {len(rows)} người\n\n"

    for row in rows:
        (
            telegram_id,
            username,
            first_name,
            last_name,
            phone,
            character_name,
            game_name,
            created_at
        ) = row

        full_name = " ".join(
            x for x in [first_name, last_name] if x
        )

        username_text = (
            f"@{username}"
            if username
            else "Không có"
        )

        item = (
            f"👤 {full_name or 'Không tên'}\n"
            f"🆔 ID: {telegram_id}\n"
            f"🔗 Username: {username_text}\n"
            f"📱 SĐT: {phone or 'Chưa có'}\n"
            f"🕹 Tên nhân vật: "
            f"{character_name or 'Chưa nhập'}\n"
            f"🎮 Game: {game_name or 'Chưa nhập'}\n"
            f"🕒 Thời gian: {created_at}\n"
            "────────────────\n"
        )

        if len(text) + len(item) > 3800:
            await update.message.reply_text(text)
            text = ""

        text += item

    if text:
        await update.message.reply_text(text)


# =========================
# /COUNT - ADMIN
# =========================

async def count_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Bạn không có quyền sử dụng lệnh này."
        )
        return

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    count = cursor.fetchone()[0]

    await update.message.reply_text(
        f"👥 Tổng cộng có {count} người đã đăng ký."
    )


# =========================
# RUN BOT
# =========================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("myid", myid)
    )

    app.add_handler(
        CommandHandler("users", users)
    )

    app.add_handler(
        CommandHandler("count", count_users)
    )

    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            get_contact
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            get_game_info
        )
    )

    print("Bot đang chạy...")

    app.run_polling()


if __name__ == "__main__":
    main()
