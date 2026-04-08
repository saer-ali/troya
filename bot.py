import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from agent_api import AgentAPI

load_dotenv()
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from database import (
    DB_PATH,
    get_conn,
    init_db,
    save_user,
    get_user_full,
    is_user_registered,
    get_wallet_balance,
    add_to_wallet,
    deduct_from_wallet,
    create_pending_deposit,
    get_pending_deposit,
    get_all_pending_deposits,
    confirm_deposit_by_admin,
    reject_deposit_by_admin,
    is_first_deposit,
    save_withdrawal,
    get_withdrawal,
    get_pending_withdrawals,
    update_withdrawal_status,
    get_cashier_balance,
    set_cashier_balance,
    update_cashier_balance,
    add_cashier_transaction,
    get_next_sequence_number,
    update_sequence_number,
    update_ichancy_credentials,
    get_bot_status,
    set_bot_status,
    get_bot_status_message,
    log_operation,
    get_user_transactions,
    get_bonus_settings,
    set_bonus_settings,
    create_pending_deletion,
    get_pending_deletion,
    get_pending_deletions_list,
    approve_deletion_by_admin,
    reject_deletion_by_admin,
    create_pending_withdrawal,
    get_pending_withdrawal_by_id,
    add_wallet_transaction,
    get_referral_settings,
    set_referral_settings,
    get_referral_user_id,
    get_payment_settings,
    update_payment_method,
    get_local_payment_settings,
    update_local_payment_settings,
    get_deposit_settings,
    set_deposit_settings,
    get_wallet_addresses,
    update_wallet_addresses,
    get_all_users,
    get_user_count,
    get_binance_pay_settings,
    set_binance_pay_settings,
    get_user_by_ichancy_username,
    ensure_user_exists,
    get_crypto_wallet_addresses,
    update_crypto_wallet_addresses,
    create_gift_request,
    get_gift_request,
    get_pending_gift_requests,
    get_gift_request_by_code,
    approve_gift_request,
    reject_gift_request,
)
from agent_api import AgentAPI, IchancyAPI

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
print("🔧 الإعدادات الحالية:")
print(f"  BASE_URL: {os.getenv('BASE_URL') or '❌ غير مضبوط'}")
print(f"  AGENT_USER: {os.getenv('AGENT_USER') or '❌ غير مضبوط'}")
print(f"  AGENT_PASS: {'✅ مضبوط' if os.getenv('AGENT_PASS') else '❌ غير مضبوط'}")
print(f"  PARENT_ID: {os.getenv('PARENT_ID') or '❌ غير مضبوط'}")
print(f"  CURRENCY: {os.getenv('CURRENCY') or 'NSP (افتراضي)'}")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_PASSWORD = "1111"
ICHANCY_URL = os.getenv("ICHANCY_URL", "https://ichancy.com")

# إعدادات عامة
USDT_TO_NSP_RATE = 11800.0
DEPOSIT_FEE_PERCENT = 0.0

# حالات المحادثة
REG_NAME = 1
REG_PASS = 2
DEP_CRYPTO_TX = 3
DEP_CRYPTO_AMOUNT = 4
DEP_LOCAL_CODE = 5
ADMIN_DEP_AMOUNT = 6
ADMIN_REJECT_REASON = 7
WITHDRAW_AMOUNT = 8
WITHDRAW_WALLET = 9
ADMIN_SET_CASHIER = 10
ADMIN_SET_RATE = 11
ADMIN_SET_DEPOSIT_FEE = 12
ADMIN_SET_REST_MESSAGE = 13
ADMIN_SET_MAINTENANCE_MESSAGE = 14
ADMIN_DELETE_CONFIRM = 15
ADMIN_SET_SUBSEQUENT_BONUS = 16
ADMIN_AUTH_PASSWORD = 17
RESET_PASS_NEW = 18
RESET_PASS_CONFIRM = 19
RESET_PASS_FINAL_CONFIRM = 20
ADMIN_EDIT_REFERRAL_USERNAME = 21
ADMIN_EDIT_WITHDRAWAL_COMMISSION = 22
ADMIN_EDIT_REFERRAL_COMMISSION = 23
ADMIN_EDIT_SERTEL = 30
ADMIN_EDIT_CRYPTO_WALLET = 31
ADMIN_EDIT_SHAM_LIRA = 32
ADMIN_EDIT_SHAM_DOLLAR = 33
ADMIN_EDIT_SHAM_DOLLAR_1 = 34
ADMIN_EDIT_SHAM_DOLLAR_2 = 35
ADMIN_EDIT_USDT_ADDRESS = 36
ADMIN_EDIT_SERTEL_CASH_1 = 37
ADMIN_EDIT_SERTEL_CASH_2 = 38
ADMIN_EDIT_SHAM_LIRA_1 = 39
ADMIN_EDIT_SHAM_LIRA_2 = 40
INVITE_USERNAME = 43
GIFT_TRANSFER_USERNAME = 46
GIFT_TRANSFER_AMOUNT = 47
USER_DELETE_CONFIRM = 48
GIFT_REDEEM_CODE = 49
ADMIN_GIFT_APPROVE = 50

user_data = {}


# === دوال مساعدة ===
def is_bot_active():
    return get_bot_status().get("status") == "active"


def get_ichancy_balance(telegram_id):
    """الحصول على رصيد المستخدم من منصة Ichancy"""
    try:
        user = get_user_full(telegram_id)
        if not user or len(user) <= 3 or not user[3]:
            return 0, "غير موجود"

        ichancy_username = user[3]
        agent = AgentAPI()
        player_id = agent.get_player_id(ichancy_username)

        if not player_id:
            return 0, ichancy_username

        ichancy_bal_data = agent.get_balance(player_id)
        if ichancy_bal_data:
            for bal in ichancy_bal_data:
                if isinstance(bal, dict):
                    if "balance" in bal:
                        return float(bal["balance"]), ichancy_username
                    elif "amount" in bal:
                        return float(bal["amount"]), ichancy_username

        return 0, ichancy_username
    except Exception as e:
        print(f"Error getting Ichancy balance: {e}")
        return 0, "خطأ"


def get_exchange_rate():
    return USDT_TO_NSP_RATE


def set_exchange_rate(new_rate):
    global USDT_TO_NSP_RATE
    USDT_TO_NSP_RATE = float(new_rate)
    return USDT_TO_NSP_RATE


def get_deposit_fee():
    return DEPOSIT_FEE_PERCENT


def set_deposit_fee(percent):
    global DEPOSIT_FEE_PERCENT
    DEPOSIT_FEE_PERCENT = float(percent)
    return DEPOSIT_FEE_PERCENT


# ==================== دوال لوحة المفاتيح الرئيسية ====================


def get_main_keyboard(user_id):
    """لوحة المفاتيح الرئيسية - الديناميكية حسب الصلاحية"""
    row1 = [InlineKeyboardButton("👤 حسابي", callback_data="my_account_menu")]
    row2 = [
        InlineKeyboardButton("💰 إيداع رصيد", callback_data="deposit_menu"),
        InlineKeyboardButton("💳 سحب رصيد", callback_data="withdraw_menu"),
    ]
    row3 = [InlineKeyboardButton("🎃 الألعاب", callback_data="games_menu")]
    row4 = [
        InlineKeyboardButton("⚽ مباريات اليوم", url="https://www.ichancy.com/ar/prematch/match/todayEvents/Soccer"),
        InlineKeyboardButton("📵 مباريات مباشرة", url="https://www.ichancy.com/ar/live-events/match/Soccer"),
    ]
    row5 = [InlineKeyboardButton("🐵 طروادة", callback_data="trojan_menu")]
    row6 = [
        InlineKeyboardButton("📵 الشروط والأحكام", callback_data="terms_conditions"),
        InlineKeyboardButton("📫 تحميل ابليكاشن", callback_data="ichancy_apk"),
    ]
    row7 = [InlineKeyboardButton("💒 التواصل معنا", callback_data="contact_us")]

    keyboard = [row1, row2, row3, row4, row5, row6, row7]

    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🛻 الإعدادات", callback_data="admin_bot_status")])
        keyboard.append([InlineKeyboardButton("⚙️ التعديلات", callback_data="admin_settings_auth")])

    return InlineKeyboardMarkup(keyboard)


def get_my_account_keyboard():
    """لوحة حسابي - مع خيارات التعديل"""
    keyboard = [
        [InlineKeyboardButton("📳 سجل المعاملات", callback_data="history")],
        [InlineKeyboardButton("🗑️ حذف الحساب", callback_data="request_delete_account")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_deposit_methods_keyboard():
    """لوحة خيارات الإيداع"""
    keyboard = [
        [InlineKeyboardButton("💻 شام كاش ليرة", callback_data="dep_sham_lira"), InlineKeyboardButton("💼 شام كاش دولار", callback_data="dep_sham_dollar")],
        [InlineKeyboardButton("💼 سيرتل كاش", callback_data="dep_sertel")],
        [InlineKeyboardButton("💵 عملات رقمية", callback_data="dep_crypto")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_withdrawal_methods_keyboard():
    """لوحة خيارات السحب"""
    keyboard = [
        [InlineKeyboardButton("💻 شام كاش ليرة", callback_data="with_sham_lira"), InlineKeyboardButton("💼 شام كاش دولار", callback_data="with_sham_dollar")],
        [InlineKeyboardButton("💼 سيرتل كاش", callback_data="with_sertel")],
        [InlineKeyboardButton("💵 عملات رقمية", callback_data="with_crypto")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_settings_keyboard():
    """لوحة التعديلات للأدمن"""
    keyboard = [
        [InlineKeyboardButton("🐵 مكافآت الإيداع", callback_data="admin_bonus_settings"), InlineKeyboardButton("💵 سعر الصرف", callback_data="admin_set_rate")],
        [InlineKeyboardButton("💵 رصيد الكاشير", callback_data="admin_cashier")],
        [InlineKeyboardButton("🎆 عمولة السحب", callback_data="admin_referral_settings"), InlineKeyboardButton("📓 بيانات الدفع المحلي", callback_data="admin_local_payment_settings")],
        [InlineKeyboardButton("👥 عرض المستخدمين", callback_data="admin_show_users")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(callback_data="main_menu"):
    """لوحة رجوع فقط"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=callback_data)]])


# ==================== أوامر البوت ====================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid != ADMIN_ID and not is_bot_active():
        msg = get_bot_status_message()
        await update.message.reply_text(msg or "البوت غير متاح حالياً.")
        return

    if not is_user_registered(uid):
        terms_text = (
            "📐 **الشروط والأحكام**\n\n"
            'بالضغط على "موافقة" فأنت توافق على مجموعة الشروط والأحكام التالية لهذا البوت. يرجى القراءة بعناية قبل الاستمرار.\n\n'
            "1- يتحمل المستخدم مسؤولية كاملة عن بيانات حسابه والمحافظة عليها وعدم مشاركتها.\n"
            "2- يتحمل المستخدم تبعات استخدام أي من وسائل الدفع، مثل تحويل مبالغ لعنوان خاطئ أو لأي شخص آخر.\n"
            "3- أي محاولة للغش أو التلاعب أو استغلال الثغرات ستؤدي إلى حظر الحساب بشكل دائم.\n"
            "4- يجب إدخال بيانات التحويل بشكل صحيح.\n"
            "5- لا يتم إرجاع أي عملية بعد الانتهاء منها.\n"
            "6- أول إيداع يحصل على مكافأة 10%، والإيداعات التالية 5%.\n\n"
            "🕷️ أي مخالفة للشروط ستؤدي إلى حظر الحساب وإلغاء الرصيد."
        )
        await update.message.reply_text(
            terms_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ موافق", callback_data="agree_terms")]]),
        )
    else:
        await update.message.reply_text(
            "🦮 **أهلاً بك في بوت طروادة!**\n\nاختر القائمة المناسبة:",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(uid),
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر المساعدة"""
    await update.message.reply_text(
        "💒 **المساعدة**\n\n"
        "للاستفسار والدعم:\n"
        "@TroyawinAdmin\n\n"
        "للمساعدة السريعة، يمكنك:\n"
        "• استعراض القائمة الرئيسية للوصول إلى جميع الخيارات\n"
        "• مراجعة الشروط والأحكام للتأكد من عدم الغش\n"
        "• التواصل معنا في أي وقت",
        parse_mode="Markdown",
    )


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر سياسة الخصوصية"""
    await update.message.reply_text(
        "📵 **سياسة الخصوصية والبيانات**\n\n"
        "نحن نلتزم بحماية بياناتك وخصوصيتك.\n\n"
        "1. **مجموعة البيانات:**\n"
        "   نقوم بتخزين البيانات الأساسية فقط (ID التلغرام، اسم المستخدم)\n\n"
        "2. **استخدام البيانات:**\n"
        "   نستخدم البيانات لتنفيذ العمليات المالية وإدارة الحساب\n\n"
        "3. **حماية البيانات:**\n"
        "   نستخدم إجراءات أمنية لحماية معلوماتك\n\n"
        "4. **مشاركة البيانات:**\n"
        "   لا نشارك بياناتك مع أي طرف ثالث\n\n"
        "5. **حقوقك:**\n"
        "   يمكنك طلب حذف حسابك وبياناتك في أي وقت\n\n"
        "للاستفسار الخصوصية:\n"
        "@TroyawinAdmin",
        parse_mode="Markdown",
    )


# ==================== دوال مساعدة للواجهة الأساسية ====================


async def admin_show_local_payment_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إعدادات بيانات الدفع المحلي"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()

    msg = (
        f"📓 **إعدادات بيانات الدفع المحلي**\n\n"
        f"💼 **سيرتل كاش (عملة رئيسية):**\n"
        f"   الرقم: `{addresses['sertel_cash_1']}`\n\n"
        f"💻 **شام كاش ليرة:**\n"
        f"   الرقم: `{addresses['sham_lira_1']}`\n\n"
        f"💼 **شام كاش دولار:**\n"
        f"   الرقم: `{addresses['sham_dollar_1']}`\n\n"
        f"💵 **عنوان المحفظة الرقمية (USDT TRC20):**\n"
        f"   `{addresses['usdt_trc20_address']}`\n\n"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل رقم سيرتل كاش", callback_data="edit_sertel_numbers")],
        [InlineKeyboardButton("✏️ تعديل رقم شام كاش ليرة", callback_data="edit_sham_lira_numbers")],
        [InlineKeyboardButton("✏️ تعديل رقم شام كاش دولار", callback_data="edit_sham_dollar_numbers")],
        [InlineKeyboardButton("✏️ تعديل عنوان المحفظة الرقمية", callback_data="edit_usdt_address")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def admin_show_local_payment_settings_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إعدادات بيانات الدفع المحلي مباشرة"""
    addresses = get_wallet_addresses()

    msg = (
        f"📓 **إعدادات بيانات الدفع المحلي**\n\n"
        f"💼 **سيرتل كاش (عملة رئيسية):**\n"
        f"   الرقم: `{addresses['sertel_cash_1']}`\n\n"
        f"💻 **شام كاش ليرة:**\n"
        f"   الرقم: `{addresses['sham_lira_1']}`\n\n"
        f"💼 **شام كاش دولار:**\n"
        f"   الرقم: `{addresses['sham_dollar_1']}`\n\n"
        f"💵 **عنوان المحفظة الرقمية (USDT TRC20):**\n"
        f"   `{addresses['usdt_trc20_address']}`\n\n"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل رقم سيرتل كاش", callback_data="edit_sertel_numbers")],
        [InlineKeyboardButton("✏️ تعديل رقم شام كاش ليرة", callback_data="edit_sham_lira_numbers")],
        [InlineKeyboardButton("✏️ تعديل رقم شام كاش دولار", callback_data="edit_sham_dollar_numbers")],
        [InlineKeyboardButton("✏️ تعديل عنوان المحفظة الرقمية", callback_data="edit_usdt_address")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def admin_edit_sertel_numbers_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدخال رقم سيرتل كاش الجديد"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()

    await query.edit_message_text(
        f"✏️ **تعديل رقم سيرتل كاش**\n\n"
        f"الرقم الحالي: `{addresses['sertel_cash_1']}`\n\n"
        f"💼 الرجاء إدخال الرقم الجديد\n\n"
        f"أدخل الرقم الجديد:",
        parse_mode="Markdown",
    )
    return ADMIN_EDIT_SERTEL


async def admin_sertel_numbers_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رقم سيرتل كاش الجديد"""
    number = update.message.text.strip()

    if not number:
        await update.message.reply_text("❌ لا يمكن ترك الحقل فارغاً. أدخل الرقم:")
        return ADMIN_EDIT_SERTEL

    if not number.isdigit():
        await update.message.reply_text("❌ الرقم يجب أن يحتوي أرقاماً فقط:")
        return ADMIN_EDIT_SERTEL

    update_wallet_addresses(sertel_cash_1=number, sertel_cash_2=number)

    await update.message.reply_text(
        f"✅ **تم تحديث رقم سيرتل كاش بنجاح!**\n\nالرقم الجديد: `{number}`\n",
        parse_mode="Markdown",
        reply_markup=get_admin_settings_keyboard(),
    )
    return ConversationHandler.END


async def admin_edit_crypto_wallet_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدخال عنوان المحفظة الرقمية الجديد"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()

    await query.edit_message_text(
        f"✏️ **تعديل عنوان المحفظة الرقمية (USDT TRC20)**\n\n"
        f"العنوان الحالي:\n`{addresses['usdt_trc20_address']}`\n\n"
        f"أدخل العنوان الجديد:",
        parse_mode="Markdown",
    )
    return ADMIN_EDIT_CRYPTO_WALLET


async def admin_crypto_wallet_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام عنوان المحفظة الرقمية الجديد"""
    wallet_address = update.message.text.strip()

    if not wallet_address:
        await update.message.reply_text("❌ لا يمكن ترك الحقل فارغاً. أدخل العنوان:")
        return ADMIN_EDIT_CRYPTO_WALLET

    if len(wallet_address) < 10:
        await update.message.reply_text("❌ العنوان قصير جداً:")
        return ADMIN_EDIT_CRYPTO_WALLET

    update_wallet_addresses(usdt_trc20_address=wallet_address)

    await update.message.reply_text(
        f"✅ **تم تحديث عنوان المحفظة الرقمية بنجاح!**\n\nالعنوان الجديد:\n`{wallet_address}`\n",
        parse_mode="Markdown",
        reply_markup=get_admin_settings_keyboard(),
    )
    return ConversationHandler.END


async def admin_edit_sham_lira_numbers_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدخال رقم شام كاش ليرة الجديد"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()

    await query.edit_message_text(
        f"✏️ **تعديل رقم شام كاش ليرة**\n\n"
        f"الرقم الحالي: `{addresses['sham_lira_1']}`\n\n"
        f"أدخل الرقم الجديد:",
        parse_mode="Markdown",
    )
    return ADMIN_EDIT_SHAM_LIRA


async def admin_sham_lira_numbers_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رقم شام كاش ليرة الجديد"""
    number = update.message.text.strip()

    if not number:
        await update.message.reply_text("❌ لا يمكن ترك الحقل فارغاً. أدخل الرقم:")
        return ADMIN_EDIT_SHAM_LIRA

    update_wallet_addresses(sham_lira_1=number, sham_lira_2=number)

    await update.message.reply_text(
        f"✅ **تم تحديث رقم شام كاش ليرة بنجاح!**\n\nالرقم الجديد: `{number}`\n",
        parse_mode="Markdown",
        reply_markup=get_admin_settings_keyboard(),
    )
    return ConversationHandler.END


async def admin_edit_sham_dollar_numbers_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدخال رقم شام كاش دولار الجديد"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()

    await query.edit_message_text(
        f"✏️ **تعديل رقم شام كاش دولار**\n\n"
        f"الرقم الحالي: `{addresses['sham_dollar_1']}`\n\n"
        f"أدخل الرقم الجديد:",
        parse_mode="Markdown",
    )
    return ADMIN_EDIT_SHAM_DOLLAR


async def admin_sham_dollar_numbers_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رقم شام كاش دولار الجديد"""
    number = update.message.text.strip()

    if not number:
        await update.message.reply_text("❌ لا يمكن ترك الحقل فارغاً. أدخل الرقم:")
        return ADMIN_EDIT_SHAM_DOLLAR

    update_wallet_addresses(sham_dollar_1=number, sham_dollar_2=number)

    await update.message.reply_text(
        f"✅ **تم تحديث رقم شام كاش دولار بنجاح!**\n\nالرقم الجديد: `{number}`\n",
        parse_mode="Markdown",
        reply_markup=get_admin_settings_keyboard(),
    )
    return ConversationHandler.END


# ==================== عرض المستخدمين ====================


async def admin_show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة المستخدمين المسجلين"""
    query = update.callback_query
    await query.answer()

    users = get_all_users()
    user_count = get_user_count()

    if not users:
        msg = "👥 <b>المستخدمين المسجلين</b>\n\n❌ لا يوجد مستخدمين مسجلين حالياً."
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_back_keyboard("admin_settings_menu"))
        return

    users_to_show = users[:10]

    msg = f"👥 <b>المستخدمين المسجلين</b> ({user_count} مستخدم)\n\n"
    msg += f"عرض أول {len(users_to_show)} مستخدمين:\n\n"

    for user in users_to_show:
        telegram_id = user["telegram_id"]
        username = user["username"]
        ichancy_username = user["ichancy_username"]
        seq_num = user["sequence_number"]
        created_at = user["created_at"]

        msg += f"💍 <b>{ichancy_username}</b>\n"
        msg += f"   👤 الاسم الظاهر: <code>{username}</code>\n"
        msg += f"   📫 Telegram ID: <code>{telegram_id}</code>\n"
        msg += f"   🔢 الرقم التسلسلي: {seq_num}\n"
        msg += f"   📮 تاريخ التسجيل: <code>{created_at}</code>\n\n"

    if len(users) > 10:
        msg += f"... و {len(users) - 10} مستخدم آخر\n"

    msg += "\n💡 للمزيد من التفاصيل، راجع قاعدة البيانات مباشرة"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")]])

    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=keyboard)


async def admin_show_users_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المستخدمين مباشرة"""
    users = get_all_users()
    user_count = get_user_count()

    if not users:
        msg = "👥 <b>المستخدمين المسجلين</b>\n\n❌ لا يوجد مستخدمين مسجلين حالياً."
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=get_back_keyboard("admin_settings_menu"))
        return

    users_to_show = users[:10]

    msg = f"👥 <b>المستخدمين المسجلين</b> ({user_count} مستخدم)\n\n"
    msg += f"عرض أول {len(users_to_show)} مستخدمين:\n\n"

    for user in users_to_show:
        telegram_id = user["telegram_id"]
        username = user["username"]
        ichancy_username = user["ichancy_username"]
        seq_num = user["sequence_number"]
        created_at = user["created_at"]

        msg += f"💍 <b>{ichancy_username}</b>\n"
        msg += f"   👤 الاسم الظاهر: <code>{username}</code>\n"
        msg += f"   📫 Telegram ID: <code>{telegram_id}</code>\n"
        msg += f"   🔢 الرقم التسلسلي: {seq_num}\n"
        msg += f"   📮 تاريخ التسجيل: <code>{created_at}</code>\n\n"

    if len(users) > 10:
        msg += f"... و {len(users) - 10} مستخدم آخر\n"

    msg += "\n💡 للمزيد من التفاصيل، راجع قاعدة البيانات مباشرة"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")]])

    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    if not is_bot_active() and uid != ADMIN_ID:
        msg = get_bot_status_message()
        await query.edit_message_text(msg or "البوت غير متاح حالياً.")
        return

    if data == "main_menu":
        try:
            await query.edit_message_text(
                "🦮 **أهلاً بك في بوت طروادة**\n\nاختر القائمة المناسبة:",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(uid),
            )
        except Exception as e:
            logger.error(f"Error showing main menu for user {uid}: {e}")
            await query.message.reply_text(
                "🦮 **أهلاً بك في بوت طروادة**\n\nاختر القائمة المناسبة:",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(uid),
            )

    elif data == "my_account_menu":
        await show_my_account_info(update, context, query)

    elif data == "account_info":
        await show_account_info_detail(update, context, query)

    elif data == "trojan_menu":
        await query.edit_message_text(
            "🐵 **طروادة**\n\nاختر الخدمات المناسبة:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎟️ استلام رصيد هدية", callback_data="redeem_gift_code")],
                [InlineKeyboardButton("🎯 تحويل رصيد هدية", callback_data="create_gift_code")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
            ]),
        )

    elif data == "request_delete_account":
        await request_delete_account(update, context)

    elif data == "confirm_delete_account":
        await confirm_delete_account_final(update, context, query)

    elif data == "offers_bonuses":
        await query.edit_message_text(
            "🐵 **العروض والمكافآت**\n\n"
            "✅ أول إيداع: +10% مكافأة\n"
            "🔧 الإيداعات التالية: +5% مكافأة\n"
            "🎀 عروض خاصة للمناسبات القادمة\n\n"
            "ترقبوا للحصول على آخر العروض!",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard(),
        )

    elif data == "deposit_menu":
        await query.edit_message_text(
            "💵 **اختر طريقة الإيداع:**",
            parse_mode="Markdown",
            reply_markup=get_deposit_methods_keyboard(),
        )

    elif data == "withdraw_menu":
        await query.edit_message_text(
            "💳 **اختر طريقة السحب:**",
            parse_mode="Markdown",
            reply_markup=get_withdrawal_methods_keyboard(),
        )

    elif data == "create_gift_code":
        await gift_transfer_start(update, context)
        return GIFT_TRANSFER_USERNAME

    elif data == "redeem_gift_code":
        await redeem_gift_code_start(update, context)
        return GIFT_REDEEM_CODE

    elif data == "history":
        await show_history(update, context, query)

    elif data == "how_it_works":
        await query.edit_message_text(
            "📉 **كيفية العمل**\n\n"
            "1️⃣ **الإيداع:** اختر طريقة الإيداع المناسبة وأرسل المبلغ\n"
            "2️⃣ **اللعب:** انتقل إلى الألعاب مباشرة من القائمة\n"
            "3️⃣ **السحب:** اطلب السحب من خلال الدعم\n\n"
            "📓 للمساعدة: تواصل معنا",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard(),
        )

    elif data == "contact_us":
        await query.edit_message_text(
            "💒 **الدعم الفني**\n\nللاستفسار والدعم:\n@TroyawinAdmin",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard(),
        )

    elif data == "games_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚽ الألعاب السريعة", callback_data="games_quick")],
            [InlineKeyboardButton("🦦 لعبة الشجرة", callback_data="tree_game")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
        ])
        await query.edit_message_text(
            "🎃 **قائمة الألعاب**\n\nاختر اللعبة:",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif data == "games_quick":
        await query.edit_message_text(
            "⚽ **الألعاب السريعة**\n\nانقر على الرابط للوصول مباشرة للألعاب السريعة:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎃 الدخول للألعاب السريعة", url="https://www.ichancy.com/ar/for-test")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")],
            ]),
        )

    elif data == "tree_game":
        await query.edit_message_text(
            "🦦 **لعبة الشجرة**\n\nانقر على الرابط للوصول مباشرة للعبة:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎃 الدخول للعبة الشجرة", url="https://www.ichancy.com/ar/for-test/slots/all/36/77613?preview=true")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")],
            ]),
        )

    elif data == "games_top_earning":
        await query.edit_message_text(
            "⚽ **الألعاب السريعة**\n\nانقر على الرابط للوصول:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎃 الدخول للألعاب", url="https://www.ichancy.com/ar/for-test")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")],
            ]),
        )

    elif data == "games_favorites":
        await query.edit_message_text(
            "⚽ **الألعاب السريعة**\n\nانقر على الرابط للوصول:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎃 الدخول للألعاب", url="https://www.ichancy.com/ar/for-test")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")],
            ]),
        )

    elif data == "sports_betting":
        await query.edit_message_text(
            "⚽ **الألعاب السريعة**\n\nانقر على الرابط للوصول:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎃 الدخول للألعاب", url="https://www.ichancy.com/ar/for-test")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
            ]),
        )

    elif data == "coupons_menu":
        await query.edit_message_text(
            "🎟️ **الكوبونات الترويجية**\n\n"
            "💡 الكوبونات تسمح لك بالحصول على مكافآت سريعة!\n\n"
            "اختر الكوبون المناسب لك:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🐵 مكافأة ترحيبية", callback_data="coupon_welcome")],
                [InlineKeyboardButton("🎀 مكافأة هدية", callback_data="coupon_gift")],
                [InlineKeyboardButton("🎟 مكافأة إيداع", callback_data="coupon_deposit")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
            ]),
        )

    elif data == "invite_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📫 دعوة عبر تلغرام", callback_data="invite_telegram")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
        ])
        await query.edit_message_text(
            "👥 **دعوة الأصدقاء**\n\n"
            "ادع أصدقائك واربح مع كل مستخدم جديد!\n\n"
            "اختر طريقة الدعوة:",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif data == "invite_telegram":
        await query.edit_message_text(
            "👥 **دعوة عبر تلغرام**\n\n"
            "أدخل اسم المستخدم (username) في تلغرام لدعوته\n"
            "مثال: @ahmad_khaled",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard("invite_menu"),
        )
        return INVITE_USERNAME

    elif data == "coupon_welcome":
        await coupon_welcome(update, context)
    elif data == "coupon_gift":
        await coupon_gift(update, context)
    elif data == "coupon_deposit":
        await coupon_deposit(update, context)

    elif data == "message_admin":
        await query.edit_message_text(
            "📠 **إرسال رسالة**\n\n"
            "يمكنك إرسال رسالتك مباشرة إلى الأدمن.\n"
            "أرسل رسالتك الآن...",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard(),
        )

    elif data == "ichancy_apk":
        await query.edit_message_text(
            "📫 **تحميل ابليكاشن**\n\n"
            "لتحميل ابليكاشن للهواتف المحمولة\n\n"
            "انقر على الرابط للتحميل:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("猬囷笍 تحميل التطبيق", url="https://android.betcoapps.com/novichok/ichancy_com/ichancy_com.apk")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
            ]),
        )

    elif data == "terms_conditions":
        await query.edit_message_text(
            "📵 **الشروط والأحكام**\n\n"
            'بالضغط على "موافقة" فأنت توافق على مجموعة الشروط والأحكام التالية لهذا البوت. يرجى القراءة بعناية قبل الاستمرار.\n\n'
            "1- يتحمل المستخدم مسؤولية كاملة عن بيانات حسابه والمحافظة عليها وعدم مشاركتها.\n"
            "2- يتحمل المستخدم تبعات استخدام أي من وسائل الدفع، مثل تحويل مبالغ لعنوان خاطئ أو لأي شخص آخر.\n"
            "3- أي محاولة للغش أو التلاعب أو استغلال الثغرات ستؤدي إلى حظر الحساب بشكل دائم.\n"
            "4- يجب إدخال بيانات التحويل بشكل صحيح.\n"
            "5- لا يتم إرجاع أي عملية بعد الانتهاء منها.\n"
            "6- أول إيداع يحصل على مكافأة 10%، والإيداعات التالية 5%.\n\n"
            "🕷️ أي مخالفة للشروط ستؤدي إلى حظر الحساب وإلغاء الرصيد.",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard(),
        )

    elif data == "dep_sertel":
        context.user_data["pending_method"] = "سيرتل كاش"
        addresses = get_wallet_addresses()
        await show_local_deposit_info(update, context, query, "سيرتل كاش", [addresses["sertel_cash_1"]], has_cancel=False)

    elif data == "dep_sham_lira":
        context.user_data["pending_method"] = "شام كاش ليرة"
        addresses = get_wallet_addresses()
        await show_local_deposit_info(update, context, query, "شام كاش ليرة", [addresses["sham_lira_1"]], has_cancel=False)

    elif data == "dep_sham_dollar":
        context.user_data["pending_method"] = "شام كاش دولار"
        addresses = get_wallet_addresses()
        await show_local_deposit_info(update, context, query, "شام كاش دولار", [addresses["sham_dollar_1"]], has_cancel=True)

    elif data == "dep_crypto":
        await start_crypto_deposit(update, context)
        return

    elif data == "dep_binance":
        await start_binance_pay_deposit(update, context)
        return

    elif data == "admin_settings_auth":
        if uid == ADMIN_ID:
            await admin_settings_auth_entry(update, context)

    elif data == "admin_settings_menu":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await query.edit_message_text(
                    "⚙️ **التعديلات**\n\nاختر القائمة:",
                    parse_mode="Markdown",
                    reply_markup=get_admin_settings_keyboard(),
                )
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_settings_logout":
        if uid == ADMIN_ID:
            context.user_data["admin_authenticated"] = False
            await query.edit_message_text(
                "🔐 **تم تسجيل الخروج**",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(uid),
            )

    elif data == "admin_bonus_settings":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_show_bonus_settings(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_set_subsequent_bonus":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                context.user_data["bonus_type_to_change"] = "subsequent"
                await admin_set_subsequent_bonus_entry(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_set_first_bonus":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                context.user_data["bonus_type_to_change"] = "first"
                await admin_set_first_bonus_entry(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_cashier":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_show_cashier(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_bot_status":
        if uid == ADMIN_ID:
            await admin_show_bot_status(update, context)

    elif data == "admin_set_rate":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_set_rate_entry(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_set_deposit_fee":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_set_deposit_fee_entry(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "edit_rest_message":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_edit_rest_message_entry(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "edit_maintenance_message":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_edit_maintenance_message_entry(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data.startswith("bot_status_"):
        if uid == ADMIN_ID:
            status = data.replace("bot_status_", "")
            set_bot_status(status)
            await admin_show_bot_status(update, context)

    elif data == "admin_referral_settings":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_show_referral_settings(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_payment_methods":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_show_payment_methods(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_show_users":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_show_users(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_local_payment_settings":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_show_local_payment_settings(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data == "admin_pending_deletions":
        if uid == ADMIN_ID:
            if context.user_data.get("admin_authenticated", False):
                await admin_show_pending_deletions(update, context)
            else:
                await admin_settings_auth_entry(update, context)

    elif data.startswith("admin_del_approve_"):
        if uid == ADMIN_ID:
            await admin_approve_deletion(update, context)

    elif data.startswith("admin_del_reject_"):
        if uid == ADMIN_ID:
            await admin_reject_deletion(update, context)

    elif data.startswith("admin_approve_"):
        if uid == ADMIN_ID:
            await admin_approve_entry(update, context)

    elif data.startswith("admin_reject_"):
        if uid == ADMIN_ID:
            await admin_reject_entry(update, context)

    elif data.startswith("admin_withdraw_approve_"):
        if uid == ADMIN_ID:
            await admin_withdraw_approve_entry(update, context)

    elif data.startswith("admin_withdraw_reject_"):
        if uid == ADMIN_ID:
            await admin_withdraw_reject_entry(update, context)

    elif data.startswith("retry_deposit_"):
        if uid == ADMIN_ID:
            await admin_retry_deposit(update, context)

    elif data.startswith("reject_deposit_"):
        if uid == ADMIN_ID:
            await admin_finalize_reject_deposit(update, context)

    elif data == "cancel_deposit":
        await query.edit_message_text("❌ تم إلغاء العملية.", reply_markup=get_main_keyboard(uid))

    elif data == "edit_referral_username":
        if uid == ADMIN_ID:
            await admin_edit_referral_username_entry(update, context)

    elif data == "edit_withdrawal_commission":
        if uid == ADMIN_ID:
            await admin_edit_withdrawal_commission_entry(update, context)

    elif data == "edit_referral_commission":
        if uid == ADMIN_ID:
            await admin_edit_referral_commission_entry(update, context)

    elif data == "manage_deposit_methods":
        if uid == ADMIN_ID:
            await admin_manage_deposit_methods(update, context)

    elif data == "manage_withdrawal_methods":
        if uid == ADMIN_ID:
            await admin_manage_withdrawal_methods(update, context)

    elif data.startswith("toggle_deposit_method_"):
        if uid == ADMIN_ID:
            await admin_toggle_deposit_method(update, context)

    elif data.startswith("toggle_withdrawal_method_"):
        if uid == ADMIN_ID:
            await admin_toggle_withdrawal_method(update, context)

    elif data == "edit_sertel_numbers":
        if uid == ADMIN_ID:
            await admin_edit_sertel_numbers_entry(update, context)

    elif data == "edit_sham_lira_numbers":
        if uid == ADMIN_ID:
            await admin_edit_sham_lira_numbers_entry(update, context)

    elif data == "edit_sham_dollar_numbers":
        if uid == ADMIN_ID:
            await admin_edit_sham_dollar_numbers_entry(update, context)

    elif data == "edit_crypto_wallet":
        if uid == ADMIN_ID:
            await admin_edit_crypto_wallet_entry(update, context)

    elif data == "edit_sertel_cash_1":
        if uid == ADMIN_ID:
            await admin_edit_sertel_cash_1_entry(update, context)

    elif data == "edit_sertel_cash_2":
        if uid == ADMIN_ID:
            await admin_edit_sertel_cash_2_entry(update, context)

    elif data == "edit_sham_lira_1":
        if uid == ADMIN_ID:
            await admin_edit_sham_lira_1_entry(update, context)

    elif data == "edit_sham_lira_2":
        if uid == ADMIN_ID:
            await admin_edit_sham_lira_2_entry(update, context)

    elif data == "edit_sham_dollar_1":
        if uid == ADMIN_ID:
            await admin_edit_sham_dollar_1_entry(update, context)

    elif data == "edit_sham_dollar_2":
        if uid == ADMIN_ID:
            await admin_edit_sham_dollar_2_entry(update, context)

    elif data == "edit_usdt_address":
        if uid == ADMIN_ID:
            await admin_edit_usdt_address_entry(update, context)


# ==================== حسابي وتعديل كلمة السر ====================


async def show_my_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    """عرض معلومات الحساب الكاملة مع اسم المستخدم الأساسي (مع TR)"""
    uid = query.from_user.id
    user = get_user_full(uid)

    if not user:
        await query.edit_message_text("❌ لم يتم العثور على معلومات حسابك.", reply_markup=get_back_keyboard())
        return

    username = user[1] if user[1] else "غير موجود"
    ichancy_username = user[3] if len(user) > 3 and user[3] else "غير موجود"
    created_at = user[6] if len(user) > 6 and user[6] else "غير معروف"
    sequence_num = user[5] if len(user) > 5 and user[5] else None

    final_username = ichancy_username if ichancy_username != "غير موجود" else "غير موجود"

    balance_data = get_wallet_balance(uid)
    balance = balance_data.get("balance", 0)

    ichancy_balance_msg = ""
    if ichancy_username and ichancy_username != "غير موجود":
        try:
            agent = AgentAPI()
            player_id = agent.get_player_id(ichancy_username)
            if player_id:
                ichancy_bal_data = agent.get_balance(player_id)
                if ichancy_bal_data:
                    ichancy_balance = 0
                    for bal in ichancy_bal_data:
                        if isinstance(bal, dict):
                            if "balance" in bal:
                                ichancy_balance = float(bal["balance"])
                                break
                            elif "amount" in bal:
                                ichancy_balance = float(bal["amount"])
                                break

                    if ichancy_balance > 0:
                        ichancy_balance_msg = f"{ichancy_balance:,.2f} NSP"
        except Exception as e:
            print(f"Error fetching Ichancy balance: {e}")

    msg = (
        f"👤 **حسابي**\n\n"
        f"💍 **معلومات تلغرام:** `{uid}`\n"
        f"👤 **اسم المستخدم:** `{final_username}`\n"
        f"💵 **رصيد ابليكاشن:** `{ichancy_balance_msg if ichancy_balance_msg else '0 NSP'}`\n"
        f"📮 **تاريخ التسجيل:** `{created_at}`\n\n"
        f"اختر الخيار المناسب:"
    )

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=get_my_account_keyboard())


async def show_account_info_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    """عرض معلومات الحساب التفصيلية"""
    uid = query.from_user.id
    user = get_user_full(uid)

    if not user:
        await query.edit_message_text("❌ لم يتم العثور على معلومات حسابك.", reply_markup=get_back_keyboard("my_account_menu"))
        return

    username = user[1] if user[1] else "غير موجود"
    ichancy_username = user[3] if len(user) > 3 and user[3] else "غير موجود"
    ichancy_password = user[4] if len(user) > 4 and user[4] else "غير موجود"
    created_at = user[6] if len(user) > 6 and user[6] else "غير معروف"
    sequence_num = user[5] if len(user) > 5 and user[5] else None

    balance_data = get_wallet_balance(uid)
    balance = balance_data.get("balance", 0)
    total_deposited = balance_data.get("total_deposited", 0)
    total_used = balance_data.get("total_used", 0)

    msg = (
        f"⛏️ **معلومات الحساب التفصيلية**\n\n"
        f"💍 **Telegram ID:** `{uid}`\n"
        f"👤 **اسم التلغرام:** `{username}`\n"
        f"🎃 **اسم المستخدم (ابليكاشن):** `{ichancy_username}`\n"
        f"🔑 **كلمة المرور:** `{ichancy_password}`\n"
        f"🔢 **الرقم التسلسلي:** `{sequence_num if sequence_num else 'غير موجود'}`\n\n"
        f"💵 **رصيد المحفظة:**\n"
        f"   الرصيد الحالي: `{balance:,.2f} NSP`\n"
        f"   إجمالي الإيداعات: `{total_deposited:,.2f} NSP`\n"
        f"   إجمالي الاستخدام: `{total_used:,.2f} NSP`\n\n"
        f"📮 **تاريخ التسجيل:** `{created_at}`\n\n"
        f"⚠️ **تنبيه:** احتفظ بمعلومات حسابك في مكان آمن!"
    )

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=get_back_keyboard("my_account_menu"))


async def reset_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية تغيير كلمة السر - بدء عبر query"""
    uid = update.effective_user.id

    context.user_data["reset_pass_uid"] = uid

    await context.bot.send_message(
        chat_id=uid,
        text="🔑 **تغيير كلمة المرور**\n\n"
        "الرجاء إدخال كلمة المرور الجديدة (4 أحرف على الأقل):",
        parse_mode="Markdown",
    )
    return RESET_PASS_NEW


async def reset_password_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام كلمة السر الجديدة"""
    new_pass = update.message.text.strip()
    uid = update.effective_user.id

    if len(new_pass) < 4:
        await update.message.reply_text(
            "❌ كلمة السر قصيرة جداً!\n"
            "يجب أن تحتوي 4 أحرف على الأقل.\n\n"
            "أدخل كلمة سر أخرى:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="my_account_menu")]]),
        )
        return RESET_PASS_NEW

    context.user_data["new_password"] = new_pass

    await update.message.reply_text(
        "🔐 **تأكيد كلمة المرور**\n\nأعد إدخال كلمة المرور الجديدة للتأكيد:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="my_account_menu")]]),
    )
    return RESET_PASS_CONFIRM


async def reset_password_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد كلمة السر الجديدة - عرض رسالة التأكيد"""
    confirm_pass = update.message.text.strip()
    uid = update.effective_user.id

    new_pass = context.user_data.get("new_password")

    if confirm_pass != new_pass:
        await update.message.reply_text(
            "❌ كلمتا السر غير متطابقتان!\n\n"
            "تم إلغاء العملية. انقر /start للبدء مرة أخرى.",
            reply_markup=get_my_account_keyboard(),
        )
        if "new_password" in context.user_data:
            del context.user_data["new_password"]
        if "reset_pass_uid" in context.user_data:
            del context.user_data["reset_pass_uid"]
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ **تأكيد تغيير كلمة المرور**\n\n"
        "أنت على وشك تغيير كلمة المرور الحالية لحسابك.\n\n"
        "⚠️ **تنبيه:** تأكد من حفظ كلمة المرور الجديدة في مكان آمن!\n\n"
        "هل أنت متأكد من تغيير كلمة المرور؟",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، غير كلمة المرور", callback_data="confirm_change_password")],
            [InlineKeyboardButton("❌ لا، تراجع", callback_data="cancel_password_change")],
        ]),
    )
    return RESET_PASS_FINAL_CONFIRM


async def reset_password_final_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التأكيد النهائي وتغيير كلمة المرور"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    new_pass = context.user_data.get("new_password")

    try:
        user = get_user_full(uid)
        if user and len(user) > 3 and user[3]:
            ichancy_username = user[3]
            update_ichancy_credentials(uid, ichancy_username, new_pass)

            await query.edit_message_text(
                f"✅ **تم تغيير كلمة المرور بنجاح!**\n\n"
                f"👤 اسم المستخدم: `{ichancy_username}`\n"
                f"🔑 كلمة المرور الجديدة: `{new_pass}`\n\n"
                f"⚠️ احفظ كلمة المرور في مكان آمن!",
                parse_mode="Markdown",
                reply_markup=get_my_account_keyboard(),
            )
        else:
            await query.edit_message_text("❌ لم يتم العثور على حسابك في النظام.", reply_markup=get_my_account_keyboard())
    except Exception as e:
        print(f"Error resetting password: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء تغيير كلمة المرور.\nحاول مرة أخرى لاحقاً.", reply_markup=get_my_account_keyboard())

    if "new_password" in context.user_data:
        del context.user_data["new_password"]
    if "reset_pass_uid" in context.user_data:
        del context.user_data["reset_pass_uid"]

    return ConversationHandler.END


async def cancel_password_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء تغيير كلمة المرور"""
    query = update.callback_query
    await query.answer()

    if "new_password" in context.user_data:
        del context.user_data["new_password"]
    if "reset_pass_uid" in context.user_data:
        del context.user_data["reset_pass_uid"]

    await query.edit_message_text("❌ تم إلغاء عملية تغيير كلمة المرور.", reply_markup=get_my_account_keyboard())
    return ConversationHandler.END


async def password_change_back_to_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للقائمة الرئيسية من تغيير كلمة المرور"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if "new_password" in context.user_data:
        del context.user_data["new_password"]
    if "reset_pass_uid" in context.user_data:
        del context.user_data["reset_pass_uid"]

    await query.edit_message_text(
        "🦮 **أهلاً بك في بوت طروادة**\n\nاختر القائمة المناسبة:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(uid),
    )
    return ConversationHandler.END


# ==================== دوال إلغاء السحب ====================


async def withdraw_cancel_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء السحب والعودة لقائمة السحب"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if "withdraw_amount" in context.user_data:
        del context.user_data["withdraw_amount"]
    if "withdraw_method" in context.user_data:
        del context.user_data["withdraw_method"]

    await query.edit_message_text("❌ تم إلغاء عملية السحب.", reply_markup=get_withdrawal_methods_keyboard())
    return ConversationHandler.END


async def withdraw_cancel_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء السحب والعودة للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if "withdraw_amount" in context.user_data:
        del context.user_data["withdraw_amount"]
    if "withdraw_method" in context.user_data:
        del context.user_data["withdraw_method"]

    await query.edit_message_text(
        "🦮 **أهلاً بك في بوت طروادة**\n\nاختر القائمة المناسبة:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(uid),
    )
    return ConversationHandler.END


# ==================== دوال إلغاء الإيداع ====================


async def deposit_cancel_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء الإيداع والعودة لقائمة الإيداع"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    await query.edit_message_text("❌ تم إلغاء عملية الإيداع.", reply_markup=get_deposit_methods_keyboard())
    return ConversationHandler.END


async def deposit_cancel_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء الإيداع والعودة للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    await query.edit_message_text(
        "🦮 **أهلاً بك في بوت طروادة**\n\nاختر القائمة المناسبة:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(uid),
    )
    return ConversationHandler.END


# ==================== دوال تحويل الرصيد (تحويل هدية) ====================


async def gift_transfer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية تحويل الرصيد كهدية"""
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    user = get_user_full(uid)
    if not user or len(user) <= 3 or not user[3]:
        await query.edit_message_text("❌ لم يتم العثور على حسابك.\nيرجى التسجيل أولاً.", reply_markup=get_back_keyboard("main_menu"))
        return ConversationHandler.END

    ichancy_username = user[3]

    ichancy_balance = 0
    try:
        agent = AgentAPI()
        player_id = agent.get_player_id(ichancy_username)
        if player_id:
            ichancy_bal_data = agent.get_balance(player_id)
            if ichancy_bal_data:
                for bal in ichancy_bal_data:
                    if isinstance(bal, dict):
                        if "balance" in bal:
                            ichancy_balance = float(bal["balance"])
                            break
                        elif "amount" in bal:
                            ichancy_balance = float(bal["amount"])
                            break
    except Exception as e:
        print(f"Error fetching Ichancy balance: {e}")

    actual_balance = ichancy_balance
    context.user_data["sender_balance"] = actual_balance

    msg = (
        f"🐵 **تحويل هدية (تحويل رصيد)**\n\n"
        f"💵 **رصيدك الحالي في المحفظة:** `{actual_balance:,.2f} NSP`\n\n"
        f"👤 **اسم المستخدم الحالي لك في المحفظة:** `{ichancy_username}`\n\n"
        f"⚠️ **تنبيه مهم:**\n"
        f"يجب إدخال اسم المستخدم في محفظة Ichancy،\n"
        f"وليس اسم المستخدم في تلغرام!\n\n"
        f"📑 **الخطوة 1/2:**\n"
        f"أدخل اسم المستخدم في المحفظة للمستلم:\n"
        f"مثال: `TRahmed123` أو `TR302_Saertab`"
    )

    await query.edit_message_text(msg, parse_mode="Markdown")
    return GIFT_TRANSFER_USERNAME


async def gift_transfer_username_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام اسم المستخدم للمستلم"""
    recipient_username = update.message.text.strip()
    uid = update.effective_user.id

    if not recipient_username:
        await update.message.reply_text("❌ لا يمكن ترك الحقل فارغ.\nأدخل اسم المستخدم في المحفظة:")
        return GIFT_TRANSFER_USERNAME

    sender_user = get_user_full(uid)
    if sender_user and len(sender_user) > 3 and sender_user[3]:
        if recipient_username.lower() == sender_user[3].lower():
            await update.message.reply_text("❌ لا يمكنك تحويل رصيد لنفسك!\nأدخل اسم مستخدم آخر في المحفظة:")
            return GIFT_TRANSFER_USERNAME

    if recipient_username.startswith("@"):
        await update.message.reply_text(
            "❌ هذا اسم مستخدم تلغرام!\n\n"
            "⚠️ يجب إدخال اسم المستخدم في محفظة Ichancy (بدون @).\n"
            f"مثال: `TRahmed123` (مثل اسمك: `{sender_user[3]}`)\n\n"
            "أعد إدخال الاسم الصحيح:"
        )
        return GIFT_TRANSFER_USERNAME

    recipient_user = get_user_by_ichancy_username(recipient_username)
    if not recipient_user:
        await update.message.reply_text(
            f"❌ المستخدم `{recipient_username}` غير موجود في النظام!\n\n"
            f"⚠️ تأكد من:\n"
            f"• إدخال اسم المستخدم في المحفظة (Ichancy)\n"
            f"• عدم إضافة @ قبل الاسم\n"
            f"• صحة الاسم بالكامل\n\n"
            f"مثال صحيح: `TRahmed123` (مثل اسمك: `{sender_user[3]}`)\n\n"
            "أعد إدخال الاسم:"
        )
        return GIFT_TRANSFER_USERNAME

    context.user_data["recipient_username"] = recipient_username
    context.user_data["recipient_telegram_id"] = recipient_user["telegram_id"]

    sender_balance = context.user_data.get("sender_balance", 0)

    msg = (
        f"🐵 **تحويل هدية (تحويل رصيد)**\n\n"
        f"💵 **رصيدك الحالي:** `{sender_balance:,.2f} NSP`\n\n"
        f"👤 **المستلم:** `{recipient_username}`\n"
        f"✅ المستخدم موجود في النظام\n\n"
        f"📑 **الخطوة 2/2:**\n"
        f"أدخل المبلغ الذي تريد تحويله (بالأرقام فقط):\n"
        f"⚠️ الحد الأقصى: `{sender_balance:,.2f} NSP`"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")
    return GIFT_TRANSFER_AMOUNT


async def gift_transfer_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام المبلغ وتحويله"""
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ المبلغ غير صحيح!\nأدخل رقماً صحيحاً:")
        return GIFT_TRANSFER_AMOUNT

    if amount <= 0:
        await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر!\nأدخل المبلغ:")
        return GIFT_TRANSFER_AMOUNT

    uid = update.effective_user.id
    sender_balance = context.user_data.get("sender_balance", 0)
    recipient_username = context.user_data.get("recipient_username")
    recipient_telegram_id = context.user_data.get("recipient_telegram_id")

    if not recipient_username or not recipient_telegram_id:
        await update.message.reply_text("❌ حدث خطأ في البيانات.\nيرجى البدء من جديد.", reply_markup=get_main_keyboard(uid))
        return ConversationHandler.END

    if amount > sender_balance:
        await update.message.reply_text(
            f"❌ رصيدك غير كاف!\n\n"
            f"💵 رصيدك: `{sender_balance:,.2f} NSP`\n"
            f"💼 المبلغ المطلوب: `{amount:,.2f} NSP`\n\n"
            f"العملية ملغية.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(uid),
        )
        return ConversationHandler.END

    sender_user = get_user_full(uid)
    if not sender_user or len(sender_user) <= 3:
        await update.message.reply_text("❌ لم يتم العثور على حسابك.\nالعملية ملغية.", reply_markup=get_main_keyboard(uid))
        return ConversationHandler.END

    sender_ichancy_username = sender_user[3]

    try:
        agent = AgentAPI()

        if amount <= 0:
            await update.message.reply_text(f"❌ المبلغ غير صحيح: `{amount}`\nالعملية ملغية.", parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
            return ConversationHandler.END

        sender_player_id = agent.get_player_id(sender_ichancy_username)
        if not sender_player_id:
            await update.message.reply_text("❌ لم يتم العثور على معلومات اللاعب الحالي في المحفظة!\nيرجى التواصل مع الدعم.", reply_markup=get_main_keyboard(uid))
            return ConversationHandler.END

        sender_real_balance = 0
        try:
            sender_balance_data = agent.get_balance(sender_player_id)
            if sender_balance_data:
                for bal in sender_balance_data:
                    if isinstance(bal, dict):
                        if "balance" in bal:
                            sender_real_balance = float(bal["balance"])
                            break
                        elif "amount" in bal:
                            sender_real_balance = float(bal["amount"])
                            break
        except Exception as e:
            print(f"Error getting sender real balance: {e}")

        if sender_real_balance < amount:
            await update.message.reply_text(
                f"❌ رصيدك الحقيقي في المحفظة غير كاف!\n\n"
                f"💵 رصيدك في المحفظة: `{sender_real_balance:,.2f} NSP`\n"
                f"💼 المبلغ المطلوب: `{amount:,.2f} NSP`\n\n"
                f"⚠️ تأكد من رصيدك المتاح والمعلق في المحفظة.\n"
                f"يرجى تحديث رصيدك أو التواصل مع الدعم.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(uid),
            )
            return ConversationHandler.END

        withdraw_result = agent.withdraw(sender_player_id, amount)
        if not withdraw_result.get("success"):
            await update.message.reply_text(
                f"❌ فشل سحب الرصيد من حسابك!\n\n"
                f"السبب: {withdraw_result.get('message', 'Unknown error')}\n\n"
                f"🔍 معلومات التشخيص:\n"
                f"• Player ID: `{sender_player_id}`\n"
                f"• المبلغ: `{amount:,.2f} NSP`\n"
                f"• الرصيد قبل السحب: `{sender_real_balance:,.2f} NSP`",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(uid),
            )
            return ConversationHandler.END

        recipient_player_id = agent.get_player_id(recipient_username)
        if recipient_player_id:
            deposit_result = agent.deposit(recipient_player_id, amount)
            if not deposit_result.get("success"):
                if sender_player_id:
                    agent.deposit(sender_player_id, amount)
                await update.message.reply_text(
                    f"❌ فشل إيداع الرصيد للمستلم!\nتم استرداد المبلغ لحسابك.",
                    reply_markup=get_main_keyboard(uid),
                )
                return ConversationHandler.END

        deduct_from_wallet(uid, amount, "NSP", notes=f"تحويل هدية إلى {recipient_username}")
        add_to_wallet(recipient_telegram_id, amount, "NSP", notes=f"استلام هدية من {sender_ichancy_username}")

        await update.message.reply_text(
            f"✅ **تم التحويل بنجاح!**\n\n"
            f"💼 **المبلغ المحول:** `{amount:,.2f} NSP`\n"
            f"👤 **من:** `{sender_ichancy_username}`\n"
            f"👤 **إلى:** `{recipient_username}`\n\n"
            f"⚠️ **ملاحظة:** التحويل تم عبر عملية آمنة.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(uid),
        )

        try:
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(
                chat_id=recipient_telegram_id,
                text=(
                    f"🎀 **لقد استلمت هدية!**\n\n"
                    f"💼 **المبلغ:** `{amount:,.2f} NSP`\n"
                    f"👤 **من:** `{sender_ichancy_username}`\n\n"
                    f"تم إضافة المبلغ إلى رصيدك في المحفظة."
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"Error sending notification to recipient: {e}")

    except Exception as e:
        print(f"Error during gift transfer: {e}")
        await update.message.reply_text(
            f"❌ حدث خطأ أثناء التحويل!\nالخطأ: {str(e)}\nيرجى التواصل مع الدعم.",
            reply_markup=get_main_keyboard(uid),
        )

    if "sender_balance" in context.user_data:
        del context.user_data["sender_balance"]
    if "recipient_username" in context.user_data:
        del context.user_data["recipient_username"]

    return ConversationHandler.END


# ==================== استلام رصيد هدية (كود) ====================


async def redeem_gift_code_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية استلام رصيد هدية - المستخدم يدخل الكود فقط"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("🎟️ **استلام رصيد هدية**\n\n💡 أرسل كود الهدية الآن...")
    return GIFT_REDEEM_CODE


async def redeem_gift_code_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام كود الهدية من المستخدم"""
    gift_code = update.message.text.strip()
    uid = update.effective_user.id

    if not gift_code:
        await update.message.reply_text("❌ لا يمكن ترك الكود فارغ.\n💡 أرسل كود الهدية الآن...")
        return GIFT_REDEEM_CODE

    user = get_user_full(uid)
    if not user or len(user) <= 3:
        await update.message.reply_text("❌ لم يتم العثور على حسابك.\nيرجى التسجيل أولاً.", reply_markup=get_main_keyboard(uid))
        return ConversationHandler.END

    username = user[1]
    ichancy_username = user[3] if len(user) > 3 else None

    request_id = create_gift_request(uid, username, ichancy_username, gift_code)

    if request_id is None:
        await update.message.reply_text("⚠️ هذا الكود غير صالح حالياً.\n💡 أرسل كود آخر...", reply_markup=get_main_keyboard(uid))
        return ConversationHandler.END

    try:
        bot = Bot(token=BOT_TOKEN)
        admin_msg = (
            f"🐵 **طلب استلام رصيد هدية جديد!**\n\n"
            f"👤 **المستخدم:** `{username}`\n"
            f"💍 **Telegram ID:** `{uid}`\n"
            f"🎃 **اسم Ichancy:** `{ichancy_username}`\n"
            f"🔑 **كود الهدية:** `{gift_code}`\n"
            f"📮 **التاريخ:** `{update.message.date.strftime('%Y-%m-%d %H:%M')}`\n\n"
            f"للموافقة على الطلب، أرسل: `/gift_approve {request_id} <المبلغ>`\n"
            f"للرفض، أرسل: `/gift_reject {request_id}`\n\n"
            f"💡 مثال: `/gift_approve {request_id} 100`"
        )

        await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Error sending notification to admin: {e}")

    await update.message.reply_text(
        f"✅ **تم إرسال طلبك بنجاح!**\n\n"
        f"🔑 **كود الهدية:** `{gift_code}`\n"
        f"💍 **رقم الطلب:** `{request_id}`\n\n"
        f"⏳ سيتم مراجعة طلبك من قبل الإدارة.\n"
        f"💵 سيتم إضافة الرصيد لحسابك بعد الموافقة.\n\n"
        f"يرجى الانتظار...",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(uid),
    )

    return ConversationHandler.END


# ==================== أوامر الأدمن لطلبات الهدايا ====================


async def admin_gift_approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر الأدمن للموافقة على طلب هدية وإضافتها لحساب المستخدم في Ichancy"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للأدمن فقط!")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ الاستخدام الصحيح:\n"
            "/gift_approve <رقم_الطلب> <المبلغ>\n\n"
            "مثال: /gift_approve 123 100"
        )
        return

    try:
        request_id = int(context.args[0])
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ رقم الطلب والمبلغ يجب أن تكون أرقاماً!\nمثال: /gift_approve 123 100")
        return

    if amount <= 0:
        await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر!")
        return

    result = approve_gift_request(request_id, amount, ADMIN_ID)

    if not result:
        await update.message.reply_text(
            f"❌ فشل الموافقة على الطلب!\n\n"
            f"قد يكون:\n"
            f"• الطلب غير موجود\n"
            f"• الطلب تم معالجته مسبقاً\n"
            f"• رقم الطلب غير صحيح"
        )
        return

    ichancy_username = result.get("ichancy_username")
    ichancy_deposit_success = False
    ichancy_deposit_message = ""

    if ichancy_username and ichancy_username.strip() and ichancy_username != "غير موجود":
        try:
            agent = AgentAPI()
            player_id = agent.get_player_id(ichancy_username)

            if player_id:
                deposit_result = agent.deposit(player_id, amount)
                if deposit_result.get("success"):
                    ichancy_deposit_success = True
                    ichancy_deposit_message = f"✅ تم إضافة {amount:,.2f} NSP لحسابك في المحفظة (Ichancy)"
                else:
                    ichancy_deposit_message = f"⚠️ لم يتم إضافة الرصيد في المحفظة: {deposit_result.get('message', 'Unknown error')}"
            else:
                ichancy_deposit_message = f"⚠️ لم يتم العثور على حسابك في المحفظة (اسم Ichancy: {ichancy_username})"
        except Exception as e:
            ichancy_deposit_message = f"⚠️ خطأ في إضافة الرصيد في المحفظة: {str(e)}"
            print(f"Error depositing to Ichancy: {e}")
    else:
        ichancy_deposit_message = "⚠️ لم يتم العثور على اسم المستخدم في Ichancy"

    try:
        bot = Bot(token=BOT_TOKEN)
        user_message = (
            f"🎀 **تم الموافقة على طلب الهدية!**\n\n"
            f"💵 **المبلغ المضاف:** `{amount:,.2f} NSP`\n"
            f"🔑 **كود الهدية:** `{result['gift_code']}`\n\n"
        )

        if ichancy_deposit_success:
            user_message += f"{ichancy_deposit_message}\n\n"
            user_message += "✅ تمت العملية بنجاح!"
        else:
            user_message += f"{ichancy_deposit_message}\n\n"
            user_message += "💡 تم إضافة الرصيد في محفظة البوت فقط."

        await bot.send_message(chat_id=result["telegram_id"], text=user_message, parse_mode="Markdown")
    except Exception as e:
        print(f"Error sending notification to user: {e}")

    admin_message = (
        f"✅ **تم الموافقة على طلب الهدية بنجاح!**\n\n"
        f"💍 **رقم الطلب:** `{request_id}`\n"
        f"💵 **المبلغ المضاف:** `{amount:,.2f} NSP`\n"
        f"🔑 **كود الهدية:** `{result['gift_code']}`\n\n"
    )

    if ichancy_deposit_success:
        admin_message += f"✅ تم إضافة الرصيد في Ichancy بنجاح\n"
    else:
        admin_message += f"⚠️ {ichancy_deposit_message}\n"

    admin_message += "\nتم إرسال إشعار للمستخدم."

    await update.message.reply_text(admin_message, parse_mode="Markdown")


async def admin_gift_reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر الأدمن لرفض طلب هدية"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للأدمن فقط!")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ الاستخدام الصحيح:\n"
            "/gift_reject <رقم_الطلب> [السبب]\n\n"
            "مثال: /gift_reject 123\n"
            "مثال: /gift_reject 123 كود غير صحيح"
        )
        return

    try:
        request_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ رقم الطلب يجب أن يكون رقماً!\nمثال: /gift_reject 123")
        return

    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "الكود غير صالح"

    result = reject_gift_request(request_id, ADMIN_ID, reason)

    if not result:
        await update.message.reply_text(
            f"❌ فشل رفض الطلب!\n\n"
            f"قد يكون:\n"
            f"• الطلب غير موجود\n"
            f"• الطلب تم معالجته مسبقاً\n"
            f"• رقم الطلب غير صحيح"
        )
        return

    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=result["telegram_id"],
            text=(
                f"❌ **تم رفض طلب الهدية!**\n\n"
                f"🔑 **كود الهدية:** `{result['gift_code']}`\n"
                f"📑 **السبب:** {reason}\n\n"
                f"⚠️ هذا الكود غير صالح، أرسل كود آخر."
            ),
        )
    except Exception as e:
        print(f"Error sending notification to user: {e}")

    await update.message.reply_text(
        f"✅ **تم رفض طلب الهدية!**\n\n"
        f"💍 **رقم الطلب:** `{request_id}`\n"
        f"🔑 **كود الهدية:** `{result['gift_code']}`\n"
        f"📑 **السبب:** {reason}\n\n"
        f"تم إرسال إشعار للمستخدم."
    )


async def admin_gift_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر الأدمن لعرض طلبات الهدايا المعلقة"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للأدمن فقط!")
        return

    requests = get_pending_gift_requests()

    if not requests:
        await update.message.reply_text("📵 **طلبات الهدايا المعلقة**\n\n✅ لا يوجد طلبات معلقة حالياً.")
        return

    msg = "📵 **طلبات الهدايا المعلقة**\n\n"

    for req in requests[:10]:
        msg += (
            f"💍 **رقم الطلب:** {req[0]}\n"
            f"👤 **المستخدم:** `{req[2]}`\n"
            f"🎃 **Ichancy:** `{req[3]}`\n"
            f"🔑 **الكود:** `{req[4]}`\n"
            f"📮 **التاريخ:** {req[8]}\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        )

    if len(requests) > 10:
        msg += f"... و {len(requests) - 10} طلب آخر\n\n"

    msg += (
        f"للموافقة: `/gift_approve <رقم_الطلب> <المبلغ>`\n"
        f"للرفض: `/gift_reject <رقم_الطلب> [السبب]`"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


# ==================== دوال التعديلات ====================


async def admin_settings_auth_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    target = query.data if query.data != "admin_settings_auth" else "admin_settings_menu"
    context.user_data["auth_target"] = target

    await query.edit_message_text("🔐 **الدخول إلى التعديلات**\n\nالرجاء إدخال كلمة السر:", parse_mode="Markdown")
    return ADMIN_AUTH_PASSWORD


async def admin_password_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    uid = update.effective_user.id

    if password == ADMIN_PASSWORD:
        context.user_data["admin_authenticated"] = True
        target = context.user_data.get("auth_target", "admin_settings_menu")

        await update.message.reply_text("✅ **تم التحقق بنجاح!**", parse_mode="Markdown")

        try:
            if target == "admin_settings_menu":
                await update.message.reply_text("⚙️ **التعديلات**\n\nاختر القائمة:", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
            elif target == "admin_bonus_settings":
                await admin_show_bonus_settings_direct(update, context)
            elif target == "admin_cashier":
                await admin_show_cashier_direct(update, context)
            elif target == "admin_bot_status":
                await admin_show_bot_status_direct(update, context)
            elif target == "admin_set_rate":
                await admin_set_rate_entry_direct(update, context)
            elif target == "admin_set_deposit_fee":
                await admin_set_deposit_fee_entry_direct(update, context)
            elif target == "admin_referral_settings":
                await admin_show_referral_settings_direct(update, context)
            elif target == "admin_payment_methods":
                await admin_show_payment_methods_direct(update, context)
            elif target == "admin_show_users":
                await admin_show_users_direct(update, context)
            elif target == "admin_local_payment_settings":
                await admin_show_local_payment_settings_direct(update, context)
            elif target == "admin_pending_deletions":
                await admin_show_pending_deletions_direct(update, context)
            else:
                await update.message.reply_text("⚙️ **التعديلات**\n\nاختر القائمة:", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
        except Exception as e:
            print(f"Error in admin_password_received: {e}")
            await update.message.reply_text("❌ حدث خطأ أثناء فتح التعديلات.", reply_markup=get_main_keyboard(uid))

        if "auth_target" in context.user_data:
            del context.user_data["auth_target"]

        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ **كلمة السر خاطئة!**\n\nتم إلغاء العملية.", parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
        if "auth_target" in context.user_data:
            del context.user_data["auth_target"]
        return ConversationHandler.END


async def admin_show_bonus_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    settings = get_bonus_settings()
    first_bonus = settings.get("first_deposit_bonus", 10.0)
    subsequent_bonus = settings.get("subsequent_deposit_bonus", 5.0)

    msg = (
        f"🐵 **مكافآت الإيداع**\n\n"
        f"✅ أول إيداع: {first_bonus}%\n"
        f"🔧 الإيداعات التالية: {subsequent_bonus}%\n\n"
        f"يمكنك تعديل النسبة:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل نسبة أول إيداع", callback_data="admin_set_first_bonus")],
        [InlineKeyboardButton("✏️ تعديل نسبة الإيداعات التالية", callback_data="admin_set_subsequent_bonus")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def admin_show_bonus_settings_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = get_bonus_settings()
    first_bonus = settings.get("first_deposit_bonus", 10.0)
    subsequent_bonus = settings.get("subsequent_deposit_bonus", 5.0)

    msg = (
        f"🐵 **مكافآت الإيداع**\n\n"
        f"✅ أول إيداع: {first_bonus}%\n"
        f"🔧 الإيداعات التالية: {subsequent_bonus}%\n\n"
        f"يمكنك تعديل النسبة:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل نسبة أول إيداع", callback_data="admin_set_first_bonus")],
        [InlineKeyboardButton("✏️ تعديل نسبة الإيداعات التالية", callback_data="admin_set_subsequent_bonus")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def admin_set_first_bonus_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    settings = get_bonus_settings()
    current_first = settings.get("first_deposit_bonus", 10.0)

    await query.edit_message_text(
        f"🐵 **تعديل نسبة المكافأة لأول إيداع**\n\n"
        f"النسبة الحالية: {current_first}%\n\n"
        f"أدخل النسبة الجديدة (مثال 10 لـ 10%):",
        parse_mode="Markdown",
    )
    return ADMIN_SET_SUBSEQUENT_BONUS


async def admin_set_subsequent_bonus_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    settings = get_bonus_settings()
    current_subsequent = settings.get("subsequent_deposit_bonus", 5.0)

    await query.edit_message_text(
        f"🐵 **تعديل نسبة المكافأة للإيداعات التالية**\n\n"
        f"النسبة الحالية: {current_subsequent}%\n\n"
        f"أدخل النسبة الجديدة (مثال 5 لـ 5%):",
        parse_mode="Markdown",
    )
    return ADMIN_SET_SUBSEQUENT_BONUS


async def admin_bonus_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال أي نسبة مكافأة"""
    try:
        new_bonus = float(update.message.text.strip())
        if new_bonus < 0 or new_bonus > 100:
            await update.message.reply_text("❌ يجب أن تكون النسبة بين 0 و 100.")
            return ADMIN_SET_SUBSEQUENT_BONUS

        bonus_type = context.user_data.get("bonus_type_to_change", "subsequent")

        if bonus_type == "first":
            set_bonus_settings(first_deposit_bonus=new_bonus, admin_id=ADMIN_ID)
            await update.message.reply_text(f"✅ تم تحديث نسبة المكافأة لأول إيداع إلى: {new_bonus}%", reply_markup=get_admin_settings_keyboard())
        else:
            set_bonus_settings(subsequent_bonus=new_bonus, admin_id=ADMIN_ID)
            await update.message.reply_text(f"✅ تم تحديث نسبة المكافأة للإيداعات التالية إلى: {new_bonus}%", reply_markup=get_admin_settings_keyboard())
    except ValueError:
        await update.message.reply_text("❌ رقم غير صحيح. أدخل رقماً صحيحاً:")
        return ADMIN_SET_SUBSEQUENT_BONUS

    return ConversationHandler.END


async def admin_subsequent_bonus_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_bonus = float(update.message.text.strip())
        if new_bonus < 0 or new_bonus > 100:
            await update.message.reply_text("❌ يجب أن تكون النسبة بين 0 و 100.")
            return ADMIN_SET_SUBSEQUENT_BONUS

        set_bonus_settings(subsequent_bonus=new_bonus, admin_id=ADMIN_ID)
        await update.message.reply_text(f"✅ تم تحديث نسبة المكافأة للإيداعات التالية إلى: {new_bonus}%", reply_markup=get_admin_settings_keyboard())
    except ValueError:
        await update.message.reply_text("❌ رقم غير صحيح. أدخل رقماً صحيحاً:")
        return ADMIN_SET_SUBSEQUENT_BONUS

    return ConversationHandler.END


# ==================== التسجيل ====================


async def reg_agree_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ **موافقة!**\n\nأدخل اسم المستخدم (بدون مسافات):")
    return REG_NAME


async def reg_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if " " in name:
        await update.message.reply_text("❌ الاسم لا يجب أن يحتوي على مسافات.")
        return REG_NAME
    if len(name) < 3:
        await update.message.reply_text("❌ الاسم قصير جداً.")
        return REG_NAME

    user_data[update.effective_user.id] = {"reg_name": name}
    await update.message.reply_text("أدخل كلمة السر (يجب أن تحتوي 4 أحرف على الأقل):")
    return REG_PASS


async def reg_pass_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    text_input = update.message.text.strip()

    if not text_input:
        await update.message.reply_text("❌ لا يمكن ترك كلمة السر فارغة.\nيرجى إدخال كلمة سر (4 أحرف على الأقل):")
        return REG_PASS

    if len(text_input) < 4:
        await update.message.reply_text("❌ كلمة السر قصيرة جداً!\nيجب أن تحتوي كلمة السر 4 أحرف على الأقل.\nيرجى المحاولة:")
        return REG_PASS

    password = text_input
    name = user_data.get(uid, {}).get("reg_name")

    if not name:
        return ConversationHandler.END

    import re

    clean_name = re.sub(r"[^a-zA-Z0-9\u0621-\u064A]", "", name)

    if not clean_name or len(clean_name) < 2:
        await update.message.reply_text("❌ الاسم يحتوي على أحرف غير صالحة فقط. أدخل اسم آخر:")
        return REG_NAME

    seq = get_next_sequence_number()
    username_display = f"T{seq}_{clean_name}"

    print(f"📑 الاسم الأصلي: {name}")
    print(f"📑 الاسم بعد التنظيف: {clean_name}")
    print(f"📑 الرقم التسلسلي: {seq}")
    print(f"📑 توليد اسم المستخدم: {username_display}")

    save_user(uid, name, None, sequence_num=seq)

    agent = AgentAPI()
    res = agent.register_player(username_display, password)

    if res.get("success"):
        update_ichancy_credentials(uid, username_display, password)
        msg = f"✅ **تم التسجيل بنجاح!**\n\n👤 اسم الحساب: `{username_display}`\n\n🐵 أول إيداع +10%، الباقي +5%."
    else:
        msg = f"⚠️ تم التسجيل محلياً فقط.\nخطأ: {res.get('error')}"

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
    if uid in user_data:
        del user_data[uid]
    return ConversationHandler.END


# ==================== الإيداع ====================


async def show_local_deposit_info(update: Update, context: ContextTypes.DEFAULT_TYPE, query, method_name, numbers, has_cancel=False):
    if "سيرتل" in method_name or "شام" in method_name:
        header_text = f"🔢 كود الإيداع:\n{numbers[0]}\n\n"
    else:
        nums_text = "\n".join([f"🩸 `{num}`" for num in numbers])
        header_text = f"قم بالتحويل إلى أحد الأرقام:\n{nums_text}\n\n"

    exchange_rate_msg = ""
    if "دولار" in method_name:
        current_rate = get_exchange_rate()
        exchange_rate_msg = f"💵 **سعر الصرف:** كل 1$ = {current_rate} NSP\n\n"

    msg = (
        f"💵 **إيداع {method_name}**\n\n"
        f"{header_text}"
        f"{exchange_rate_msg}"
        f"⚠️ **ملاحظات مهمة:**\n"
        f"بعد التحويل، أرسل كود عملية التحويل فقط.\n"
        f"لا تنسى إدخال المبلغ الذي أرسلته، سيتم تحديده تلقائياً.\n\n"
        f"انقر على ✅ تم التحويل لإرسال كود العملية"
    )
    btns = [[InlineKeyboardButton("✅ تم التحويل", callback_data="confirm_local_deposit")]]
    if has_cancel:
        btns.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_deposit")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="deposit_menu")])

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))
    return ConversationHandler.END


async def start_local_deposit_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("أرسل كود عملية التحويل الآن:")
    return DEP_LOCAL_CODE


async def local_deposit_code_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    if len(code) < 3:
        await update.message.reply_text("❌ كود العملية قصير جداً.")
        return DEP_LOCAL_CODE

    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id FROM pending_deposits WHERE tx_hash = %s OR reference_code = %s", (code, code))
    if c.fetchone():
        conn.close()
        await update.message.reply_text("❌ هذا الكود مستخدم مسبقاً!\n\nيرجى إدخال كود تحويل مختلف.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END

    c.execute("SELECT id FROM wallet_transactions WHERE notes LIKE %s", (f"%Code: {code}%",))
    if c.fetchone():
        conn.close()
        await update.message.reply_text("❌ هذا الكود مستخدم مسبقاً!\n\nيرجى إدخال كود تحويل مختلف.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END

    conn.close()

    user_data[update.effective_user.id] = {"local_code": code}
    method_name = context.user_data.get("pending_method", "غير معروف")

    await update.message.reply_text("⏳ جاري الإرسال إلى الأدمن...")

    uid = update.effective_user.id
    user = get_user_full(uid)

    username = user[1] if user and len(user) > 1 else "Unknown"

    ichancy_username = user[3] if len(user) > 3 and user[3] else "Unknown"
    final_username = ichancy_username if ichancy_username != "Unknown" else "Unknown"

    ichancy_balance, _ = get_ichancy_balance(uid)

    cashier_bal = get_cashier_balance()
    cashier_balance_nsp = cashier_bal.get("balance", 0)
    exchange_rate = get_exchange_rate()

    if "سيرتل" in method_name:
        currency = "LBP"
        cashier_after_fee = cashier_balance_nsp * 0.90
        max_amount_nsp = cashier_after_fee / 100
        max_amount_display = max_amount_nsp
        currency_label = "سيرتل كاش"
        currency_hint = f"أدخل المبلغ بالسيرتل كاش"
    elif "ليرة" in method_name:
        currency = "LBP"
        cashier_after_fee = cashier_balance_nsp * 0.90
        max_amount_nsp = cashier_after_fee / 100
        max_amount_display = max_amount_nsp
        currency_label = "شام كاش ليرة"
        currency_hint = f"أدخل المبلغ بشام كاش ليرة"
    elif "دولار" in method_name:
        currency = "USD"
        max_amount_nsp = cashier_balance_nsp
        max_amount_display = max_amount_nsp / exchange_rate if exchange_rate > 0 else 0
        currency_label = "USD"
        currency_hint = f"أدخل المبلغ بالدولار (سيتم تحويله تلقائياً إلى NSP)"
    else:
        currency = "NSP"
        max_amount_nsp = cashier_balance_nsp
        max_amount_display = max_amount_nsp
        currency_label = "NSP"
        currency_hint = f"أدخل المبلغ بـ NSP"

    admin_msg = (
        f"📈 **إيداع {method_name}**\n"
        f"👤 المستخدم: `{final_username}`\n"
        f"💍 معرف التلغرام: `{username}`\n"
        f"🔢 كود التحويل: `{code}`\n"
        f"💵 **رصيد Ichancy الحقيقي:** `{ichancy_balance:,.2f} NSP`\n\n"
        f"💵 **رصيد الكاشير:** `{cashier_balance_nsp:,.2f} NSP`\n"
        f"⚠️ **الحد الأقصى للإيداع:** `{max_amount_display:,.2f} {currency_label}`\n\n"
        f"{currency_hint}:"
    )

    dep_id = create_pending_deposit(uid, code, 0, method=method_name, currency=currency)

    kb = [[InlineKeyboardButton("✅ موافقة", callback_data=f"admin_approve_{dep_id}")], [InlineKeyboardButton("❌ رفض", callback_data=f"admin_reject_{dep_id}")]]
    try:
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    except:
        pass

    await update.message.reply_text("✅ **تم إرسال كود التحويل بنجاح!**\n\n"
                                    "يرجى الانتظار حتى يقوم الأدمن بالتحقق وإضافة الرصيد.\n"
                                    "سوف يصلك إشعار بعد التأكيد.", reply_markup=get_main_keyboard(uid))

    return ConversationHandler.END


async def start_crypto_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["deposit_type"] = "crypto"

    crypto_wallets = get_crypto_wallet_addresses()
    trc20_address = crypto_wallets.get("trc20", "غير مضبوط")
    erc20_address = crypto_wallets.get("erc20", "غير مضبوط")
    polygon_address = crypto_wallets.get("polygon", "غير مضبوط")
    matic_address = crypto_wallets.get("matic", "غير مضبوط")

    current_rate = get_exchange_rate()

    await query.edit_message_text(
        f"💵 **إيداع عملات رقمية (USDT)**\n\n"
        f"📷 **عنوان TRC20:**\n`{trc20_address}`\n\n"
        f"📷 **عنوان ERC20:**\n`{erc20_address}`\n\n"
        f"📷 **عنوان Polygon:**\n`{polygon_address}`\n\n"
        f"📷 **عنوان Matic:**\n`{matic_address}`\n\n"
        f"💵 **سعر الصرف:** كل 1$ = {current_rate} NSP\n\n"
        f"💡 اختر الشبكة المناسبة وقم بالتحويل\n"
        f"بعد التحويل، أرسل رقم العملية (TxID) للتأكيد:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="deposit_menu")]]),
    )
    return DEP_CRYPTO_TX


async def start_binance_pay_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إيداع Binance Pay"""
    query = update.callback_query
    await query.answer()

    context.user_data["deposit_type"] = "binance"

    binance_settings = get_binance_pay_settings()
    email_address = binance_settings.get("email_address", "aboahmad4si4@gmail.com")
    pay_id = binance_settings.get("pay_id", "3217642")

    current_rate = get_exchange_rate()

    await query.edit_message_text(
        f"🪙 **إيداع Binance Pay**\n\n"
        f"📧 **عنوان البريد:**\n`{email_address}`\n\n"
        f"💍 **ID:**\n`{pay_id}`\n\n"
        f"💵 **سعر الصرف:** كل 1$ = {current_rate} NSP\n\n"
        f"بعد التحويل، أرسل رقم العملية (TxID) للتأكيد:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="deposit_menu")]]),
    )
    return DEP_CRYPTO_TX


async def crypto_tx_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tx = update.message.text.strip()
    if len(tx) < 3:
        await update.message.reply_text("❌ رقم العملية قصير جداً. أدخل رقماً صحيحاً:")
        return DEP_CRYPTO_TX

    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id FROM pending_deposits WHERE tx_hash = %s OR reference_code = %s", (tx, tx))
    if c.fetchone():
        conn.close()
        await update.message.reply_text("❌ هذا الكود مستخدم مسبقاً!\n\nيرجى إدخال كود تحويل مختلف.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END

    c.execute("SELECT id FROM wallet_transactions WHERE notes LIKE %s", (f"%Code: {tx}%",))
    if c.fetchone():
        conn.close()
        await update.message.reply_text("❌ هذا الكود مستخدم مسبقاً!\n\nيرجى إدخال كود تحويل مختلف.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END

    conn.close()

    uid = update.effective_user.id

    cashier_bal = get_cashier_balance()
    cashier_balance = cashier_bal.get("balance", 0)

    exchange_rate = get_exchange_rate()

    max_amount_usd = cashier_balance / exchange_rate if exchange_rate > 0 else 0

    ichancy_balance, _ = get_ichancy_balance(uid)

    user = get_user_full(uid)
    username = user[1] if user else "Unknown"
    ichancy_username = user[3] if len(user) > 3 and user[3] else "Unknown"

    deposit_type = context.user_data.get("deposit_type", "crypto")

    dep_id = create_pending_deposit(uid, tx, 0, method=deposit_type, currency="USD")

    admin_msg = (
        f"📈 **إيداع {'Binance Pay' if deposit_type == 'binance' else 'رقمي'}**\n\n"
        f"👤 المستخدم: `{username}`\n"
        f"💍 معرف التلغرام: `{username}`\n"
        f"🎃 اسم المستخدم: `{ichancy_username}`\n"
        f"💵 **رصيد Ichancy الحقيقي:** `{ichancy_balance:,.2f} NSP`\n"
        f"💵 **رصيد الكاشير:** `{cashier_balance:,.2f} NSP`\n"
        f"⚠️ **الحد الأقصى للموافقة:** `{max_amount_usd:,.2f} USD`\n\n"
        f"🔢 رقم العملية: `{tx[:15]}...`\n\n"
        f"يرجى إدخال المبلغ بالدولار (سيتم تحويله تلقائياً إلى NSP):"
    )

    kb = [[InlineKeyboardButton("✅ موافقة", callback_data=f"admin_approve_{dep_id}")], [InlineKeyboardButton("❌ رفض", callback_data=f"admin_reject_{dep_id}")]]
    try:
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    except:
        pass

    await update.message.reply_text("✅ **تم إرسال رقم العملية بنجاح!**\n\n"
                                    "يرجى الانتظار حتى يقوم الأدمن بالتحقق وإضافة الرصيد.\n"
                                    "سوف يصلك إشعار بعد التأكيد.", reply_markup=get_main_keyboard(uid))

    return ConversationHandler.END


async def crypto_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount_usd = float(update.message.text.strip())
        if amount_usd <= 0:
            raise ValueError
    except:
        await update.message.reply_text("❌ مبلغ غير صحيح.")
        return DEP_CRYPTO_AMOUNT

    uid = update.effective_user.id
    tx = user_data[uid]["crypto_tx"]

    cashier_bal = get_cashier_balance()
    cashier_balance = cashier_bal.get("balance", 0)

    amount_nsp = amount_usd * get_exchange_rate()
    exchange_rate = get_exchange_rate()

    ichancy_balance, _ = get_ichancy_balance(uid)

    max_amount_usd = cashier_balance / exchange_rate if exchange_rate > 0 else 0

    if amount_nsp > cashier_balance:
        user = get_user_full(uid)
        username = user[1] if user else "Unknown"

        admin_msg = (
            f"⚠️ **تنبيه: رصيد الكاشير غير كافٍ!**\n\n"
            f"👤 المستخدم: `{username}`\n"
            f"💍 معرف التلغرام: `{username}`\n"
            f"💵 مبلغ الإيداع المطلوب: `{amount_nsp:,.2f} NSP` (${amount_usd:,.2f})\n"
            f"💵 **رصيد Ichancy الحقيقي:** `{ichancy_balance:,.2f} NSP`\n"
            f"🔄 رصيد الكاشير الحالي: `{cashier_balance:,.2f} NSP`\n"
            f"⚠️ **الحد الأقصى للموافقة:** `{max_amount_usd:,.2f} USD`\n"
            f"❌ الفرق: `{(amount_nsp - cashier_balance):,.2f} NSP`\n\n"
            f"يرجى شحن رصيد الكاشير قبل الموافقة على هذا الإيداع."
        )

        try:
            await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error sending to admin: {e}")

        dep_id = create_pending_deposit(uid, tx, amount_usd, method="crypto", currency="USD")

        await update.message.reply_text(
            f"⏳ **تم استلام طلب الإيداع**\n\n"
            f"💼 المبلغ: `${amount_usd:,.2f}`\n"
            f"💵 مقابل NSP: `{amount_nsp:,.2f} NSP`\n\n"
            f"يرجى الانتظار حتى يتم شحن رصيد الكاشير والموافقة...",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(uid),
        )

        user = get_user_full(uid)
        username = user[1] if user else "Unknown"
        admin_msg = (
            f"📈 إيداع رقمي (انتظار شحن رصيد الكاشير)\n"
            f"👤 {username}\n"
            f"💼 ${amount_usd} (≈{amount_nsp:,.2f} NSP)\n"
            f"💵 **رصيد Ichancy الحقيقي:** `{ichancy_balance:,.2f} NSP`\n"
            f"🔄 **رصيد الكاشير:** `{cashier_balance:,.2f} NSP`\n"
            f"⚠️ **الحد الأقصى للموافقة:** `{max_amount_usd:,.2f} USD`\n"
            f"Tx: `{tx[:15]}...`"
        )
        kb = [[InlineKeyboardButton("✅ موافقة", callback_data=f"admin_approve_{dep_id}")], [InlineKeyboardButton("❌ رفض", callback_data=f"admin_reject_{dep_id}")]]
        try:
            await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        except:
            pass

        if uid in user_data:
            del user_data[uid]
        return ConversationHandler.END

    dep_id = create_pending_deposit(uid, tx, amount_usd, method="crypto", currency="USD")

    await update.message.reply_text("⏳ تم الإرسال. انتظر التأكيد.", reply_markup=get_main_keyboard(uid))
    user = get_user_full(uid)
    username = user[1] if user else "Unknown"
    admin_msg = (
        f"📈 إيداع رقمي\n"
        f"👤 {username}\n"
        f"💼 ${amount_usd} (≈{amount_nsp:,.2f} NSP)\n"
        f"💵 **رصيد Ichancy الحقيقي:** `{ichancy_balance:,.2f} NSP`\n"
        f"🔄 **رصيد الكاشير:** `{cashier_balance:,.2f} NSP`\n"
        f"⚠️ **الحد الأقصى للموافقة:** `{max_amount_usd:,.2f} USD`\n"
        f"Tx: `{tx[:15]}...`"
    )
    kb = [[InlineKeyboardButton("✅ موافقة", callback_data=f"admin_approve_{dep_id}")], [InlineKeyboardButton("❌ رفض", callback_data=f"admin_reject_{dep_id}")]]
    try:
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    except:
        pass
    if uid in user_data:
        del user_data[uid]
    return ConversationHandler.END


# ==================== السحب ====================


async def start_withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, method=None):
    """بدء عملية السحب - استلام المبلغ"""
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    if method is None and query.data:
        if query.data == "with_sertel":
            method = "سيرتل كاش"
        elif query.data == "with_sham_lira":
            method = "شام كاش ليرة"
        elif query.data == "with_sham_dollar":
            method = "شام كاش دولار"
        elif query.data == "with_crypto":
            method = "عملات رقمية"

    if method:
        context.user_data["withdraw_method"] = method
        print(f"DEBUG - start_withdrawal_amount: Set withdraw_method to: {method} for user {uid}")
    else:
        print(f"DEBUG - start_withdrawal_amount: WARNING - method is None for user {uid}")

    balance_data = get_wallet_balance(uid)
    balance = balance_data.get("balance", 0)

    ichancy_balance, ichancy_username = get_ichancy_balance(uid)
    ichancy_balance_msg = f"\n💵 **رصيد Ichancy الحقيقي:** `{ichancy_balance:,.2f} NSP`" if ichancy_balance > 0 else ""

    if method in ["سيرتل كاش", "شام كاش ليرة", "شام كاش دولار"]:
        prompt_text = f"أدخل المبلغ الذي تريد سحبه (NSP):"
    else:
        prompt_text = f"أدخل المبلغ الذي تريد سحبه (NSP):"

    await query.edit_message_text(
        f"💳 **سحب رصيد**\n\n"
        f"🔫 **طريقة السحب:** `{method}`\n"
        f"{ichancy_balance_msg}\n\n"
        f"{prompt_text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="withdraw_menu")]]),
    )
    return WITHDRAW_AMOUNT


async def withdrawal_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام المبلغ والتحقق منه قبل طلب عنوان المحفظة"""
    print(f"DEBUG - withdrawal_amount_received START:")
    print(f"  all user_data: {context.user_data}")

    method = context.user_data.get("withdraw_method", "غير محدد")

    try:
        amount = float(update.message.text.strip())
        if amount <= 0:
            await update.message.reply_text(
                f"❌ المبلغ يجب أن يكون أكبر من صفر.\n\n🔫 طريقة السحب: `{method}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔧 إعادة المحاولة", callback_data="withdraw_menu")],
                    [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="main_menu")],
                ]),
            )
            return WITHDRAW_AMOUNT
    except ValueError:
        await update.message.reply_text(
            f"❌ مبلغ غير صحيح. أدخل رقماً:\n\n🔫 طريقة السحب: `{method}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔧 إعادة المحاولة", callback_data="withdraw_menu")],
                [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="main_menu")],
            ]),
        )
        return WITHDRAW_AMOUNT

    uid = update.effective_user.id
    ichancy_balance, _ = get_ichancy_balance(uid)
    balance = ichancy_balance

    if amount > balance:
        await update.message.reply_text(
            f"❌ **رصيد غير كافٍ!**\n\n"
            f"🔫 طريقة السحب: `{method}`\n"
            f"💵 رصيدك الحالي: `{balance:,.2f} NSP`\n"
            f"💳 المبلغ المطلوب: `{amount:,.2f} NSP`\n\n"
            f"اختر:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔧 إعادة المحاولة", callback_data="withdraw_menu")],
                [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="main_menu")],
            ]),
        )
        return ConversationHandler.END

    context.user_data["withdraw_amount"] = amount

    referral_settings = get_referral_settings()
    withdrawal_commission_percent = referral_settings.get("withdrawal_commission", 10.0)

    fee_amount = amount * (withdrawal_commission_percent / 100)
    net_amount = amount - fee_amount

    usdt_to_nsp_rate = get_exchange_rate()
    net_amount_usd = net_amount / usdt_to_nsp_rate if usdt_to_nsp_rate > 0 else 0

    if method == "سيرتل كاش":
        wallet_prompt = "أدخل رقم سيرتل كاش للتحويل إليه:"
    elif method == "شام كاش ليرة":
        wallet_prompt = "أدخل رقم شام كاش (ليرة) للتحويل إليه:"
    elif method == "شام كاش دولار":
        wallet_prompt = "أدخل رقم شام كاش (دولار) للتحويل إليه:"
    elif method == "عملات رقمية":
        wallet_prompt = "أدخل عنوان المحفظة الرقمية (USDT TRC20):"
    else:
        wallet_prompt = "أدخل رقم المحفظة أو الكود:"

    ichancy_balance, ichancy_username = get_ichancy_balance(uid)
    ichancy_balance_msg = f"\n💵 **رصيد Ichancy الحقيقي:** `{ichancy_balance:,.2f} NSP`" if ichancy_balance > 0 else ""

    if method == "سيرتل كاش":
        sertel_value = net_amount / 100
        await update.message.reply_text(
            f"💳 **سحب رصيد**\n\n"
            f"💵 المبلغ: `{amount:,.2f} NSP`\n"
            f"🔫 الطريقة: `{method}`\n\n"
            f"🩸 العمولة ({withdrawal_commission_percent}%): `{fee_amount:,.2f} NSP`\n"
            f"💳 المبلغ الصافي: `{sertel_value:,.2f} سيرتل كاش`"
            f"{ichancy_balance_msg}\n\n"
            f"{wallet_prompt}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="withdraw_menu")]]),
        )
    elif method == "شام كاش ليرة":
        lira_value = net_amount / 100
        await update.message.reply_text(
            f"💳 **سحب رصيد**\n\n"
            f"💵 المبلغ: `{amount:,.2f} NSP`\n"
            f"🔫 الطريقة: `{method}`\n\n"
            f"🩸 العمولة ({withdrawal_commission_percent}%): `{fee_amount:,.2f} NSP`\n"
            f"💳 المبلغ الصافي: `{lira_value:,.2f} شام كاش ليرة`"
            f"{ichancy_balance_msg}\n\n"
            f"{wallet_prompt}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="withdraw_menu")]]),
        )
    else:
        await update.message.reply_text(
            f"💳 **سحب رصيد**\n\n"
            f"💵 المبلغ: `{amount:,.2f} NSP`\n"
            f"🔫 الطريقة: `{method}`\n\n"
            f"🩸 العمولة ({withdrawal_commission_percent}%): `{fee_amount:,.2f} NSP`\n"
            f"💳 المبلغ الصافي: `{net_amount:,.2f} NSP` (≈ `{net_amount_usd:,.2f}$`)"
            f"{ichancy_balance_msg}\n\n"
            f"{wallet_prompt}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="withdraw_menu")]]),
        )
    return WITHDRAW_WALLET


async def withdrawal_wallet_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام عنوان المحفظة وخصم الرصيد"""
    wallet_address = update.message.text.strip()

    method = context.user_data.get("withdraw_method", "غير محدد")

    if len(wallet_address) < 3:
        await update.message.reply_text(
            f"❌ رقم المحفظة قصير جداً. يرجى إدخال رقم صحيح:\n\n"
            f"🔫 طريقة السحب: `{method}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔧 إعادة المحاولة", callback_data="withdraw_menu")],
                [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="main_menu")],
            ]),
        )
        return WITHDRAW_WALLET

    uid = update.effective_user.id
    amount = context.user_data.get("withdraw_amount", 0)

    print(f"DEBUG - withdraw_wallet_received:")
    print(f"  uid: {uid}")
    print(f"  amount: {amount}")
    print(f"  method from user_data: {method}")
    print(f"  all user_data: {context.user_data}")

    if amount <= 0:
        await update.message.reply_text(f"❌ حدث خطأ في المبلغ. يرجى المحاولة مرة أخرى.\n\n🔫 طريقة السحب: `{method}`", parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
        return ConversationHandler.END

    referral_settings = get_referral_settings()
    withdrawal_commission_percent = referral_settings.get("withdrawal_commission", 10.0)

    fee_amount = amount * (withdrawal_commission_percent / 100)
    net_amount = amount - fee_amount

    usdt_to_nsp_rate = get_exchange_rate()
    net_amount_usd = net_amount / usdt_to_nsp_rate if usdt_to_nsp_rate > 0 else 0

    user = get_user_full(uid)
    ichancy_username = user[3] if len(user) > 3 and user[3] else None

    final_username = ichancy_username if ichancy_username else "Unknown"

    ichancy_balance, _ = get_ichancy_balance(uid)

    ichancy_withdrawal_success = False
    ichancy_withdrawal_msg = ""

    if ichancy_username:
        try:
            agent = AgentAPI()
            player_id = agent.get_player_id(ichancy_username)
            if player_id:
                withdraw_amount = int(round(amount))
                print(f"DEBUG - Attempting to withdraw from Ichancy:")
                print(f"  player_id: {player_id}")
                print(f"  amount: {withdraw_amount}")
                print(f"  original amount: {amount}")

                res = agent.withdraw(player_id, withdraw_amount)
                print(f"DEBUG - Withdraw response: {res}")

                if res.get("success"):
                    ichancy_withdrawal_success = True
                    ichancy_withdrawal_msg = "✅ تم الخصم من المحفظة"
                else:
                    ichancy_withdrawal_msg = f"⚠️ خطأ في الخصم من المحفظة: {res.get('message', 'Unknown')}"
            else:
                ichancy_withdrawal_msg = "⚠️ لم يتم العثور على اللاعب في المحفظة"
        except Exception as e:
            print(f"DEBUG - Withdraw exception: {e}")
            ichancy_withdrawal_msg = f"⚠️ استثناء: {str(e)}"
    else:
        ichancy_withdrawal_msg = "⚠️ اسم المستخدم غير موجود"

    if not ichancy_withdrawal_success:
        await update.message.reply_text(f"❌ **فشل السحب**\n\n{ichancy_withdrawal_msg}\n\nيرجى التأكد من رصيدك في المحفظة والمحاولة مرة أخرى.", reply_markup=get_main_keyboard(uid))
        return ConversationHandler.END

    withdraw_id = create_pending_withdrawal(uid, amount, fee_amount, net_amount, method)

    deduct_notes = f"Method: {method} | Code: {withdraw_id} | Wallet: {wallet_address} | Ichancy: {ichancy_withdrawal_msg}"
    deduct_from_wallet(uid, amount, "NSP", withdraw_id, deduct_notes)

    update_cashier_balance(net_amount, "add")
    add_cashier_transaction("withdrawal_net", net_amount, "NSP", f"Withdrawal from user {uid} via {method}")

    if method == "سيرتل كاش":
        net_display = f"{net_amount / 100:,.2f} سيرتل كاش"
    elif method == "شام كاش ليرة":
        net_display = f"{net_amount / 100:,.2f} شام كاش ليرة"
    elif method == "شام كاش دولار":
        net_display = f"{net_amount_usd:,.2f} شام كاش دولار"
    elif method == "عملات رقمية":
        net_display = f"{net_amount_usd:,.2f} USDT"
    else:
        net_display = f"{net_amount:,.2f} NSP"

    if method == "سيرتل كاش":
        sertel_value = net_amount / 100
        admin_msg = (
            f"💳 **طلب سحب جديد (تم الخصم)**\n\n"
            f"👤 المستخدم: `{final_username}`\n"
            f"💍 Telegram ID: `{uid}`\n"
            f"🔫 طريقة السحب: `{method}`\n"
            f"💵 الصافي: `{sertel_value:,.2f} سيرتل كاش`\n"
            f"📷 المحفظة/الكود: `{wallet_address}`\n\n"
            f"رقم الطلب: `{withdraw_id}`"
        )
    elif method == "شام كاش ليرة":
        lira_value = net_amount / 100
        admin_msg = (
            f"💳 **طلب سحب جديد (تم الخصم)**\n\n"
            f"👤 المستخدم: `{final_username}`\n"
            f"💍 Telegram ID: `{uid}`\n"
            f"🔫 طريقة السحب: `{method}`\n"
            f"💵 الصافي: `{lira_value:,.2f} شام كاش ليرة`\n"
            f"📷 المحفظة/الكود: `{wallet_address}`\n\n"
            f"رقم الطلب: `{withdraw_id}`"
        )
    else:
        admin_msg = (
            f"💳 **طلب سحب جديد (تم الخصم)**\n\n"
            f"👤 المستخدم: `{final_username}`\n"
            f"💍 Telegram ID: `{uid}`\n"
            f"🔫 طريقة السحب: `{method}`\n"
            f"💳 الصافي: `{net_amount:,.2f} NSP` (≈ `{net_amount_usd:,.2f}$`)\n"
            f"💼 قيمة الصافي: `{net_display}`\n"
            f"📷 المحفظة/الكود: `{wallet_address}`\n\n"
            f"رقم الطلب: `{withdraw_id}`"
        )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ موافقة وإرسال - {final_username}", callback_data=f"admin_withdraw_approve_{withdraw_id}")],
        [InlineKeyboardButton("❌ رفض", callback_data=f"admin_withdraw_reject_{withdraw_id}")],
    ])

    try:
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        print(f"Error sending to admin: {e}")

    if method == "سيرتل كاش":
        sertel_value = net_amount / 100
        user_msg = (
            f"✅ **تم إرسال طلب السحب بنجاح!**\n\n"
            f"💵 المبلغ الكلي: `{amount:,.2f} NSP`\n"
            f"🩸 العمولة ({withdrawal_commission_percent}%): `{fee_amount:,.2f} NSP`\n"
            f"💳 المبلغ الصافي: `{sertel_value:,.2f} سيرتل كاش`\n"
            f"🔫 الطريقة: `{method}`\n"
            f"📷 المحفظة: `{wallet_address[:20]}...`\n\n"
            f"⏳ طلبك قيد المراجعة من قبل الإدارة.\n"
            f"سيتم التحويل فوراً بعد الموافقة.\n"
            f"رقم الطلب: `{withdraw_id}`"
        )
    elif method == "شام كاش ليرة":
        lira_value = net_amount / 100
        user_msg = (
            f"✅ **تم إرسال طلب السحب بنجاح!**\n\n"
            f"💵 المبلغ الكلي: `{amount:,.2f} NSP`\n"
            f"🩸 العمولة ({withdrawal_commission_percent}%): `{fee_amount:,.2f} NSP`\n"
            f"💳 المبلغ الصافي: `{lira_value:,.2f} شام كاش ليرة`\n"
            f"🔫 الطريقة: `{method}`\n"
            f"📷 المحفظة: `{wallet_address[:20]}...`\n\n"
            f"⏳ طلبك قيد المراجعة من قبل الإدارة.\n"
            f"سيتم التحويل فوراً بعد الموافقة.\n"
            f"رقم الطلب: `{withdraw_id}`"
        )
    else:
        user_msg = (
            f"✅ **تم إرسال طلب السحب بنجاح!**\n\n"
            f"💵 المبلغ الكلي: `{amount:,.2f} NSP`\n"
            f"🩸 العمولة ({withdrawal_commission_percent}%): `{fee_amount:,.2f} NSP`\n"
            f"💳 المبلغ الصافي: `{net_amount:,.2f} NSP` (≈ `{net_amount_usd:,.2f}`$)\n"
            f"🔫 الطريقة: `{method}`\n"
            f"📷 المحفظة: `{wallet_address[:20]}...`\n\n"
            f"⏳ طلبك قيد المراجعة من قبل الإدارة.\n"
            f"سيتم التحويل فوراً بعد الموافقة.\n"
            f"رقم الطلب: `{withdraw_id}`"
        )

    if ichancy_withdrawal_success:
        user_msg += f"✅ تم خصم الرصيد من حسابك في المحفظة\n"
    else:
        user_msg += f"⚠️ {ichancy_withdrawal_msg}\n"

    user_msg += f"\n⏳ تم إرسال الطلب للإدارة.\nسيتم التحويل فوراً بعد الموافقة."

    await update.message.reply_text(user_msg, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

    if "withdraw_amount" in context.user_data:
        del context.user_data["withdraw_amount"]
    if "withdraw_method" in context.user_data:
        del context.user_data["withdraw_method"]

    return ConversationHandler.END


async def admin_withdraw_approve_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """موافقة الأدمن على السحب - الرصيد تم خصمه مسبقاً"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    try:
        withdraw_id = int(query.data.split("_")[3])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ خطأ في معرف السحب.")
        return

    from database import get_pending_withdrawal_by_id

    withdraw = get_pending_withdrawal_by_id(withdraw_id)

    if not withdraw:
        await query.edit_message_text("❌ طلب السحب غير موجود أو تم معالجته.")
        return

    uid = withdraw[1]
    amount = withdraw[2]
    fee_amount = withdraw[3]
    net_amount = withdraw[4]
    method = withdraw[5]

    referral_settings = get_referral_settings()
    withdrawal_commission_percent = referral_settings.get("withdrawal_commission", 10.0)

    cashier_commission = amount * (withdrawal_commission_percent / 100)

    tr302_commission = amount * 0.02
    tr302_username = "T402_Pr25"

    print(f"\n=== DEBUG: 2% Commission Process ===")
    print(f"Total amount: {amount} NSP")
    print(f"2% commission: {tr302_commission} NSP")
    print(f"Target user: {tr302_username}")

    tr302_msg = ""

    if tr302_commission > 0:
        try:
            agent = AgentAPI()
            player_id = agent.get_player_id(tr302_username)
            print(f"Ichancy player_id for {tr302_username}: {player_id}")

            if player_id:
                res = agent.deposit(player_id, int(round(tr302_commission)))
                if res.get("success"):
                    tr302_msg = f"\n💵 عمولة نظامية (2%): `{tr302_commission:,.2f} NSP` → {tr302_username} ✅"
                    print(f"✅ SUCCESS: 2% commission added to Ichancy!")
                else:
                    tr302_msg = f"\n⚠️ عمولة نظامية (2%): `{tr302_commission:,.2f} NSP` → {tr302_username} (فشل الإيداع في المحفظة)"
                    print(f"❌ FAILED to deposit to Ichancy: {res}")
            else:
                tr302_msg = f"\n⚠️ عمولة نظامية (2%): لم يتم العثور على `{tr302_username}` في المحفظة"
                print(f"❌ Player ID not found in Ichancy for {tr302_username}")

            tr302_user_data = get_user_by_ichancy_username(tr302_username)
            tr302_user_id = tr302_user_data["telegram_id"] if tr302_user_data else None
            if tr302_user_id:
                add_to_wallet(tr302_user_id, tr302_commission, "NSP", related_id=withdraw_id, notes=f"2% automatic commission from withdrawal {withdraw_id}")
                print(f"✅ Commission also added to local wallet (user_id: {tr302_user_id})")

        except Exception as e:
            print(f"❌ ERROR in 2% commission process: {e}")
            import traceback
            traceback.print_exc()
            tr302_msg = f"\n⚠️ خطأ في إضافة عمولة 2% إلى {tr302_username}"

    print(f"=== END: 2% Commission Process ===\n")

    from database import update_withdrawal_status_withdrawal_id

    update_withdrawal_status_withdrawal_id(withdraw_id, "approved", admin_id=ADMIN_ID)

    usdt_to_nsp_rate = get_exchange_rate()
    net_amount_usd = net_amount / usdt_to_nsp_rate if usdt_to_nsp_rate > 0 else 0

    if method == "سيرتل كاش":
        sertel_value = net_amount / 100
        await query.edit_message_text(f"✅ تم تأكيد السحب بنجاح!\n\n💳 الصافي: {sertel_value:,.2f} سيرتل كاش", reply_markup=get_main_keyboard(ADMIN_ID))
    elif method == "شام كاش ليرة":
        lira_value = net_amount / 100
        await query.edit_message_text(f"✅ تم تأكيد السحب بنجاح!\n\n💳 الصافي: {lira_value:,.2f} شام كاش ليرة", reply_markup=get_main_keyboard(ADMIN_ID))
    else:
        await query.edit_message_text(f"✅ تم تأكيد السحب بنجاح!\n\n💳 الصافي: {net_amount:,.2f} NSP (≈ {net_amount_usd:,.2f}$)", reply_markup=get_main_keyboard(ADMIN_ID))

    try:
        if method == "سيرتل كاش":
            sertel_value = net_amount / 100
            await context.bot.send_message(uid, f"✅ تمت عملية السحب بنجاح!\n\n💳 المبلغ: {amount:,.2f} NSP\n🩸 العمولة ({withdrawal_commission_percent}%): {fee_amount:,.2f} NSP\n💳 الصافي: {sertel_value:,.2f} سيرتل كاش\n🔫 الطريقة: {method}\n\nشكراً لاستخدامك خدماتنا!", reply_markup=get_main_keyboard(uid))
        elif method == "شام كاش ليرة":
            lira_value = net_amount / 100
            await context.bot.send_message(uid, f"✅ تمت عملية السحب بنجاح!\n\n💳 المبلغ: {amount:,.2f} NSP\n🩸 العمولة ({withdrawal_commission_percent}%): {fee_amount:,.2f} NSP\n💳 الصافي: {lira_value:,.2f} شام كاش ليرة\n🔫 الطريقة: {method}\n\nشكراً لاستخدامك خدماتنا!", reply_markup=get_main_keyboard(uid))
        else:
            await context.bot.send_message(uid, f"✅ تمت عملية السحب بنجاح!\n\n💳 المبلغ: {amount:,.2f} NSP\n🩸 العمولة ({withdrawal_commission_percent}%): {fee_amount:,.2f} NSP\n💳 الصافي: {net_amount:,.2f} NSP (≈ {net_amount_usd:,.2f}$)\n🔫 الطريقة: {method}\n\nشكراً لاستخدامك خدماتنا!", reply_markup=get_main_keyboard(uid))
    except Exception as e:
        print(f"Error sending message to user: {e}")


async def admin_withdraw_reject_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض طلب السحب - استرداد الرصيد للمستخدم"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    try:
        withdraw_id = int(query.data.split("_")[3])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ خطأ في معرف السحب.")
        return

    from database import get_pending_withdrawal_by_id, update_withdrawal_status_withdrawal_id

    withdraw = get_pending_withdrawal_by_id(withdraw_id)

    if withdraw:
        uid = withdraw[1]
        amount = withdraw[2]
        net_amount = withdraw[4]
        method = withdraw[5]

        user = get_user_full(uid)
        ichancy_username = user[3] if len(user) > 3 and user[3] else None

        ichancy_refund_msg = ""
        if ichancy_username:
            try:
                agent = AgentAPI()
                player_id = agent.get_player_id(ichancy_username)
                if player_id:
                    res = agent.deposit(player_id, amount)
                    if res.get("success"):
                        ichancy_refund_msg = "✅ تم استرداد الرصيد للمحفظة"
                    else:
                        ichancy_refund_msg = f"⚠️ خطأ في الإيداع للمحفظة: {res.get('message', 'Unknown')}"
                else:
                    ichancy_refund_msg = "⚠️ لم يتم العثور على اللاعب في المحفظة"
            except Exception as e:
                ichancy_refund_msg = f"⚠️ استثناء: {str(e)}"
        else:
            ichancy_refund_msg = "⚠️ اسم المستخدم غير موجود"

        update_withdrawal_status_withdrawal_id(withdraw_id, "rejected", admin_id=ADMIN_ID)

        refund_notes = f"Method: {method} | Code: {withdraw_id} | Refund of rejected withdrawal | Ichancy: {ichancy_refund_msg}"
        add_to_wallet(uid, amount, "NSP", withdraw_id, refund_notes)

        update_cashier_balance(net_amount, "deduct")
        add_cashier_transaction("withdrawal_refund", net_amount, "NSP", f"Refund rejected withdrawal from user {uid}")

        from database import add_wallet_transaction

        notes = f"Method: {method} | Code: {withdraw_id} | Rejected - Amount refunded | Ichancy: {ichancy_refund_msg}"
        add_wallet_transaction(uid, "withdrawal", amount, "NSP", "rejected", withdraw_id, notes)

        await query.edit_message_text(f"❌ تم رفض طلب السحب.\n\n{ichancy_refund_msg}", reply_markup=get_main_keyboard(ADMIN_ID))

        try:
            await context.bot.send_message(uid, f"❌ **تم رفض طلب السحب.**\n\n{ichancy_refund_msg}\n\nيرجى التواصل مع الدعم لمعرفة السبب.", parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
        except Exception as e:
            print(f"Error sending message to user: {e}")


# ==================== الأدمن ====================


async def admin_show_cashier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    b = get_cashier_balance()
    current_bal = b.get("balance", 0)
    msg = f"💵 **رصيد الكاشير الحالي:**\n`{current_bal:,.2f} NSP`\n\nاختر الإجراء:"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🩸 تعيين رصيد جديد", callback_data="set_cashier_act")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])
    await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)


async def admin_show_cashier_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    b = get_cashier_balance()
    current_bal = b.get("balance", 0)
    msg = f"💵 **رصيد الكاشير الحالي:**\n`{current_bal:,.2f} NSP`\n\nاختر الإجراء:"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🩸 تعيين رصيد جديد", callback_data="set_cashier_act")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


async def admin_set_rate_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"⚠️ **تعديل سعر الصرف**\n\nالسعر الحالي: 1$ = {get_exchange_rate()} NSP\n\nأدخل السعر الجديد:")
    return ADMIN_SET_RATE


async def admin_set_rate_entry_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"⚠️ **تعديل سعر الصرف**\n\nالسعر الحالي: 1$ = {get_exchange_rate()} NSP\n\nأدخل السعر الجديد:")
    return ADMIN_SET_RATE


async def admin_rate_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_rate = float(update.message.text.strip())
        set_exchange_rate(new_rate)
        await update.message.reply_text(f"✅ تم تحديث السعر: 1$ = {new_rate} NSP", reply_markup=get_admin_settings_keyboard())
    except:
        await update.message.reply_text("❌ رقم غير صحيح.", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_set_deposit_fee_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"💵 **تعديل رسوم الإيداع**\n\nالنسبة الحالية: {get_deposit_fee()}%\n\nأدخل النسبة الجديدة (مثال 5 لـ 5%):")
    return ADMIN_SET_DEPOSIT_FEE


async def admin_set_deposit_fee_entry_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💵 **تعديل رسوم الإيداع**\n\nالنسبة الحالية: {get_deposit_fee()}%\n\nأدخل النسبة الجديدة (مثال 5 لـ 5%):")
    return ADMIN_SET_DEPOSIT_FEE


async def admin_deposit_fee_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fee = float(update.message.text.strip())
        set_deposit_fee(fee)
        await update.message.reply_text(f"✅ تم تحديث رسوم الإيداع: {fee}%", reply_markup=get_admin_settings_keyboard())
    except:
        await update.message.reply_text("❌ رقم غير صحيح.", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_show_bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        status_data = get_bot_status()
        current_status = status_data.get("status", "active")

        kb = [
            [InlineKeyboardButton("🪸 Active", callback_data="bot_status_active")],
            [InlineKeyboardButton("💤 Rest", callback_data="bot_status_rest")],
            [InlineKeyboardButton("🩸 Maintenance", callback_data="bot_status_maintenance")],
            [InlineKeyboardButton("✏️ تعديل رسالة Rest", callback_data="edit_rest_message")],
            [InlineKeyboardButton("✏️ تعديل رسالة Maintenance", callback_data="edit_maintenance_message")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
        ]

        try:
            await query.edit_message_text(f"🛻 حالة البوت: {current_status}", reply_markup=InlineKeyboardMarkup(kb))
        except Exception as edit_error:
            if "Message is not modified" not in str(edit_error):
                logger.error(f"Error editing bot status: {edit_error}")

    except Exception as e:
        logger.error(f"Error in admin_show_bot_status: {e}")
        try:
            await update.callback_query.message.reply_text("❌ حدث خطأ في عرض حالة البوت.", reply_markup=get_main_keyboard(update.effective_user.id))
        except:
            pass


async def admin_show_bot_status_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        status_data = get_bot_status()
        current_status = status_data.get("status", "active")

        kb = [
            [InlineKeyboardButton("🪸 Active", callback_data="bot_status_active")],
            [InlineKeyboardButton("💤 Rest", callback_data="bot_status_rest")],
            [InlineKeyboardButton("🩸 Maintenance", callback_data="bot_status_maintenance")],
            [InlineKeyboardButton("✏️ تعديل رسالة Rest", callback_data="edit_rest_message")],
            [InlineKeyboardButton("✏️ تعديل رسالة Maintenance", callback_data="edit_maintenance_message")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
        ]

        await update.message.reply_text(f"🛻 حالة البوت: {current_status}", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logger.error(f"Error in admin_show_bot_status_direct: {e}")
        await update.message.reply_text("❌ حدث خطأ في عرض حالة البوت.", reply_markup=get_main_keyboard(update.effective_user.id))


async def admin_edit_rest_message_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✏️ أدخل رسالة الراحة الجديدة:")
    return ADMIN_SET_REST_MESSAGE


async def admin_edit_maintenance_message_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚠️ أدخل رسالة الصيانة الجديدة:")
    return ADMIN_SET_MAINTENANCE_MESSAGE


async def admin_message_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if ADMIN_ID in user_data and "message_type" in user_data[ADMIN_ID]:
        msg_type = user_data[ADMIN_ID]["message_type"]

        current_status = get_bot_status().get("status", "active")

        if msg_type == "rest":
            set_bot_status(current_status, rest_message=text)
        elif msg_type == "maintenance":
            set_bot_status(current_status, maintenance_message=text)

        del user_data[ADMIN_ID]["message_type"]

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة لحالة البوت", callback_data="admin_bot_status")]])
        await update.message.reply_text("✅ تم تحديث الرسالة.", reply_markup=keyboard)
    else:
        await update.message.reply_text("❌ خطأ في السياق.", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_approve_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    try:
        dep_id = int(query.data.split("_")[2])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ خطأ في معرف الإيداع.")
        return

    dep = get_pending_deposit(dep_id)
    if not dep:
        await query.edit_message_text("❌ الإيداع غير موجود أو تم معالجته.")
        return

    if "admin_pending" not in context.bot_data:
        context.bot_data["admin_pending"] = {}

    context.bot_data["admin_pending"][ADMIN_ID] = dep_id

    uid = dep[1]
    deposit_currency = dep[4]
    deposit_method = dep[8]

    cashier_bal = get_cashier_balance()
    cashier_balance_nsp = cashier_bal.get("balance", 0)
    exchange_rate = get_exchange_rate()

    if "سيرتل" in deposit_method:
        cashier_after_fee = cashier_balance_nsp * 0.90
        max_amount_nsp = cashier_after_fee / 100
        max_amount_display = max_amount_nsp
        input_prompt = f"أدخل المبلغ بالسيرتل كاش:\n\n💵 الحد الأقصى: `{max_amount_display:,.2f} سيرتل كاش`"
    elif "ليرة" in deposit_method:
        cashier_after_fee = cashier_balance_nsp * 0.90
        max_amount_nsp = cashier_after_fee / 100
        max_amount_display = max_amount_nsp
        input_prompt = f"أدخل المبلغ بشام كاش ليرة:\n\n💵 الحد الأقصى: `{max_amount_display:,.2f} شام كاش ليرة`"
    elif "دولار" in deposit_method:
        max_amount_nsp = cashier_balance_nsp
        max_amount_display = max_amount_nsp / exchange_rate if exchange_rate > 0 else 0
        input_prompt = f"أدخل المبلغ بالدولار (سيتم تحويله تلقائياً إلى NSP):\n\n💵 الحد الأقصى: `{max_amount_display:,.2f} USD`"
    elif deposit_currency == "USD" or "crypto" in deposit_method or "binance" in deposit_method:
        max_amount_nsp = cashier_balance_nsp
        max_amount_display = max_amount_nsp / exchange_rate if exchange_rate > 0 else 0
        input_prompt = f"أدخل المبلغ بالدولار (سيتم تحويله تلقائياً إلى NSP):\n\n💵 الحد الأقصى: `{max_amount_display:,.2f} USD`"
    else:
        max_amount_nsp = cashier_balance_nsp
        max_amount_display = max_amount_nsp
        input_prompt = f"أدخل المبلغ بـ NSP:\n\n💵 الحد الأقصى: `{max_amount_display:,.2f} NSP`"

    await query.edit_message_text(f"📑 إيداع #{dep_id}\n\n{input_prompt}")
    return ADMIN_DEP_AMOUNT


async def admin_amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ رقم غير صحيح. أدخل رقماً:")
        return ADMIN_DEP_AMOUNT

    admin_pending = context.bot_data.get("admin_pending", {})
    if ADMIN_ID not in admin_pending:
        await update.message.reply_text("❌ خطأ: لم يتم العثور على معلومات الإيداع.")
        return ConversationHandler.END

    dep_id = admin_pending[ADMIN_ID]
    dep = get_pending_deposit(dep_id)
    if not dep:
        await update.message.reply_text("❌ الإيداع غير موجود أو تم معالجته.")
        return ConversationHandler.END

    uid = dep[1]
    deposit_currency = dep[4]
    deposit_method = dep[8]
    reference_code = dep[7]

    if "سيرتل" in deposit_method:
        amount_input = amount
        amount = amount * 100
        amount_usd = 0
        currency_text = f"{amount_input} سيرتل كاش"
    elif deposit_currency == "LBP":
        amount_input = amount
        amount = amount * 100
        amount_usd = 0
        currency_text = f"{amount_input} شام كاش ليرة"
    elif deposit_currency == "USD" or deposit_method in ["crypto", "sham_cash_dollar"]:
        amount_usd = amount
        amount = amount_usd * get_exchange_rate()
        currency_text = f"${amount_usd} USD (×{get_exchange_rate()} = {amount} NSP)"
    else:
        amount_usd = amount / get_exchange_rate() if get_exchange_rate() > 0 else 0
        currency_text = f"{amount} NSP"

    first_deposit = is_first_deposit(uid)

    bonus_settings = get_bonus_settings()
    first_bonus_rate = bonus_settings.get("first_deposit_bonus", 10.0) / 100
    subsequent_bonus_rate = bonus_settings.get("subsequent_deposit_bonus", 5.0) / 100

    bonus_rate = first_bonus_rate if first_deposit else subsequent_bonus_rate
    bonus_amount = amount * bonus_rate
    final_amount = amount + bonus_amount

    ichancy_success = True
    ichancy_msg = ""

    try:
        result = confirm_deposit_by_admin(dep_id, final_amount, ADMIN_ID, bonus_amount)

        if result:
            user = get_user_full(uid)

            if user and len(user) > 3 and user[3]:
                ichancy_username = user[3]
                agent = AgentAPI()
                player_id = agent.get_player_id(ichancy_username)

                if player_id:
                    res = agent.deposit(player_id, final_amount)

                    if res.get("success"):
                        ichancy_msg = "\n\n✅ *تمت الإضافة إلى حساب Ichancy.*"
                        update_cashier_balance(final_amount, "deduct")
                        add_cashier_transaction("deposit", final_amount, "NSP", f"User {uid} deposit")
                    else:
                        ichancy_success = False
                        error_msg = res.get("message", "Unknown error")
                        ichancy_msg = f"\n\n⚠️ **خطأ Ichancy:** `{error_msg}`"

                        from database import get_wallet_balance, deduct_from_wallet, reject_deposit_by_admin

                        balance_data = get_wallet_balance(uid)
                        current_balance = balance_data.get("balance", 0)

                        if current_balance >= final_amount:
                            deduct_from_wallet(uid, final_amount, "NSP", None, f"Reverted deposit #{dep_id} - Ichancy error: {error_msg}")

                        reject_deposit_by_admin(dep_id, ADMIN_ID, f"Ichancy error: {error_msg}")

                        cashier_bal = get_cashier_balance()
                        await context.bot.send_message(ADMIN_ID, f"🩸 **تنبيه: الكاشير فارغة!**\n\n💵 رصيد الكاشير الحالي: `{cashier_bal.get('balance', 0):,.2f} NSP`\n💵 المبلغ المطلوب: `{final_amount:,.2f} NSP`\n👤 المستخدم: {user[1] if user[1] else 'Unknown'} (ID: {uid})\n📑 كود التحويل: {reference_code}\n\n⚠️ يرجى شحن رصيد الكاشير فوراً!")

                        await context.bot.send_message(uid, f"⏳ **تم استلام طلبك!**\n\n💵 المبلغ: {currency_text}\n🐵 المكافأة: {bonus_amount} NSP\n📳 الإجمالي: {final_amount} NSP\n\nشكراً لك! 💋", reply_markup=get_main_keyboard(uid))

                        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

                        context.user_data[f"pending_deposit_{dep_id}"] = {
                            "uid": uid,
                            "amount": amount,
                            "final_amount": final_amount,
                            "bonus_amount": bonus_amount,
                            "currency_text": currency_text,
                            "bonus_type": "أول إيداع" if first_deposit else "إيداع لاحق",
                            "bonus_rate": bonus_rate,
                            "ichancy_username": ichancy_username,
                        }

                        kb = InlineKeyboardMarkup([
                            [InlineKeyboardButton("✅ موافقة", callback_data=f"retry_deposit_{dep_id}")],
                            [InlineKeyboardButton("❌ رفض", callback_data=f"reject_deposit_{dep_id}")],
                        ])

                        await update.message.reply_text(f"❌ **فشلت الموافقة على الإيداع**\n\n💵 المبلغ: {currency_text}\n⚠️ خطأ Ichancy: `{error_msg}`\n\nبسبب شحن رصيد الكاشير، اختر الإجراء:", reply_markup=kb)

                        if "admin_pending" in context.bot_data and ADMIN_ID in context.bot_data["admin_pending"]:
                            del context.bot_data["admin_pending"][ADMIN_ID]
                        return ConversationHandler.END
                else:
                    ichancy_success = False
                    ichancy_msg = "\n\n⚠️ **لم يتم العثور على اللاعب في Ichancy**"

            bonus_type = "أول إيداع" if first_deposit else "إيداع لاحق"

            success_text = f"✅ تمت الموافقة!\nالمبلغ: {currency_text}\nنوع المكافأة: {bonus_type} ({bonus_rate * 100}%){ichancy_msg}"

            if not ichancy_success:
                success_text += "\n\n⚠️ تنبيه: فشل تحديث رصيد Ichancy."

            await update.message.reply_text(success_text, reply_markup=get_main_keyboard(ADMIN_ID))

            try:
                await context.bot.send_message(uid, f"🎀 تم شحن رصيدك بنجاح!\nالمبلغ: {currency_text}\nمكافأة ({bonus_type}): {bonus_amount} NSP ({bonus_rate * 100}%)\nالإجمالي: {final_amount} NSP{ichancy_msg}", reply_markup=get_main_keyboard(uid))
            except Exception as e:
                print(f"Error sending message to user: {e}")
        else:
            await update.message.reply_text("❌ خطأ في قاعدة البيانات.", reply_markup=get_main_keyboard(ADMIN_ID))

    except Exception as e:
        print(f"Exception in admin_amount_entered: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"❌ خطأ غير متوقع: {str(e)[:200]}", reply_markup=get_main_keyboard(ADMIN_ID))

    if "admin_pending" in context.bot_data and ADMIN_ID in context.bot_data["admin_pending"]:
        del context.bot_data["admin_pending"][ADMIN_ID]

    return ConversationHandler.END


async def admin_retry_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعادة محاولة إيداع فاشل - بعد شحن رصيد الكاشير"""
    query = update.callback_query
    await query.answer()

    try:
        dep_id = int(query.data.split("_")[2])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ خطأ في معرف الإيداع.")
        return

    deposit_data = context.user_data.get(f"pending_deposit_{dep_id}")
    if not deposit_data:
        await query.edit_message_text("❌ بيانات الإيداع غير موجودة.")
        return

    uid = deposit_data["uid"]
    final_amount = deposit_data["final_amount"]
    bonus_amount = deposit_data["bonus_amount"]
    ichancy_username = deposit_data["ichancy_username"]
    bonus_type = deposit_data["bonus_type"]
    bonus_rate = deposit_data["bonus_rate"]
    currency_text = deposit_data["currency_text"]

    ichancy_success = True
    ichancy_msg = ""

    if ichancy_username:
        try:
            agent = AgentAPI()
            player_id = agent.get_player_id(ichancy_username)
            if player_id:
                res = agent.deposit(player_id, final_amount)
                if res.get("success"):
                    ichancy_msg = "\n\n✅ *تمت الإضافة إلى حساب Ichancy.*"
                    update_cashier_balance(final_amount, "deduct")
                    add_cashier_transaction("deposit", final_amount, "NSP", f"User {uid} deposit - retry")
                else:
                    ichancy_success = False
                    error_msg = res.get("message", "Unknown error")
                    ichancy_msg = f"\n\n⚠️ **خطأ Ichancy:** `{error_msg}`"
        except Exception as e:
            ichancy_success = False
            ichancy_msg = f"\n\n⚠️ **استثناء:** `{str(e)}`"

    if ichancy_success:
        await query.edit_message_text(f"✅ **تمت الموافقة!**\n\nالمبلغ: {currency_text}\nنوع المكافأة: {bonus_type} ({bonus_rate * 100}%){ichancy_msg}", reply_markup=get_main_keyboard(ADMIN_ID))

        try:
            await context.bot.send_message(uid, f"🎀 تم شحن رصيدك بنجاح!\nالمبلغ: {currency_text}\nمكافأة ({bonus_type}): {bonus_amount} NSP ({bonus_rate * 100}%)\nالإجمالي: {final_amount} NSP{ichancy_msg}", reply_markup=get_main_keyboard(uid))
        except Exception as e:
            print(f"Error sending message to user: {e}")
    else:
        await query.edit_message_text(f"❌ **فشلت المحاولة**\n\nالمبلغ: {currency_text}\n⚠️ خطأ Ichancy: `{ichancy_msg}`", reply_markup=get_main_keyboard(ADMIN_ID))


async def admin_finalize_reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض نهائي للإيداع"""
    query = update.callback_query
    await query.answer()

    try:
        dep_id = int(query.data.split("_")[2])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ خطأ في معرف الإيداع.")
        return

    deposit_data = context.user_data.get(f"pending_deposit_{dep_id}")
    if not deposit_data:
        await query.edit_message_text("❌ بيانات الإيداع غير موجودة.")
        return

    uid = deposit_data["uid"]
    currency_text = deposit_data["currency_text"]

    try:
        await context.bot.send_message(uid, f"❌ **تم رفض طلبك**\n\nيرجى التواصل مع الدعم لمعرفة السبب.", reply_markup=get_main_keyboard(uid))
    except Exception as e:
        print(f"Error sending message to user: {e}")

    await query.edit_message_text(f"❌ تم رفض الإيداع.\n\nالمبلغ: {currency_text}", reply_markup=get_main_keyboard(ADMIN_ID))


async def admin_reject_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        dep_id = int(query.data.split("_")[2])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ خطأ في معرف الإيداع.")
        return

    dep = get_pending_deposit(dep_id)
    if dep:
        reject_deposit_by_admin(dep_id, ADMIN_ID, "مرفوض")
        try:
            await context.bot.send_message(dep[1], "❌ تم الرفض.", reply_markup=get_main_keyboard(dep[1]))
        except:
            pass
    await query.edit_message_text("تم الرفض.", reply_markup=get_main_keyboard(ADMIN_ID))


# ==================== طلبات الحذف ====================


async def admin_show_pending_deletions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    deletions = get_pending_deletions_list()

    if not deletions:
        await query.edit_message_text("🗑️ لا يوجد طلبات حذف معلقة.", reply_markup=get_admin_settings_keyboard())
        return

    msg = "🗑️ **طلبات حذف الحسابات المعلقة:**\n\n"

    for del_req in deletions:
        del_id = del_req[0]
        username = del_req[2] or "Unknown"
        created_at = del_req[4] if len(del_req) > 4 else "Unknown"
        ichancy = del_req[6] if len(del_req) > 6 and del_req[6] else "Unknown"

        msg += f"💍 `{del_id}` | 👤 `{username}`\n🎃 `{ichancy}` | 📮 {created_at}\n───────────────\n"

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())


async def admin_show_pending_deletions_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deletions = get_pending_deletions_list()

    if not deletions:
        await update.message.reply_text("🗑️ لا يوجد طلبات حذف معلقة.", reply_markup=get_admin_settings_keyboard())
        return

    msg = "🗑️ **طلبات حذف الحسابات المعلقة:**\n\n"

    for del_req in deletions:
        del_id = del_req[0]
        username = del_req[2] or "Unknown"
        created_at = del_req[4] if len(del_req) > 4 else "Unknown"
        ichancy = del_req[6] if len(del_req) > 6 and del_req[6] else "Unknown"

        msg += f"💍 `{del_id}` | 👤 `{username}`\n🎃 `{ichancy}` | 📮 {created_at}\n───────────────\n"

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())


async def admin_approve_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    try:
        deletion_id = int(query.data.split("_")[3])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ خطأ في معرف الطلب.")
        return

    del_req = get_pending_deletion(deletion_id)
    if not del_req:
        await query.edit_message_text("❌ الطلب غير موجود أو تم معالجته.")
        return

    telegram_id = del_req[1]
    username = del_req[2] or "Unknown"

    result = approve_deletion_by_admin(deletion_id, ADMIN_ID)

    if result:
        await query.edit_message_text(f"✅ **تم حذف الحساب بنجاح**\n\n👤 المستخدم: `{username}`\n💍 Telegram ID: `{telegram_id}`", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())

        try:
            await context.bot.send_message(telegram_id, "🗑️ **تم حذف حسابك بنجاح.**\n\nيمكنك إعادة التسجيل مرة أخرى.\nانقر /start", parse_mode="Markdown")
        except Exception as e:
            print(f"Error notifying user: {e}")
    else:
        await query.edit_message_text("❌ فشل في حذف الحساب.", reply_markup=get_admin_settings_keyboard())


async def admin_reject_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    try:
        deletion_id = int(query.data.split("_")[3])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ خطأ في معرف الطلب.")
        return

    del_req = get_pending_deletion(deletion_id)
    if not del_req:
        await query.edit_message_text("❌ الطلب غير موجود أو تم معالجته.")
        return

    telegram_id = del_req[1]
    username = del_req[2] or "Unknown"

    reject_deletion_by_admin(deletion_id, ADMIN_ID)

    await query.edit_message_text(f"❌ **تم رفض طلب الحذف**\n\n👤 المستخدم: `{username}`", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())

    try:
        await context.bot.send_message(telegram_id, "❌ **تم رفض طلب حذف حسابك.**\n\nحسابك لا يزال موجوداً.", parse_mode="Markdown", reply_markup=get_main_keyboard(telegram_id))
    except Exception as e:
        print(f"Error notifying user: {e}")


# ==================== وظائف أخرى ====================


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    uid = query.from_user.id if query else update.effective_user.id
    txs = get_user_transactions(uid, limit=50)

    if not txs:
        txt = "📳 **لا توجد معاملات بعد.**"
        if query:
            await query.edit_message_text(txt, parse_mode="Markdown", reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=get_back_keyboard())
        return

    deposits = [t for t in txs if t[0] == "deposit"]
    withdrawals = [t for t in txs if t[0] == "withdrawal"]

    user = get_user_full(uid)
    ichancy_username = user[3] if len(user) > 3 and user[3] else None
    final_username = ichancy_username if ichancy_username else "Unknown"

    txt = "📳 **سجل المعاملات:**\n\n"

    if deposits:
        txt += "💰 **الإيداعات:**\n\n"
        for t in deposits[:15]:
            t_type = t[0]
            amount = t[1]
            currency = t[2]
            status = t[3]
            date_str = t[4]
            note = t[5] if len(t) > 5 else ""

            method = "غير محدد"
            code = "-"
            bonus_info = ""

            if note:
                if "Method:" in note:
                    try:
                        method = note.split("Method:")[1].split("|")[0].strip()
                    except:
                        pass
                if "Code:" in note:
                    try:
                        code = note.split("Code:")[1].split("|")[0].strip()
                    except:
                        pass
                if "Bonus:" in note:
                    try:
                        bonus_value = note.split("Bonus:")[1].split("|")[0].strip()
                        if bonus_value and bonus_value != "0" and bonus_value != "0.0":
                            bonus_info = f"\n🐵 مكافأة: `{bonus_value} {currency}`"
                    except:
                        pass
                if "طريقة:" in note:
                    try:
                        method = note.split("طريقة:")[1].split("|")[0].strip()
                    except:
                        pass
                if "كود:" in note:
                    try:
                        code = note.split("كود:")[1].split("|")[0].strip()
                    except:
                        pass

            status_icon = "✅"
            if status == "rejected" or status == "cancelled":
                status_icon = "❌"

            short_date = str(date_str).split(" ")[0] if date_str else "Unknown"

            txt += f"💵 `{amount:,.0f} NSP` {status_icon}\n🔫 الطريقة: `{method}`\n🔢 كود التحويل: `{code}`{bonus_info}\n📮 {short_date}\n───────────────\n"
    else:
        txt += "💰 **الإيداعات:**\n   لا توجد إيداعات بعد\n\n"

    if withdrawals:
        txt += "\n💳 **السحوبات:**\n\n"
        for t in withdrawals[:15]:
            t_type = t[0]
            amount = t[1]
            currency = t[2]
            status = t[3]
            date_str = t[4]
            note = t[5] if len(t) > 5 else ""

            method = "غير محدد"

            if note:
                if "Method:" in note:
                    try:
                        method = note.split("Method:")[1].split("|")[0].strip()
                    except:
                        pass
                if "طريقة:" in note:
                    try:
                        method = note.split("طريقة:")[1].split("|")[0].strip()
                    except:
                        pass

            status_icon = "✅"
            if status == "rejected" or status == "cancelled":
                status_icon = "❌"

            short_date = str(date_str).split(" ")[0] if date_str else "Unknown"

            txt += f"💵 `{amount:,.0f} {currency}` {status_icon}\n🔫 الطريقة: `{method}`\n📮 {short_date}\n───────────────\n"
    else:
        txt += "\n💳 **السحوبات:**\n    لا توجد سحوبات بعد\n"

    if query:
        await query.edit_message_text(txt, parse_mode="Markdown", reply_markup=get_back_keyboard())
    else:
        await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=get_back_keyboard())


async def request_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب حذف الحساب مع تأكيد"""
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    user = get_user_full(uid)

    if not user:
        await query.edit_message_text("❌ لم يتم العثور على حسابك.", reply_markup=get_main_keyboard(uid))
        return

    username = user[1] if user[1] else "Unknown"
    ichancy_username = user[3] if len(user) > 3 and user[3] else "Unknown"

    await query.edit_message_text(
        f"⚠️ **تأكيد حذف الحساب**\n\n"
        f"أنت على وشك حذف حسابك نهائياً!\n\n"
        f"👤 اسم المستخدم: `{ichancy_username}`\n"
        f"💍 Telegram ID: `{uid}`\n\n"
        f"⚠️ **تنبيه:** هذا الإجراء نهائي ولا يمكن التراجع!\n"
        f"سيتم حذف مجموعة بياناتك بما في ذلك:\n"
        f"• معلومات الحساب\n"
        f"• سجل المعاملات\n"
        f"• الرصيد المتبقي\n\n"
        f"هل أنت متأكد من حذف حسابك؟",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، احذف حسابي", callback_data="confirm_delete_account")],
            [InlineKeyboardButton("❌ لا، تراجع", callback_data="my_account_menu")],
        ]),
    )


async def confirm_delete_account_final(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    """تأكيد نهائي لحذف الحساب"""
    uid = query.from_user.id
    user = get_user_full(uid)

    if not user:
        await query.edit_message_text("❌ لم يتم العثور على حسابك.", reply_markup=get_main_keyboard(uid))
        return

    username = user[1] if user[1] else "Unknown"
    ichancy_username = user[3] if len(user) > 3 and user[3] else "Unknown"

    deletion_id = create_pending_deletion(uid, username)

    if not deletion_id:
        await query.edit_message_text("❌ حدث خطأ في إنشاء طلب الحذف.", reply_markup=get_main_keyboard(uid))
        return

    admin_msg = (
        f"🗑️ **طلب حذف حساب جديد**\n\n"
        f"💍 ID الطلب: `{deletion_id}`\n"
        f"👤 اسم المستخدم: `{username}`\n"
        f"🎃 حساب Ichancy: `{ichancy_username}`\n"
        f"💍 Telegram ID: `{uid}`\n\n"
        f"⚠️ هذا الحذف نهائي ولا يمكن التراجع!"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ موافقة على الحذف", callback_data=f"admin_del_approve_{deletion_id}")],
        [InlineKeyboardButton("❌ رفض", callback_data=f"admin_del_reject_{deletion_id}")],
    ])

    try:
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        print(f"Error sending to admin: {e}")

    await query.edit_message_text(
        "⏳ **تم إرسال طلب حذف حسابك للإدارة.**\n\n"
        "سيتم إشعارك بالقرار قريباً.\n\n"
        "⚠️ ملاحظة: إذا تمت الموافقة، سيتم حذف مجموعة بياناتك نهائياً.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(uid),
    )


async def admin_cashier_set(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("أدخل الرصيد الجديد (NSP):")
    return ADMIN_SET_CASHIER


async def admin_cashier_save(update: Update, context):
    try:
        amt = float(update.message.text.strip())
        set_cashier_balance(amt)
        await update.message.reply_text(f"✅ تم التعيين: {amt}", reply_markup=get_admin_settings_keyboard())
    except:
        await update.message.reply_text("❌ خطأ", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


# ==================== التشغيل ====================


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

    try:
        if ADMIN_ID:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ حدث خطأ:\n```\n{str(context.error)[:400]}\n```", parse_mode="Markdown")
    except:
        pass


def main():
    init_db()

    async def post_init(application: Application) -> None:
        try:
            from telegram import MenuButtonCommands, BotCommand, BotCommandScopeAllPrivateChats

            await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
            print("✅ تم إضافة قائمة الأوامر (Hamburger Menu)")

            commands = [
                BotCommand("start", "ابدأ"),
                BotCommand("help", "مساعدة"),
                BotCommand("privacy", "سياسة الخصوصية والبيانات"),
            ]

            await application.bot.set_my_commands(commands=commands, scope=BotCommandScopeAllPrivateChats())
            print("✅ تم تعيين أوامر البوت لجميع المستخدمين")
        except Exception as e:
            print(f"⚠️ خطأ في تعيين القائمة: {e}")
            import traceback
            traceback.print_exc()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("privacy", privacy_command))

    reg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(reg_agree_terms, pattern="^agree_terms$")],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name_received)],
            REG_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_pass_received)],
        },
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(reg_conv)

    local_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_local_deposit_conv, pattern="^confirm_local_deposit$")],
        states={DEP_LOCAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, local_deposit_code_received)]},
        fallbacks=[CommandHandler("cancel", start), CallbackQueryHandler(deposit_cancel_to_menu, pattern="^deposit_menu$"), CallbackQueryHandler(deposit_cancel_to_main, pattern="^main_menu$")],
    )
    app.add_handler(local_conv)

    crypto_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_crypto_deposit, pattern="^dep_crypto$"), CallbackQueryHandler(start_binance_pay_deposit, pattern="^dep_binance$")],
        states={DEP_CRYPTO_TX: [MessageHandler(filters.TEXT & ~filters.COMMAND, crypto_tx_received)]},
        fallbacks=[CommandHandler("cancel", start), CallbackQueryHandler(deposit_cancel_to_menu, pattern="^deposit_menu$"), CallbackQueryHandler(deposit_cancel_to_main, pattern="^main_menu$")],
    )
    app.add_handler(crypto_conv)

    withdraw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_withdrawal_amount, pattern="^with_(sertel|sham_lira|sham_dollar|crypto)$")],
        states={WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdrawal_amount_received)], WITHDRAW_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdrawal_wallet_received)]},
        fallbacks=[CommandHandler("cancel", start), CallbackQueryHandler(withdraw_cancel_to_menu, pattern="^withdraw_menu$"), CallbackQueryHandler(withdraw_cancel_to_main, pattern="^main_menu$")],
    )
    app.add_handler(withdraw_conv)

    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_approve_entry, pattern="^admin_approve_")],
        states={ADMIN_DEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_amount_entered)]},
        fallbacks=[CommandHandler("cancel", start)],
        name="admin_approve_conversation",
    )
    app.add_handler(admin_conv)

    cash_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_cashier_set, pattern="^set_cashier_act$")],
        states={ADMIN_SET_CASHIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_cashier_save)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(cash_conv)

    rate_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_rate_entry, pattern="^admin_set_rate$")],
        states={ADMIN_SET_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_rate_entered)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(rate_conv)

    fee_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_deposit_fee_entry, pattern="^admin_set_deposit_fee$")],
        states={ADMIN_SET_DEPOSIT_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_deposit_fee_entered)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(fee_conv)

    bonus_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_subsequent_bonus_entry, pattern="^admin_set_subsequent_bonus$"), CallbackQueryHandler(admin_set_first_bonus_entry, pattern="^admin_set_first_bonus$")],
        states={ADMIN_SET_SUBSEQUENT_BONUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_subsequent_bonus_entered)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(bonus_conv)

    withdrawal_commission_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_withdrawal_commission_entry, pattern="^edit_withdrawal_commission$")],
        states={ADMIN_EDIT_WITHDRAWAL_COMMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_withdrawal_commission_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(withdrawal_commission_conv)

    auth_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_settings_auth_entry, pattern="^admin_settings_auth$")],
        states={ADMIN_AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_password_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(auth_conv)

    reset_pass_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(reset_password_start, pattern="^reset_password$")],
        states={
            RESET_PASS_NEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_password_new)],
            RESET_PASS_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_password_confirm)],
            RESET_PASS_FINAL_CONFIRM: [CallbackQueryHandler(reset_password_final_confirm, pattern="^confirm_change_password$"), CallbackQueryHandler(cancel_password_change, pattern="^cancel_password_change$")],
        },
        fallbacks=[CommandHandler("cancel", start), CallbackQueryHandler(password_change_back_to_account, pattern="^my_account_menu$"), CallbackQueryHandler(password_change_back_to_account, pattern="^main_menu$")],
    )
    app.add_handler(reset_pass_conv)

    sertel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_sertel_numbers_entry, pattern="^edit_sertel_numbers$")],
        states={ADMIN_EDIT_SERTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sertel_numbers_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(sertel_conv)

    crypto_wallet_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_crypto_wallet_entry, pattern="^edit_crypto_wallet$")],
        states={ADMIN_EDIT_CRYPTO_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_crypto_wallet_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(crypto_wallet_conv)

    sham_lira_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_sham_lira_numbers_entry, pattern="^edit_sham_lira_numbers$")],
        states={ADMIN_EDIT_SHAM_LIRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sham_lira_numbers_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(sham_lira_conv)

    sham_dollar_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_sham_dollar_numbers_entry, pattern="^edit_sham_dollar_numbers$")],
        states={ADMIN_EDIT_SHAM_DOLLAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sham_dollar_numbers_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(sham_dollar_conv)

    sertel_cash_1_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_sertel_cash_1_entry, pattern="^edit_sertel_cash_1$")],
        states={ADMIN_EDIT_SERTEL_CASH_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sertel_cash_1_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(sertel_cash_1_conv)

    sertel_cash_2_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_sertel_cash_2_entry, pattern="^edit_sertel_cash_2$")],
        states={ADMIN_EDIT_SERTEL_CASH_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sertel_cash_2_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(sertel_cash_2_conv)

    sham_lira_1_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_sham_lira_1_entry, pattern="^edit_sham_lira_1$")],
        states={ADMIN_EDIT_SHAM_LIRA_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sham_lira_1_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(sham_lira_1_conv)

    sham_lira_2_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_sham_lira_2_entry, pattern="^edit_sham_lira_2$")],
        states={ADMIN_EDIT_SHAM_LIRA_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sham_lira_2_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(sham_lira_2_conv)

    sham_dollar_1_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_sham_dollar_1_entry, pattern="^edit_sham_dollar_1$")],
        states={ADMIN_EDIT_SHAM_DOLLAR_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sham_dollar_1_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(sham_dollar_1_conv)

    sham_dollar_2_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_sham_dollar_2_entry, pattern="^edit_sham_dollar_2$")],
        states={ADMIN_EDIT_SHAM_DOLLAR_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_sham_dollar_2_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(sham_dollar_2_conv)

    usdt_address_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_usdt_address_entry, pattern="^edit_usdt_address$")],
        states={ADMIN_EDIT_USDT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_usdt_address_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(usdt_address_conv)

    invite_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(invite_telegram, pattern="^invite_telegram$")],
        states={INVITE_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, invite_username_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(invite_conv)

    gift_transfer_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(gift_transfer_start, pattern="^create_gift_code$")],
        states={
            GIFT_TRANSFER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, gift_transfer_username_received)],
            GIFT_TRANSFER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, gift_transfer_amount_received)],
        },
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(gift_transfer_conv)

    gift_redeem_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(redeem_gift_code_start, pattern="^redeem_gift_code$")],
        states={GIFT_REDEEM_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, redeem_gift_code_received)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(gift_redeem_conv)

    app.add_handler(CommandHandler("gift_approve", admin_gift_approve_command))
    app.add_handler(CommandHandler("gift_reject", admin_gift_reject_command))
    app.add_handler(CommandHandler("gift_list", admin_gift_list_command))

    async def msg_entry_wrapper(update, context):
        query = update.callback_query
        await query.answer()
        if query.data == "edit_rest_message":
            user_data[ADMIN_ID] = {"message_type": "rest"}
            await query.edit_message_text("✏️ أدخل رسالة الراحة الجديدة:")
            return ADMIN_SET_REST_MESSAGE
        elif query.data == "edit_maintenance_message":
            user_data[ADMIN_ID] = {"message_type": "maintenance"}
            await query.edit_message_text("⚠️ أدخل رسالة الصيانة الجديدة:")
            return ADMIN_SET_MAINTENANCE_MESSAGE

    msg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(msg_entry_wrapper, pattern="^edit_(rest|maintenance)_message$")],
        states={ADMIN_SET_REST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_message_entered)], ADMIN_SET_MAINTENANCE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_message_entered)]},
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(msg_conv)

    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot started...")
    app.run_polling(drop_pending_updates=True)


# ==================== إعدادات أخرى ====================


async def admin_show_referral_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إعدادات عمولة السحب"""
    query = update.callback_query
    await query.answer()

    settings = get_referral_settings()
    withdrawal_commission = settings.get("withdrawal_commission", 10.0)

    msg = (
        f"🎆 **عمولة السحب**\n\n"
        f"💵 عمولة السحب الحالية: {withdrawal_commission}%\n\n"
        f"💡 هذه العمولة يتم خصمها من كل عملية سحب."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل عمولة السحب", callback_data="edit_withdrawal_commission")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def admin_show_referral_settings_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إعدادات عمولة السحب مباشرة"""
    settings = get_referral_settings()
    withdrawal_commission = settings.get("withdrawal_commission", 10.0)

    msg = (
        f"🎆 **عمولة السحب**\n\n"
        f"💵 عمولة السحب الحالية: {withdrawal_commission}%\n\n"
        f"💡 هذه العمولة يتم خصمها من كل عملية سحب."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل عمولة السحب", callback_data="edit_withdrawal_commission")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)


# ==================== إعدادات طرق الدفع ====================


async def admin_show_payment_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض وتعديل طرق الدفع"""
    query = update.callback_query
    await query.answer()

    settings = get_payment_settings()
    deposit_methods = settings.get("deposit_methods", [])
    withdrawal_methods = settings.get("withdrawal_methods", [])

    msg = "🩸 **إدارة طرق الدفع**\n\n"

    msg += "💰 **طرق الإيداع:**\n"
    for method in deposit_methods:
        msg += f"  • {method['display_name']}\n"

    msg += "\n💳 **طرق السحب:**\n"
    for method in withdrawal_methods:
        msg += f"  • {method['display_name']}\n"

    msg += "\n⚠️ اختر القائمة لإدارة الطرق:"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 إدارة الإيداعات", callback_data="manage_deposit_methods")],
        [InlineKeyboardButton("💳 إدارة السحوبات", callback_data="manage_withdrawal_methods")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def admin_show_payment_methods_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض طرق الدفع مباشرة"""
    settings = get_payment_settings()
    deposit_methods = settings.get("deposit_methods", [])
    withdrawal_methods = settings.get("withdrawal_methods", [])

    msg = "🩸 **إدارة طرق الدفع**\n\n"

    msg += "💰 **طرق الإيداع:**\n"
    for method in deposit_methods:
        msg += f"  • {method['display_name']}\n"

    msg += "\n💳 **طرق السحب:**\n"
    for method in withdrawal_methods:
        msg += f"  • {method['display_name']}\n"

    msg += "\n⚠️ اختر القائمة لإدارة الطرق:"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 إدارة الإيداعات", callback_data="manage_deposit_methods")],
        [InlineKeyboardButton("💳 إدارة السحوبات", callback_data="manage_withdrawal_methods")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)


# ==================== دوال إعدادات أخرى ====================


async def admin_edit_referral_username_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدخال اسم المستخدم المحيل الجديد"""
    query = update.callback_query
    await query.answer()

    settings = get_referral_settings()
    current_username = settings.get("referral_username", "Tr302_Saertab")

    await query.edit_message_text(f"✏️ **تعديل اسم المستخدم المحيل**\n\nالاسم الحالي: `{current_username}`\n\nأدخل الاسم الجديد (مثال: Tr302_Saertab):", parse_mode="Markdown")
    return ADMIN_EDIT_REFERRAL_USERNAME


async def admin_referral_username_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام اسم المستخدم المحيل الجديد"""
    new_username = update.message.text.strip()

    if not new_username or len(new_username) < 3:
        await update.message.reply_text("❌ الاسم قصير جداً. أدخل اسماً صحيحاً:")
        return ADMIN_EDIT_REFERRAL_USERNAME

    set_referral_settings(referral_username=new_username)
    await update.message.reply_text(f"✅ تم تحديث اسم المستخدم المحيل إلى: `{new_username}`", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_edit_withdrawal_commission_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدخال عمولة السحب الجديدة"""
    query = update.callback_query
    await query.answer()

    settings = get_referral_settings()
    current_commission = settings.get("withdrawal_commission", 10.0)

    await query.edit_message_text(f"✏️ **تعديل عمولة السحب**\n\nالنسبة الحالية: {current_commission}%\n\nأدخل النسبة الجديدة (مثال 10 لـ 10%):", parse_mode="Markdown")
    return ADMIN_EDIT_WITHDRAWAL_COMMISSION


async def admin_withdrawal_commission_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام عمولة السحب الجديدة"""
    try:
        new_commission = float(update.message.text.strip())
        if new_commission < 0 or new_commission > 100:
            await update.message.reply_text("❌ يجب أن تكون النسبة بين 0 و 100:")
            return ADMIN_EDIT_WITHDRAWAL_COMMISSION

        set_referral_settings(withdrawal_commission=new_commission)
        await update.message.reply_text(f"✅ تم تحديث عمولة السحب إلى: {new_commission}%", reply_markup=get_admin_settings_keyboard())
    except ValueError:
        await update.message.reply_text("❌ رقم غير صحيح. أدخل رقماً:")
        return ADMIN_EDIT_WITHDRAWAL_COMMISSION

    return ConversationHandler.END


async def admin_edit_referral_commission_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدخال عمولة الإحالة الجديدة"""
    query = update.callback_query
    await query.answer()

    settings = get_referral_settings()
    current_commission = settings.get("referral_commission", 2.0)

    await query.edit_message_text(f"✏️ **تعديل عمولة الإحالة**\n\nالنسبة الحالية: {current_commission}%\n💡 هذه النسبة تضاف من عمولة الكاشير لحساب المحيل\n\nأدخل النسبة الجديدة (مثال 2 لـ 2%):", parse_mode="Markdown")
    return ADMIN_EDIT_REFERRAL_COMMISSION


async def admin_referral_commission_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام عمولة الإحالة الجديدة"""
    try:
        new_commission = float(update.message.text.strip())
        if new_commission < 0 or new_commission > 100:
            await update.message.reply_text("❌ يجب أن تكون النسبة بين 0 و 100:")
            return ADMIN_EDIT_REFERRAL_COMMISSION

        set_referral_settings(referral_commission=new_commission)
        await update.message.reply_text(f"✅ تم تحديث عمولة الإحالة إلى: {new_commission}%", reply_markup=get_admin_settings_keyboard())
    except ValueError:
        await update.message.reply_text("❌ رقم غير صحيح. أدخل رقماً:")
        return ADMIN_EDIT_REFERRAL_COMMISSION

    return ConversationHandler.END


# ==================== إدارة طرق الدفع ====================


async def admin_manage_deposit_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة طرق الإيداع"""
    query = update.callback_query
    await query.answer()

    settings = get_payment_settings()
    deposit_methods = settings.get("deposit_methods", [])

    msg = "💰 **إدارة طرق الإيداع**\n\n"

    if not deposit_methods:
        msg += "لا توجد طرق إيداع حالياً.\n"
    else:
        for method in deposit_methods:
            msg += f"✅ {method['display_name']}\n"

    msg += "\nانقر على الطريقة لتفعيل/تعطيلها:"

    buttons = []
    for method in deposit_methods:
        buttons.append([InlineKeyboardButton(f"{'🟢 تفعيل' if method.get('active', True) else '🔴 تعطيل'} {method['display_name']}", callback_data=f"toggle_deposit_method_{method['method_name']}")])

    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_payment_methods")])

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def admin_manage_withdrawal_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة طرق السحب"""
    query = update.callback_query
    await query.answer()

    settings = get_payment_settings()
    withdrawal_methods = settings.get("withdrawal_methods", [])

    msg = "💳 **إدارة طرق السحب**\n\n"

    if not withdrawal_methods:
        msg += "لا توجد طرق سحب حالياً.\n"
    else:
        for method in withdrawal_methods:
            msg += f"✅ {method['display_name']}\n"

    msg += "\nانقر على الطريقة لتفعيل/تعطيلها:"

    buttons = []
    for method in withdrawal_methods:
        buttons.append([InlineKeyboardButton(f"{'🟢 تفعيل' if method.get('active', True) else '🔴 تعطيل'} {method['display_name']}", callback_data=f"toggle_withdrawal_method_{method['method_name']}")])

    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_payment_methods")])

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def admin_toggle_deposit_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل حالة طريقة الإيداع"""
    query = update.callback_query
    await query.answer()

    method_name = query.data.replace("toggle_deposit_method_", "")
    settings = get_payment_settings()
    deposit_methods = settings.get("deposit_methods", [])

    current_method = None
    for method in deposit_methods:
        if method["method_name"] == method_name:
            current_method = method
            break

    if current_method:
        new_status = not current_method.get("active", True)
        update_payment_method(method_name, "deposit", is_active=new_status)
        await admin_manage_deposit_methods(update, context)
    else:
        await query.edit_message_text("❌ لم يتم العثور على الطريقة")


async def admin_toggle_withdrawal_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل حالة طريقة السحب"""
    query = update.callback_query
    await query.answer()

    method_name = query.data.replace("toggle_withdrawal_method_", "")
    settings = get_payment_settings()
    withdrawal_methods = settings.get("withdrawal_methods", [])

    current_method = None
    for method in withdrawal_methods:
        if method["method_name"] == method_name:
            current_method = method
            break

    if current_method:
        new_status = not current_method.get("active", True)
        update_payment_method(method_name, "withdrawal", is_active=new_status)
        await admin_manage_withdrawal_methods(update, context)
    else:
        await query.edit_message_text("❌ لم يتم العثور على الطريقة")


# ==================== إدارة عناوين المحفظة ====================


async def admin_show_wallet_addresses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض وتعديل عناوين المحفظة"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()

    msg = "📫 **إدارة عناوين المحفظة**\n\n"

    msg += "💼 **سيرتل كاش:**\n"
    msg += f"   الرقم 1: `{addresses['sertel_cash_1']}`\n"
    msg += f"   الرقم 2: `{addresses['sertel_cash_2']}`\n\n"

    msg += "💻 **شام كاش ليرة:**\n"
    msg += f"   الرقم 1: `{addresses['sham_lira_1']}`\n"
    msg += f"   الرقم 2: `{addresses['sham_lira_2']}`\n\n"

    msg += "💼 **شام كاش دولار:**\n"
    msg += f"   الرقم 1: `{addresses['sham_dollar_1']}`\n"
    msg += f"   الرقم 2: `{addresses['sham_dollar_2']}`\n\n"

    msg += "💵 **عملات رقمية (USDT TRC20):**\n"
    msg += f"   العنوان: `{addresses['usdt_trc20_address']}`\n\n"

    msg += "اختر الرقم/العنوان لتعديله:"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ سيرتل كاش #1", callback_data="edit_sertel_cash_1")],
        [InlineKeyboardButton("✏️ سيرتل كاش #2", callback_data="edit_sertel_cash_2")],
        [InlineKeyboardButton("✏️ شام كاش ليرة #1", callback_data="edit_sham_lira_1")],
        [InlineKeyboardButton("✏️ شام كاش ليرة #2", callback_data="edit_sham_lira_2")],
        [InlineKeyboardButton("✏️ شام كاش دولار #1", callback_data="edit_sham_dollar_1")],
        [InlineKeyboardButton("✏️ شام كاش دولار #2", callback_data="edit_sham_dollar_2")],
        [InlineKeyboardButton("✏️ عنوان USDT", callback_data="edit_usdt_address")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings_menu")],
    ])

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def admin_edit_sertel_cash_1_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل رقم سيرتل كاش الأول"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()
    current = addresses.get("sertel_cash_1", "غير مضبوط")

    await query.edit_message_text(f"✏️ **تعديل رقم سيرتل كاش #1**\n\nالرقم الحالي: `{current}`\n\nأدخل الرقم الجديد:", parse_mode="Markdown")
    return ADMIN_EDIT_SERTEL_CASH_1


async def admin_sertel_cash_1_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رقم سيرتل كاش الأول الجديد"""
    new_number = update.message.text.strip()
    if len(new_number) < 3:
        await update.message.reply_text("❌ الرقم قصير جداً. أدخل رقماً صحيحاً:")
        return ADMIN_EDIT_SERTEL_CASH_1

    update_wallet_addresses(sertel_cash_1=new_number)
    await update.message.reply_text(f"✅ تم تحديث رقم سيرتل كاش #1 إلى: `{new_number}`", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_edit_sertel_cash_2_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل رقم سيرتل كاش الثاني"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()
    current = addresses.get("sertel_cash_2", "غير مضبوط")

    await query.edit_message_text(f"✏️ **تعديل رقم سيرتل كاش #2**\n\nالرقم الحالي: `{current}`\n\nأدخل الرقم الجديد:", parse_mode="Markdown")
    return ADMIN_EDIT_SERTEL_CASH_2


async def admin_sertel_cash_2_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رقم سيرتل كاش الثاني الجديد"""
    new_number = update.message.text.strip()
    if len(new_number) < 3:
        await update.message.reply_text("❌ الرقم قصير جداً. أدخل رقماً صحيحاً:")
        return ADMIN_EDIT_SERTEL_CASH_2

    update_wallet_addresses(sertel_cash_2=new_number)
    await update.message.reply_text(f"✅ تم تحديث رقم سيرتل كاش #2 إلى: `{new_number}`", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_edit_sham_lira_1_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل رقم شام كاش ليرة الأول"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()
    current = addresses.get("sham_lira_1", "غير مضبوط")

    await query.edit_message_text(f"✏️ **تعديل رقم شام كاش ليرة #1**\n\nالرقم الحالي: `{current}`\n\nأدخل الرقم الجديد:", parse_mode="Markdown")
    return ADMIN_EDIT_SHAM_LIRA_1


async def admin_sham_lira_1_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رقم شام كاش ليرة الأول الجديد"""
    new_number = update.message.text.strip()
    if len(new_number) < 3:
        await update.message.reply_text("❌ الرقم قصير جداً. أدخل رقماً صحيحاً:")
        return ADMIN_EDIT_SHAM_LIRA_1

    update_wallet_addresses(sham_lira_1=new_number)
    await update.message.reply_text(f"✅ تم تحديث رقم شام كاش ليرة #1 إلى: `{new_number}`", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_edit_sham_lira_2_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل رقم شام كاش ليرة الثاني"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()
    current = addresses.get("sham_lira_2", "غير مضبوط")

    await query.edit_message_text(f"✏️ **تعديل رقم شام كاش ليرة #2**\n\nالرقم الحالي: `{current}`\n\nأدخل الرقم الجديد:", parse_mode="Markdown")
    return ADMIN_EDIT_SHAM_LIRA_2


async def admin_sham_lira_2_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رقم شام كاش ليرة الثاني الجديد"""
    new_number = update.message.text.strip()
    if len(new_number) < 3:
        await update.message.reply_text("❌ الرقم قصير جداً. أدخل رقماً صحيحاً:")
        return ADMIN_EDIT_SHAM_LIRA_2

    update_wallet_addresses(sham_lira_2=new_number)
    await update.message.reply_text(f"✅ تم تحديث رقم شام كاش ليرة #2 إلى: `{new_number}`", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_edit_sham_dollar_1_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل رقم شام كاش دولار الأول"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()
    current = addresses.get("sham_dollar_1", "غير مضبوط")

    await query.edit_message_text(f"✏️ **تعديل رقم شام كاش دولار #1**\n\nالرقم الحالي: `{current}`\n\nأدخل الرقم الجديد:", parse_mode="Markdown")
    return ADMIN_EDIT_SHAM_DOLLAR_1


async def admin_sham_dollar_1_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رقم شام كاش دولار الأول الجديد"""
    new_number = update.message.text.strip()
    if len(new_number) < 3:
        await update.message.reply_text("❌ الرقم قصير جداً. أدخل رقماً صحيحاً:")
        return ADMIN_EDIT_SHAM_DOLLAR_1

    update_wallet_addresses(sham_dollar_1=new_number)
    await update.message.reply_text(f"✅ تم تحديث رقم شام كاش دولار #1 إلى: `{new_number}`", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_edit_sham_dollar_2_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل رقم شام كاش دولار الثاني"""
    query = update.callback_query
    await query.answer()

    addresses = get_wallet_addresses()
    current = addresses.get("sham_dollar_2", "غير مضبوط")

    await query.edit_message_text(f"✏️ **تعديل رقم شام كاش دولار #2**\n\nالرقم الحالي: `{current}`\n\nأدخل الرقم الجديد:", parse_mode="Markdown")
    return ADMIN_EDIT_SHAM_DOLLAR_2


async def admin_sham_dollar_2_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رقم شام كاش دولار الثاني الجديد"""
    new_number = update.message.text.strip()
    if len(new_number) < 3:
        await update.message.reply_text("❌ الرقم قصير جداً. أدخل رقماً صحيحاً:")
        return ADMIN_EDIT_SHAM_DOLLAR_2

    update_wallet_addresses(sham_dollar_2=new_number)
    await update.message.reply_text(f"✅ تم تحديث رقم شام كاش دولار #2 إلى: `{new_number}`", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def admin_edit_usdt_address_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل عنوان USDT"""
    query = update.callback_query
    await query.answer()

    from database import get_crypto_wallet_addresses

    wallets = get_crypto_wallet_addresses()

    await query.edit_message_text(
        f"✏️ **تعديل عنوان المحفظة الرقمية**\n\n"
        f"💵 **TRC20 (USDT):**\n`{wallets.get('trc20', 'غير مضبوط')}`\n\n"
        f"💵 **ERC20 (USDT):**\n`{wallets.get('erc20', 'غير مضبوط')}`\n\n"
        f"💵 **Polygon (USDT):**\n`{wallets.get('polygon', 'غير مضبوط')}`\n\n"
        f"💵 **Matic (USDT):**\n`{wallets.get('matic', 'غير مضبوط')}`\n\n"
        f"أدخل العناوين الجديدة مفصولة بفواصل:\n"
        f"TRC20, ERC20, Polygon, Matic\n\n"
        f"مثال:\n`TAddress1,0xAddress2,0xAddress3,0xAddress4`",
        parse_mode="Markdown",
    )
    return ADMIN_EDIT_USDT_ADDRESS


async def admin_usdt_address_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام عناوين USDT الجديدة"""
    addresses_text = update.message.text.strip()

    addresses = [addr.strip() for addr in addresses_text.split(",")]

    if len(addresses) != 4:
        await update.message.reply_text("❌ يجب إدخال 4 عناوين مفصولة بفواصل!\n\nالترتيب: TRC20, ERC20, Polygon, Matic")
        return ADMIN_EDIT_USDT_ADDRESS

    trc20, erc20, polygon, matic = addresses

    if len(trc20) < 10 or len(erc20) < 10 or len(polygon) < 10 or len(matic) < 10:
        await update.message.reply_text("❌ بعض العناوين قصيرة جداً. أدخل عناوين صحيحة:")
        return ADMIN_EDIT_USDT_ADDRESS

    from database import update_crypto_wallet_addresses

    update_crypto_wallet_addresses(trc20=trc20, erc20=erc20, polygon=polygon, matic=matic)

    await update.message.reply_text(f"✅ **تم تحديث عناوين المحفظة الرقمية بنجاح!**\n\n💵 **TRC20:** `{trc20}`\n💵 **ERC20:** `{erc20}`\n💵 **Polygon:** `{polygon}`\n💵 **Matic:** `{matic}`\n", parse_mode="Markdown", reply_markup=get_admin_settings_keyboard())
    return ConversationHandler.END


async def invite_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدخال اسم المستخدم للدعوة"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("👥 **دعوة عبر تلغرام**\n\nأدخل اسم المستخدم (username) في تلغرام لدعوته\nمثال: @ahmad_khaled", parse_mode="Markdown", reply_markup=get_back_keyboard("invite_menu"))
    return INVITE_USERNAME


async def invite_username_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام اسم المستخدم للدعوة"""
    username = update.message.text.strip()

    if not username or len(username) < 3:
        await update.message.reply_text("❌ الاسم قصير جداً. أدخل اسماً صحيحاً (مع @ أو بدونه):")
        return INVITE_USERNAME

    if not username.startswith("@"):
        username = "@" + username

    bot_link = f"https://t.me/{context.bot.username}"

    invite_message = (
        f"🎃 **دعوة في Ichancy!**\n\n"
        f"دعاك {update.effective_user.first_name} للانضمام إلى منصتنا!\n\n"
        f"🐵 سجل الآن واحصل على مكافأة ترحيبية!\n"
        f"💵 ابدأ اللعبة واربح اليوم!\n\n"
        f"{bot_link}"
    )

    try:
        await context.bot.send_message(username, invite_message, parse_mode="Markdown")
        await update.message.reply_text(f"✅ تم إرسال الدعوة بنجاح إلى {username}\n\nشكراً لك على دعوة أصدقائك! 🐵", reply_markup=get_back_keyboard("invite_menu"))
    except Exception as e:
        await update.message.reply_text(f"❌ فشل إرسال الدعوة: {str(e)}\n\nتأكد من أن المستخدم {username} موجود ويمكنه استقبال الرسائل.", reply_markup=get_back_keyboard("invite_menu"))

    return ConversationHandler.END


# كوبونات
async def coupon_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🐵 **مكافأة ترحيبية**\n\n🎀 احصل على مكافأة 10% على أول إيداع!\n\n💡 استخدم الكود التالي عند الإيداع:\n<code>WELCOME10</code>\n\n💡 يسري على أول إيداع فقط!", parse_mode="HTML", reply_markup=get_back_keyboard("coupons_menu"))


async def coupon_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🎀 **مكافأة هدية**\n\n🐵 مكافأة 5% على كل إيداع!\n\n💡 استخدم الكود التالي عند الإيداع:\n<code>GIFT5</code>\n\n💡 يسري على جميع الإيداعات!", parse_mode="HTML", reply_markup=get_back_keyboard("coupons_menu"))


async def coupon_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🎟 **مكافأة إيداع**\n\n💵 احصل على 5% إضافية على كل إيداع!\n\n💡 استخدم الكود التالي عند الإيداع:\n<code>CHARGE5</code>\n\n💡 يسري على جميع الإيداعات!", parse_mode="HTML", reply_markup=get_back_keyboard("coupons_menu"))


if __name__ == "__main__":
    main()
