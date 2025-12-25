import asyncio
import logging
import aiosqlite
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web  # ওয়েব সার্ভারের জন্য

# --- কনফিগারেশন ---
# টোকেনটি সরাসরি এখানে না বসিয়ে Render এর Environment Variable এ বসানো নিরাপদ
API_TOKEN = os.getenv("BOT_TOKEN")  

# অ্যাডমিন লিস্ট
ADMIN_IDS = [6872143322, 8363437161, 7931424304, 6698901002] 

# --- লগিং এবং সেটআপ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
DB_NAME = "bot_users.db"

# --- ডাটাবেস সেটআপ ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_user(user: types.User):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO users (id, full_name, username) VALUES (?, ?, ?)", 
                (user.id, user.full_name, user.username)
            )
            await db.commit()
        except Exception as e:
            logging.error(f"DB Error: {e}")

async def get_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            count = await cursor.fetchone()
            return count[0]

async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users") as cursor:
            return await cursor.fetchall()

# --- FSM স্টেটস ---
class AdminState(StatesGroup):
    waiting_for_broadcast_content = State()
    waiting_for_confirm = State()

# --- ১. সাধারণ ইউজারদের জন্য ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await add_user(message.from_user)
    welcome_msg = f"""আসসালামু আলাইকুম, {message.from_user.first_name}! ❤️

আমাদের অফিসিয়াল বটে আপনাকে স্বাগতম।
আমি HELIX বাংলাদেশ নাগরিক সেবা এজেন্ট।
বাংলাদেশের নাগরিকদের জন্য দ্রুত, সহজ ও নিরাপদে বিভিন্ন সেবা পৌঁছে দেওয়াই আমাদের মূল লক্ষ্য।

আপনি যদি বাংলাদেশের নাগরিক হয়ে থাকেন, তাহলে আমাদের সেবা আপনার জন্য অবশ্যই উপকারী।
আমাদের মিনি অ্যাপে এখনই রেজিস্ট্রেশন করে নিন এবং ঘরে বসেই উপভোগ করুন নানা গুরুত্বপূর্ণ সেবা খুব সহজে ও ঝামেলাহীনভাবে।

✅ যেকোনো অভিযোগ, অনুযোগ, পরামর্শ বা রিপোর্ট করার জন্য
✅ আমাদের এজেন্টের সাথে লাইভ কথা বলার জন্য

নিচে দেওয়া ইউজারনেমে ক্লিক করে আমাদের মেসেজ করুন।
প্রথম মেসেজে শুধু Hi অথবা Hello লিখুন।

আমাদের এডমিন স্যার খুব দ্রুত আপনার মেসেজের রিপ্লাই দেবেন, ইনশাআল্লাহ।
টেলিগ্রাম @Helix_Panel 
মিনি এপ @ShellShockRobot

ধন্যবাদ।
HELIX বাংলাদেশ নাগরিক সেবা
আপনার সেবাই আমাদের অঙ্গীকার
"""
    await message.answer(welcome_msg)

# --- ২. অ্যাডমিন প্যানেল ---
async def send_admin_panel(message: types.Message):
    total_users = await get_stats()
    text = (
        f"🛡️ **Admin Control Panel**\n\n"
        f"👥 Total Users: `{total_users}`\n"
        f"👤 Current Admin: `{message.from_user.first_name}`"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Broadcast", callback_data="admin_broadcast")
    kb.button(text="📂 Export IDs", callback_data="admin_export")
    kb.button(text="📊 Refresh", callback_data="admin_refresh")
    kb.adjust(1) 
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await send_admin_panel(message)

# --- ৩. বাটন হ্যান্ডলিং ---
@dp.callback_query(F.data.startswith("admin_"))
async def admin_callbacks(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    action = call.data.split("_")[1]

    if action == "refresh":
        total_users = await get_stats()
        text = f"🛡️ **Admin Panel**\n👥 Users: `{total_users}`"
        try:
            await call.message.edit_text(text, reply_markup=call.message.reply_markup, parse_mode="Markdown")
        except:
            await call.answer("Updated!")

    elif action == "export":
        users = await get_all_users()
        filename = "users.txt"
        with open(filename, "w") as f:
            for user in users:
                f.write(f"{user[0]}\n")
        await call.message.answer_document(FSInputFile(filename))
        os.remove(filename)

    elif action == "broadcast":
        await call.message.answer("📢 ব্রডকাস্ট মেসেজ দিন:")
        await state.set_state(AdminState.waiting_for_broadcast_content)

# --- ৪. ব্রডকাস্ট সিস্টেম ---
@dp.message(AdminState.waiting_for_broadcast_content)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Send", callback_data="confirm_send")
    kb.button(text="❌ Cancel", callback_data="cancel_send")
    await message.copy_to(chat_id=message.from_user.id)
    await message.answer("উপরে প্রিভিউ। পাঠাতে চান?", reply_markup=kb.as_markup())
    await state.set_state(AdminState.waiting_for_confirm)

@dp.callback_query(AdminState.waiting_for_confirm)
async def confirm_send(call: types.CallbackQuery, state: FSMContext):
    if call.data == "cancel_send":
        await call.message.edit_text("❌ বাতিল করা হলো।")
        await state.clear()
        return
    data = await state.get_data()
    users = await get_all_users()
    count = 0
    status_msg = await call.message.edit_text("⏳ পাঠানো হচ্ছে...")
    for user in users:
        try:
            await bot.copy_message(user[0], data['chat_id'], data['msg_id'])
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await status_msg.edit_text(f"✅ সফলভাবে পাঠানো হয়েছে: {count} জনকে।")
    await state.clear()

# --- ৫. ওয়েব সার্ভার (Render এর জন্য) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render PORT এনভায়রনমেন্ট ভেরিয়েবল দেয়, না থাকলে 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- মেইন রানার ---
async def main():
    await init_db()
    # একই সাথে ওয়েব সার্ভার এবং বট চালু রাখা
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
