from telebot import types
from .config import CHANNEL_USERNAME
from .storage import update_seen, get_seen

def create_seen_button(message_id):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("👀 مشاهده شد ✅", callback_data=f"seen_{message_id}")
    markup.add(btn)
    return markup

async def handle_seen(bot, call):
    user_id = call.from_user.id
    post_id = int(call.data.replace("seen_", ""))
    update_seen(user_id, post_id)
    await bot.answer_callback_query(call.id, "✅ ثبت شد")
