import requests, random , string, sqlite3
from decouple import config
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, ApplicationBuilder, ContextTypes, CallbackQueryHandler, filters
from telegram.ext.filters import TEXT
from telegram.constants import ParseMode
import asyncio  # اضافه کردن برای استفاده از sleep

TOKEN = config('TOKEN')
CHANNELS = {}  # تغییر به یک دیکشنری برای ذخیره {نام کانال: لینک کانال}
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
ADMIN_IDs = [5050906432, 8072841447, 1725178616]  # ایدی ادمین را وارد کنید
ADMIN_ID = [5050906432]  # ایدی ادمین را وارد کنید
# متغیر برای ذخیره پیام کانال
CHANNEL_MESSAGE_ID = None  # آی‌دی پیام کانال

# ذخیره پیام موقت برای ارسال
ADMIN_MESSAGES = {}
# users = set()  # لیست کاربران برای ارسال پیام
# شناسه کانال منبع
source_channel = -1002384637392  # کانال منبع که پیام‌ها از آن فوروارد می‌شوند
user_states = {}

FILE_NAME = "users.txt"
# اتصال به دیتابیس
conn = sqlite3.connect("files.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_identifier TEXT NOT NULL UNIQUE
)
""")
conn.commit()

# تابع تولید شناسه یکتای فایل
def generate_file_identifier():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

# تابعی برای ذخیره آی‌دی کاربران
def save_user_id(user_id):
    try:
        # باز کردن فایل و خواندن آی‌دی‌ها
        with open(FILE_NAME, "r") as file:
            user_ids = file.read().splitlines()
    except FileNotFoundError:
        # اگر فایل وجود نداشت، یک لیست خالی می‌سازیم
        user_ids = []

    # بررسی اگر آی‌دی در فایل وجود ندارد، آن را ذخیره کنیم
    if str(user_id) not in user_ids:
        with open(FILE_NAME, "a") as file:
            file.write(f"{user_id}\n")
    #     print(f"User ID {user_id} saved.")
    # else:
    #     print(f"User ID {user_id} already exists.")

# بررسی عضویت کاربر
async def check_user_subscription(user_id):
    for channel_link in CHANNELS.values():
        url = f"{TELEGRAM_API_URL}/getChatMember?chat_id={channel_link}&user_id={user_id}"
        response = requests.get(url).json()
        try:
            status = response['result']['status']
            if status not in ['member', 'administrator', 'creator']:
                return False
        except KeyError:
            return False
    return True

# بررسی ادمین بودن کاربر
def is_admin(user_id):
    return user_id in ADMIN_IDs


# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user_id(user_id)  # ذخیره ID کاربر
    args = context.args

    if await check_user_subscription(user_id):
        if len(args) == 1:
            file_identifier = args[0]

            # ارسال درخواست فایل به صورت غیر همزمان برای هر کاربر
            asyncio.create_task(handle_file_request(update, context, file_identifier))
        else:
            await update.message.reply_text("سلام عزیز !")
    else:
        keyboard = [
            [InlineKeyboardButton(f"عضویت در {name}", url=f"https://t.me/{link[1:]}")]
            for name, link in CHANNELS.items()
        ]
        keyboard.append([InlineKeyboardButton("بررسی عضویت", callback_data="check_subscription")])  # دکمه بررسی عضویت
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔔 لطفاً ابتدا در کانال‌های زیر عضو شوید:\n سپس دوباره روی لینک کلیک کنید",
            reply_markup=reply_markup
        )

# تابع مدیریت درخواست فایل
async def handle_file_request(update: Update, context: ContextTypes.DEFAULT_TYPE, file_identifier: str):
    # ارسال پیام اولیه با دکمه اینلاین
    keyboard = [
        [InlineKeyboardButton("مشاهده کانال", url="https://t.me/+oIqjq1ClWKM0Y2M0")]  # لینک کانال خود را وارد کنید
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "لطفاً 5 پست آخر کانال را مشاهده کنید، سپس فایل به صورت خودکار برای شما ارسال خواهد شد.",
        reply_markup=reply_markup
    )

    # افزودن حالت انتظار برای ۱۵ ثانیه
    await asyncio.sleep(15)

    # جستجوی فایل در دیتابیس بر اساس شناسه یکتا
    cursor.execute("SELECT file_id, file_type FROM files WHERE file_identifier = ?", (file_identifier,))
    result = cursor.fetchone()

    if result:
        file_id, file_type = result

        # ارسال فایل به کاربر بر اساس نوع آن
        if file_type == "photo":
            sent_message = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=file_id, caption="""برای دانلود فیلم‌های بیشتر عضو چنل زیر شوید:

🆔  @Pussi_bang                   🆔 @Pussi_bang""")
        elif file_type == "video":
            sent_message = await context.bot.send_video(chat_id=update.effective_chat.id, video=file_id, caption="""برای دانلود فیلم‌های بیشتر عضو چنل زیر شوید:

🆔  @Pussi_bang                   🆔 @Pussi_bang""")
        elif file_type == "audio":
            sent_message = await context.bot.send_audio(chat_id=update.effective_chat.id, audio=file_id, caption="""برای دانلود فیلم‌های بیشتر عضو چنل زیر شوید:

🆔  @Pussi_bang                   🆔 @Pussi_bang""")
        elif file_type == "document":
            sent_message = await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id, caption="""برای دانلود فیلم‌های بیشتر عضو چنل زیر شوید:

🆔  @Pussi_bang                   🆔 @Pussi_bang""")
        
        await context.bot.send_message(
                chat_id= update._effective_user.id,
                text='این فایل‌ها پس از 30 ثانیه حذف خواهند شد\nلطفاً در سیو مسیج خود ذخیره کنید.'
            )
        # ایجاد تسک برای حذف فایل بعد از 30 ثانیه
        asyncio.create_task(delete_file_after_timeout(sent_message))
    else:
        await update.message.reply_text("فایل مورد نظر پیدا نشد.")


# تابع حذف فایل پس از 30 ثانیه
async def delete_file_after_timeout(sent_message):
    await asyncio.sleep(30)  # صبر کردن برای 30 ثانیه
    try:
        # حذف فایل ارسال شده از چت
        await sent_message.delete()
    except Exception as e:
        print(f"خطا در حذف فایل: {e}")


# مدیریت دکمه بررسی عضویت
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if await check_user_subscription(user_id):
        # اگر عضو بود، دستور start با پارامتر دوباره اجرا می‌شود
        start_data = context.user_data.get("start_data", None)
        if start_data:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"/start {start_data}"
            )
        else:
            await query.edit_message_text("✅ شما عضو کانال‌ها هستید. حالا دوباره روی لینک پست کلیک کنید.")
    else:
        # اگر عضو نبود
        await context.bot.send_message(chat_id=query.message.chat_id,
                                       text="❌ شما هنوز در کانال‌ها عضو نشده‌اید. لطفاً ابتدا عضو شوید.")

# دستور /addch برای ادمین
async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("افزودن کانال", callback_data="add_channel")],
            [InlineKeyboardButton("حذف کانال", callback_data="remove_channel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("لطفاً یک گزینه را انتخاب کنید:", reply_markup=reply_markup)
    else:
        await update.message.reply_text('⛔ فقط ادمین‌ها اجازه استفاده از این دستور را دارند.')

# افزودن کانال
async def add_channel_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("لطفاً نام کانال را وارد کنید:")

    # انتظار برای نام کانال
    context.user_data["action"] = "adding_channel"

# دریافت نام و لینک کانال برای افزودن
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = context.user_data.get("action")

    if action == "adding_channel":
        channel_name = update.message.text
        context.user_data["channel_name"] = channel_name
        await update.message.reply_text(f"نام کانال '{channel_name}' دریافت شد. حالا لینک کانال را وارد کنید:")
        context.user_data["action"] = "adding_channel_link"

    elif action == "adding_channel_link":
        channel_link = update.message.text
        channel_name = context.user_data.get("channel_name")
        CHANNELS[channel_name] = channel_link  # افزودن به دیکشنری
        await update.message.reply_text(f"کانال '{channel_name}' با لینک {channel_link} اضافه شد.")
        context.user_data.clear()

# حذف کانال
async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"remove_{name}") for name in CHANNELS.keys()]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "لطفاً کانالی که می‌خواهید حذف کنید را انتخاب کنید:",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("⛔ فقط ادمین‌ها اجازه استفاده از این دستور را دارند.")

# حذف کانال از لیست
async def handle_remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    channel_name = query.data.split("_", 1)[1]
    if channel_name in CHANNELS:
        del CHANNELS[channel_name]  # حذف از دیکشنری
        await query.edit_message_text(f"کانال '{channel_name}' از لیست حذف شد.")
    else:
        await query.edit_message_text("کانال مورد نظر یافت نشد.")


# دستور /mes برای دریافت پیام از ادمین
async def mes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_id not in ADMIN_ID:
        await update.message.reply_text("⛔ فقط ادمین‌ها اجازه استفاده از این دستور را دارند.")
        return

    await update.message.reply_text("لطفاً آی‌دی عددی پیام را وارد کنید:")

    # ذخیره وضعیت انتظار دریافت آی‌دی عددی پیام
    context.user_data['waiting_for_message_id'] = True

# دریافت آی‌دی پیام و ارسال به کاربران
async def handle_message_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    with open(FILE_NAME, "r") as file:
            user_ids = file.read().splitlines()

    if context.user_data.get('waiting_for_message_id', False) and user_id in ADMIN_ID:
        # پایان حالت انتظار
        context.user_data['waiting_for_message_id'] = False

        # آی‌دی عددی پیام وارد شده
        try:
            message_id = int(update.message.text)  # تبدیل به عدد
        except ValueError:
            await update.message.reply_text("⛔ آی‌دی پیام وارد شده معتبر نیست. لطفاً یک عدد وارد کنید.")
            return

        try:
            # کپی کردن پیام از کانال مشخص‌شده
            from_chat_id = -1002218489604  # نام کاربری کانال خود را اینجا وارد کنید
            original_message = await context.bot.forward_message(
                chat_id=ADMIN_ID[0],  # پیام به یک ادمین فرستاده شود تا بتوانیم جزئیات آن را بررسی کنیم
                from_chat_id=from_chat_id,
                message_id=message_id
            )

            # بازسازی پیام و ارسال به کاربران
            sent_count = 0
            for user in user_ids:
                try:
                    # بازسازی پیام بر اساس نوع (متن، عکس، فایل و ...)
                    if original_message.text:
                        await context.bot.send_message(
                            chat_id=user,
                            text=original_message.text,
                            reply_markup=original_message.reply_markup,
                            parse_mode=ParseMode.HTML,
                        )
                    elif original_message.photo:
                        await context.bot.send_photo(
                            chat_id=user,
                            photo=original_message.photo[-1].file_id,  # بزرگ‌ترین سایز عکس
                            caption=original_message.caption,
                            reply_markup=original_message.reply_markup,
                            parse_mode=ParseMode.HTML,
                        )
                    elif original_message.document:
                        await context.bot.send_document(
                            chat_id=user,
                            document=original_message.document.file_id,
                            caption=original_message.caption,
                            reply_markup=original_message.reply_markup,
                            parse_mode=ParseMode.HTML,
                        )
                    # ارسال سایر انواع پیام‌ها (مثلاً ویدیو، صدا و ...) را نیز می‌توانید اضافه کنید

                    sent_count += 1
                    await asyncio.sleep(1)  # رعایت محدودیت API تلگرام (1 پیام در ثانیه)
                except Exception as e:
                    print(f"خطا در ارسال پیام به کاربر {user}: {e}")

            await update.message.reply_text(f"✅ پیام با موفقیت به {sent_count} کاربر ارسال شد.")

        except Exception as e:
            await update.message.reply_text(f"⛔ خطا در دریافت یا ارسال پیام: {e}")


# اگر ادمین دستور را لغو کرد
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['waiting_for_message_id'] = False
    await update.message.reply_text("❌ عملیات لغو شد.")


# دستور /send
async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):    
        await update.message.reply_text("لطفاً فایل مورد نظر خود را ارسال کنید (عکس، ویدیو یا آهنگ).")
    else:
        await update.message.reply_text('⛔ فقط ادمین‌ها اجازه استفاده از این دستور را دارند.')

# مدیریت فایل‌های ارسال شده
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):     
        file_id = None
        file_type = None

        # بررسی نوع فایل و گرفتن file_id
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            file_type = "photo"
        elif update.message.video:
            file_id = update.message.video.file_id
            file_type = "video"
        elif update.message.audio:
            file_id = update.message.audio.file_id
            file_type = "audio"
        elif update.message.document:
            file_id = update.message.document.file_id
            file_type = "document"

        if file_id and file_type:
            # بررسی وجود فایل تکراری در دیتابیس
            cursor.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
            existing_file = cursor.fetchone()

            if existing_file:
                # اگر فایل قبلاً موجود بود
                await update.message.reply_text("این فایل قبلاً ارسال شده است.")
            else:
                # تولید شناسه یکتا برای فایل
                file_identifier = generate_file_identifier()

                # ذخیره اطلاعات فایل در دیتابیس
                cursor.execute("INSERT INTO files (file_id, file_type, file_identifier) VALUES (?, ?, ?)",
                            (file_id, file_type, file_identifier))
                conn.commit()

                # ایجاد لینک دانلود بر اساس شناسه فایل
                link = f"https://t.me/{context.bot.username}?start={file_identifier}"

                # ارسال پیام به صورت ریپلای
                await update.message.reply_text(
                    f"فایل شما دریافت شد!\nلینک فایل شما:\n{link}",
                    reply_to_message_id=update.message.message_id
                )
        else:
            await update.message.reply_text("نوع فایل پشتیبانی نمی‌شود.")
    else:
        await update.message.reply_text('سلام عزیز !')
        
# دستور /list
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        # گرفتن تعداد فایل‌ها بر اساس نوع
        cursor.execute("SELECT file_type, COUNT(*) FROM files GROUP BY file_type")
        file_counts = cursor.fetchall()

        if not file_counts:
            await update.message.reply_text("هیچ فایلی ذخیره نشده است.")
            return

        # پیام تعداد فایل‌ها
        message_text = "تعداد فایل‌ها:\n"
        for file_type, count in file_counts:
            message_text += f"{file_type.capitalize()} : {count} \n"

        # ایجاد کیبورد اینلاین
        keyboard = [
            [InlineKeyboardButton("فیلم‌ها", callback_data="video"),
            InlineKeyboardButton("عکس‌ها", callback_data="photo"),
            InlineKeyboardButton("آهنگ‌ها", callback_data="audio"),
            InlineKeyboardButton("مستندات", callback_data="document")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # ارسال پیام همراه با کیبورد
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text('⛔ فقط ادمین‌ها اجازه استفاده از این دستور را دارند.')    

# تابع مدیریت کلیک روی دکمه‌های اینلاین
async def handle_inline_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    file_type = query.data

    # جستجوی فایل‌ها بر اساس نوع
    cursor.execute("SELECT file_identifier FROM files WHERE file_type = ?", (file_type,))
    files = cursor.fetchall()

    if not files:
        await query.answer("هیچ فایلی برای این نوع موجود نیست.")
        return

    # ایجاد لینک‌ها برای فایل‌ها
    file_links = [f"https://t.me/{context.bot.username}?start={file[0]}\n" for file in files]

    # ارسال لینک‌ها به صورت جداگانه در چندین پیام
    max_files_per_message = 5  # حداکثر تعداد فایل‌ها در یک پیام
    for i in range(0, len(file_links), max_files_per_message):
        await query.message.reply_text("\n".join(file_links[i:i + max_files_per_message]))

    await query.answer()



# اجرای ربات
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # افزودن هندلرهای مربوط به کامندها
    app.add_handler(CommandHandler("start", start, filters=filters.TEXT & filters.Regex(r"^/start .*")))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addch", add_channel))
    app.add_handler(CommandHandler("mes", mes))
    app.add_handler(CommandHandler("send", send))
    app.add_handler(CommandHandler("list", list_files))

    # هندلرهای مربوط به کال‌بک‌ها
    app.add_handler(CallbackQueryHandler(add_channel_name, pattern="add_channel"))
    app.add_handler(CallbackQueryHandler(remove_channel, pattern="remove_channel"))
    app.add_handler(CallbackQueryHandler(handle_remove_channel, pattern="remove_"))

    # هندلرهای مربوط به پیام‌ها
    # فیلتر برای پیام‌های عمومی
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^\d+$"), handle_message))

    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, handle_file))

    # فیلتر برای پیام‌هایی که فقط شامل اعداد هستند
    app.add_handler(MessageHandler(filters.Regex(r"^\d+$"), handle_message_id))
    app.add_handler(CallbackQueryHandler(check_subscription, pattern="check_subscription"))

    app.add_handler(CallbackQueryHandler(handle_inline_button))



    print("Bot is Running...")
    app.run_polling()
