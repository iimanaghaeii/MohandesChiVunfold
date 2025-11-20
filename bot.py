# bot_mohandes_chi_optimized_v3_FINAL_WITH_DELETE.py
import asyncio
import sqlite3
import time
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.config import BOT_TOKEN, CHANNEL_USERNAME

DB_PATH = "bot_mohandes_chi.db"

# دیکشنری موقت برای نگهداری پیام‌های فوروارد شده و پیام سوال (برای حذف بعدی)
# ساختار: {user_id: {post_id: (forwarded_message_id, prompt_message_id)}}
forwarded_messages = {}

# ===================================================================
# بخش ۱: توابع دیتابیس (SQLite)
# ===================================================================
def init_db():
    """ایجاد دیتابیس و جداول لازم در صورت عدم وجود"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # جدول کاربران
    cur.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_seen INTEGER)""")
    # جدول آخرین ۳ پست کانال (slot 1,2,3)
    cur.execute("""CREATE TABLE IF NOT EXISTS last_posts (slot INTEGER PRIMARY KEY, post_id INTEGER)""")
    # جدول دیده‌شده‌ها (هر کاربر چه پست‌هایی رو دیده)
    cur.execute("""CREATE TABLE IF NOT EXISTS seen (user_id INTEGER, post_id INTEGER, seen_at INTEGER,
                PRIMARY KEY (user_id, post_id))""")
    conn.commit()
    conn.close()

def save_last_posts_list(post_ids):
    """ذخیره آخرین ۳ پست کانال در دیتابیس (جایگزین قبلی‌ها)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM last_posts")
    for idx, pid in enumerate(post_ids[:3], start=1):
        cur.execute("INSERT INTO last_posts (slot, post_id) VALUES (?, ?)", (idx, int(pid)))
    conn.commit()
    conn.close()

def load_last_posts_list():
    """بارگذاری آخرین ۳ پست کانال از دیتابیس (به ترتیب slot)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT post_id FROM last_posts ORDER BY slot ASC")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def add_user_if_not_exists(user_id):
    """اضافه کردن کاربر جدید به دیتابیس (فقط اولین بار)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, first_seen) VALUES (?, ?)",
                (user_id, int(time.time())))
    conn.commit()
    conn.close()

def get_all_users():
    """دریافت لیست تمام کاربرهایی که تا حالا با ربات حرف زدن"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def mark_seen(user_id, post_id):
    """ثبت اینکه کاربر فلان پست رو دیده (یا حذف کرده)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO seen (user_id, post_id, seen_at) VALUES (?, ?, ?)",
                (user_id, post_id, int(time.time())))
    conn.commit()
    conn.close()

def get_seen_for_user(user_id):
    """لیست پست‌هایی که این کاربر دیده رو برمی‌گردونه"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT post_id FROM seen WHERE user_id=?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

# ===================================================================
# بخش ۲: راه‌اندازی ربات و توابع کمکی
# ===================================================================
init_db()  # ایجاد دیتابیس در ابتدای اجرا
bot = AsyncTeleBot(BOT_TOKEN)

def create_seen_buttons(post_id):
    """ساخت دکمه‌های زیر هر پست فوروارد شده: «مشاهده شد» و «دیدم، پاکش کن»"""
    markup = InlineKeyboardMarkup()
    btn_seen = InlineKeyboardButton("✅ مشاهده شد", callback_data=f"seen_{post_id}")
    btn_delete = InlineKeyboardButton("🗑 دیدم، پاکش کن", callback_data=f"delete_{post_id}")
    markup.row(btn_seen, btn_delete)
    return markup

async def is_member(bot_obj, user_id):
    """چک کردن عضویت کاربر در کانال اجباری"""
    try:
        res = await bot_obj.get_chat_member(CHANNEL_USERNAME, user_id)
        return res.status not in ['left', 'kicked']
    except:
        return False

# دیکشنری وضعیت کاربران (برای عملیات چندمرحله‌ای مثل جمع دو عدد)
user_states = {}  # user_id -> {'action': 'sum', 'nums': []}

async def core_main(user_id):
    """نمایش منوی اصلی ربات بعد از اینکه کاربر همه پست‌ها رو دید"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("جمع دو عدد"))
    await bot.send_message(
        user_id,
        "تبریک! حالا می‌توانید از امکانات ربات استفاده کنید.",
        reply_markup=markup
    )

# ===================================================================
# بخش ۳: دریافت پست جدید از کانال و ارسال به همه کاربران
# ===================================================================
@bot.channel_post_handler(func=lambda m: True)
async def handle_channel_post(message):
    """
    هر وقت پستی در کانال ارسال بشه، این تابع اجرا میشه:
    - آخرین ۳ پست رو آپدیت می‌کنه
    - به همه کاربرانی که اون پست رو ندیدن، فوروارد می‌کنه + سوال
    """
    msg_id = message.message_id
    current = load_last_posts_list()
    new_list = [msg_id] + [p for p in current if p != msg_id]
    save_last_posts_list(new_list[:3])

    users = get_all_users()
    for user_id in users:
        seen = get_seen_for_user(user_id)
        remain = [p for p in new_list if p not in seen]
        for pid in remain:
            try:
                fwd = await bot.forward_message(user_id, CHANNEL_USERNAME, pid)
                prompt = await bot.send_message(
                    user_id,
                    "پست بالا را مشاهده کرده‌اید؟",
                    reply_markup=create_seen_buttons(pid)
                )
                forwarded_messages.setdefault(user_id, {})[pid] = (fwd.message_id, prompt.message_id)
            except Exception as e:
                # اگر کاربر بلاک کرده یا مشکلی باشه، رد می‌شیم
                pass

# ===================================================================
# بخش ۴: پردازش تمام پیام‌های کاربران
# ===================================================================
@bot.message_handler(func=lambda m: True)
async def all_messages(message):
    """
    هندلر اصلی تمام پیام‌ها:
    ۱. کاربر رو ثبت می‌کنه
    ۲. چک می‌کنه عضو کانال هست یا نه
    ۳. اگر پست ندیده داشته باشه، مجبورش می‌کنه اول ببینه
    ۴. در غیر اینصورت منوی اصلی رو نشون میده
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text or ""

    add_user_if_not_exists(user_id)

    # اگر کاربر در حال انجام عملیات جمع دو عدد باشه
    if user_id in user_states and user_states[user_id]["action"] == "sum":
        return await sum_two_numbers_receive(message)

    # چک کردن عضویت در کانال
    if not await is_member(bot, user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"),
            types.InlineKeyboardButton("عضو شدم", callback_data="check_membership")
        )
        return await bot.send_message(
            chat_id,
            "برای استفاده از ربات ابتدا عضو کانال شوید:",
            reply_markup=markup
        )

    # اگر دکمه «جمع دو عدد» رو زده باشه ولی هنوز پست ندیده باشه
    if text == "جمع دو عدد":
        last_posts = load_last_posts_list()
        seen = get_seen_for_user(user_id)
        if any(p not in seen for p in last_posts):
            return await bot.send_message(user_id, "ابتدا همه پست‌ها را مشاهده کنید!")
        return await sum_two_numbers_start(message)

    # در هر حالت دیگر، چک می‌کنیم آیا پست ندیده‌ای داره یا نه
    return await check_and_show_posts(user_id, chat_id)

# ===================================================================
# بخش ۵: کال‌بک‌ها (دکمه‌های اینلاین)
# ===================================================================
@bot.callback_query_handler(func=lambda c: c.data == "check_membership")
async def callback_check_membership(call):
    """دکمه «عضو شدم» - چک مجدد عضویت"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if await is_member(bot, user_id):
        await bot.answer_callback_query(call.id, "عضویت تأیید شد ✅")
        try:
            await bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        await check_and_show_posts(user_id, chat_id)
    else:
        await bot.answer_callback_query(call.id, "هنوز عضو کانال نشده‌اید ❌", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("seen_"))
async def callback_seen(call):
    """دکمه «مشاهده شد» - ۳ ثانیه صبر می‌کنه بعد پیام‌ها رو پاک می‌کنه"""
    user_id = call.from_user.id
    post_id = int(call.data.split("_")[1])
    mark_seen(user_id, post_id)
    await bot.answer_callback_query(call.id, "✅ ثبت شد")
    await delete_post_messages_delayed(user_id, post_id)  # پاک کردن با تاخیر
    await call.message.delete()  # حذف پیام سوال
    await check_remaining_and_maybe_main(user_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delete_"))
async def callback_delete(call):
    """دکمه «دیدم، پاکش کن» - فوراً پیام‌ها رو پاک می‌کنه"""
    user_id = call.from_user.id
    post_id = int(call.data.split("_")[1])
    mark_seen(user_id, post_id)
    await bot.answer_callback_query(call.id, "🗑 حذف شد")
    await delete_post_messages_immediate(user_id, post_id)  # حذف فوری
    await check_remaining_and_maybe_main(user_id)

# ===================================================================
# بخش ۶: توابع کمکی حذف و چک کردن وضعیت
# ===================================================================
async def delete_post_messages_delayed(user_id, post_id):
    """حذف پیام فوروارد شده و پیام سوال بعد از ۳ ثانیه"""
    if user_id in forwarded_messages and post_id in forwarded_messages[user_id]:
        fwd_id, prompt_id = forwarded_messages[user_id][post_id]
        await asyncio.sleep(3)
        try:
            await bot.delete_message(user_id, fwd_id)
        except:
            pass
        try:
            await bot.delete_message(user_id, prompt_id)
        except:
            pass
        forwarded_messages[user_id].pop(post_id, None)

async def delete_post_messages_immediate(user_id, post_id):
    """حذف فوری پیام فوروارد شده و پیام سوال"""
    if user_id in forwarded_messages and post_id in forwarded_messages[user_id]:
        fwd_id, prompt_id = forwarded_messages[user_id][post_id]
        try:
            await bot.delete_message(user_id, fwd_id)
        except:
            pass
        try:
            await bot.delete_message(user_id, prompt_id)
        except:
            pass
        forwarded_messages[user_id].pop(post_id, None)

async def check_remaining_and_maybe_main(user_id):
    """اگر همه پست‌های آخرین ۳ تا دیده شده باشن، منوی اصلی رو نشون بده"""
    last_posts = load_last_posts_list()
    seen = get_seen_for_user(user_id)
    if all(p in seen for p in last_posts):
        await core_main(user_id)

async def check_and_show_posts(user_id, chat_id):
    """
    وقتی کاربر پیام معمولی می‌فرسته، چک می‌کنیم آیا پست ندیده‌ای داره؟
    اگر داره، همه رو براش فوروارد می‌کنیم
    """
    last_posts = load_last_posts_list()
    seen = get_seen_for_user(user_id)
    remain = [p for p in last_posts if p not in seen]

    if not remain:
        return await core_main(user_id)

    await bot.send_message(chat_id,
                           f"شما باید {len(remain)} پست را مشاهده کنید:",
                           reply_markup=types.ReplyKeyboardRemove())
    for pid in remain:
        try:
            fwd = await bot.forward_message(user_id, CHANNEL_USERNAME, pid)
            prompt = await bot.send_message(
                user_id,
                "پست بالا را مشاهده کرده‌اید؟",
                reply_markup=create_seen_buttons(pid))
            forwarded_messages.setdefault(user_id, {})[pid] = (fwd.message_id, prompt.message_id)
        except:
            pass

# ===================================================================
# بخش ۷: قابلیت نمونه - جمع دو عدد (چند مرحله‌ای)
# ===================================================================
async def sum_two_numbers_start(message):
    """شروع عملیات جمع دو عدد - وضعیت کاربر رو تغییر میده"""
    user_id = message.from_user.id
    user_states[user_id] = {'action': 'sum', 'nums': []}
    await bot.send_message(user_id, "عدد اول؟")

async def sum_two_numbers_receive(message):
    """دریافت اعداد از کاربر و محاسبه جمع"""
    user_id = message.from_user.id
    try:
        num = float(message.text.replace(",", "."))  # پشتیبانی از کاما هم
    except:
        return await bot.send_message(user_id, "لطفاً عدد معتبر وارد کنید ❌")
    
    user_states[user_id]['nums'].append(num)
    
    if len(user_states[user_id]['nums']) == 2:
        total = sum(user_states[user_id]['nums'])
        await bot.send_message(user_id, f"نتیجه: {total}")
        user_states.pop(user_id, None)
        return await core_main(user_id)
    
    await bot.send_message(user_id, "عدد دوم؟")

# ===================================================================
# بخش ۸: اجرای ربات
# ===================================================================
async def periodic_task():
    """تسک دوره‌ای (هر ۸ ساعت) فقط برای دیباگ - می‌تونی بعداً چیز دیگه‌ای بذاری"""
    while True:
        print("[Periodic] last posts =", load_last_posts_list())
        await asyncio.sleep(28800)  # ۸ ساعت

async def main():
    asyncio.create_task(periodic_task())
    print("Bot running…")
    await bot.infinity_polling()

if __name__ == "__main__":
    asyncio.run(main())