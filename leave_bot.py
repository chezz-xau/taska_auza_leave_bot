import os
import logging
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Konfigurasi Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ambil Environment Variables dari Render
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
OWNER_IDS = [int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip()]

# Fungsi Sambungan ke Neon Database
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Handler /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Semak sama ada pengguna adalah Owner atau Staf
    if user_id in OWNER_IDS:
        keyboard = [
            [InlineKeyboardButton("📋 Senarai Permohonan Cuti", callback_data="list_leaves")],
            [InlineKeyboardButton("➕ Tambah Kuota Cuti Staf", callback_data="add_leave_quota")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("👋 Selamat datang, Owner! Sila pilih menu pengurusan cuti:", reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("📝 Mohon Cuti", callback_data="apply_leave")],
            [InlineKeyboardButton("📊 Semak Baki Cuti", callback_data="check_balance")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("👋 Selamat datang ke Sistem Cuti Staf. Sila pilih tindakan:", reply_markup=reply_markup)

# Fungsi Semak Baki Cuti untuk Staf
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_name = query.from_user.full_name
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT total_leave, taken_leave, balance_leave FROM staff_leaves WHERE staff_name = %s", (user_name,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        total, taken, balance = result
        text = f"📊 **Rekod Cuti Anda ({user_name})**\n\n📌 Jumlah Kelayakan: {total} hari\n❌ Cuti Diambil: {taken} hari\n✅ Baki Cuti: {balance} hari"
    else:
        # Jika nama tiada lagi dalam database, masukkan rekod lalai
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO staff_leaves (staff_name, total_leave, taken_leave, balance_leave) VALUES (%s, 14, 0, 14)", (user_name,))
        conn.commit()
        cur.close()
        conn.close()
        text = f"📊 **Rekod Cuti Anda ({user_name})**\n\n📌 Jumlah Kelayakan: 14 hari\n❌ Cuti Diambil: 0 hari\n✅ Baki Cuti: 14 hari"
        
    await query.edit_message_text(text=text, parse_mode="Markdown")

# Fungsi Butang Callback Utama
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "check_balance":
        await check_balance(update, context)
    elif data == "apply_leave":
        await query.answer()
        await query.edit_message_text(text="📝 Sila hantar permohonan cuti anda dengan format:\n\n`Cuti: [Tarikh Mula] hingga [Tarikh Akhir] - [Sebab]`\n\nContoh: `Cuti: 10/11/2026 hingga 12/11/2026 - Urusan Keluarga`", parse_mode="Markdown")

# Main Function untuk Jalankan Bot
def main():
    if not TOKEN or not DATABASE_URL:
        logger.error("TELEGRAM_BOT_TOKEN atau DATABASE_URL tidak dijumpai di environment variables!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot Cuti Staf sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
