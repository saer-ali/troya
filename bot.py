import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        # قائمة الأدمن
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 لوحة الأدمن", callback_data="admin_panel")],
            [InlineKeyboardButton("🆔 عرض المعرف", callback_data="show_id")],
            [InlineKeyboardButton("📁 فحص المتغيرات", callback_data="check_env")],
            [InlineKeyboardButton("❌ إغلاق البوت", callback_data="shutdown")]
        ])
        await update.message.reply_text("🔐 **مرحباً أيها الأدمن!**\nاختر من القائمة:", parse_mode="Markdown", reply_markup=keyboard)
    else:
        # قائمة المستخدم العادي
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("اضغط هنا", callback_data="test_button")],
            [InlineKeyboardButton("🆔 عرض المعرف", callback_data="show_id")],
            [InlineKeyboardButton("📁 فحص المتغيرات", callback_data="check_env")]
        ])
        await update.message.reply_text("مرحباً! اختر:", reply_markup=keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or "لا يوجد"
    first_name = query.from_user.first_name or "لا يوجد"
    
    if query.data == "test_button":
        await query.edit_message_text("✅ تم بنجاح!")
    
    elif query.data == "show_id":
        msg = f"""🆔 **معلومات حسابك:**

• المعرف (ID): `{user_id}`
• اسم المستخدم: @{username}
• الاسم الأول: {first_name}
• صلاحيات: {'👑 أدمن' if user_id == ADMIN_ID else '👤 مستخدم عادي'}"""
        await query.edit_message_text(msg, parse_mode="Markdown")
    
    elif query.data == "check_env":
        bot_token = os.getenv("BOT_TOKEN")
        admin_id = os.getenv("ADMIN_ID")
        base_url = os.getenv("BASE_URL")
        agent_user = os.getenv("AGENT_USER")
        
        msg = f"""📁 **متغيرات البيئة:**

BOT_TOKEN: {'✅ موجود' if bot_token else '❌ غير موجود'}
ADMIN_ID: {'✅ موجود' if admin_id else '❌ غير موجود'}
BASE_URL: {'✅ موجود' if base_url else '❌ غير موجود'}
AGENT_USER: {'✅ موجود' if agent_user else '❌ غير موجود'}
AGENT_PASS: {'✅ موجود' if os.getenv("AGENT_PASS") else '❌ غير موجود'}
PARENT_ID: {'✅ موجود' if os.getenv("PARENT_ID") else '❌ غير موجود'}

CURRENCY: {os.getenv('CURRENCY', 'NSP')}
"""
        await query.edit_message_text(msg, parse_mode="Markdown")
    
    elif query.data == "admin_panel":
        msg = """👑 **لوحة التحكم**

• إدارة المستخدمين
• مراجعة الإيداعات
• مراجعة السحوبات
• إعدادات النظام"""
        await query.edit_message_text(msg, parse_mode="Markdown")
    
    elif query.data == "shutdown":
        if user_id == ADMIN_ID:
            await query.edit_message_text("⏹️ جاري إيقاف البوت...")
            os._exit(0)
        else:
            await query.edit_message_text("❌ ليس لديك صلاحية!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()