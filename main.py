import os
import asyncio
import threading
import logging
import google.generativeai as genai
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- লগিং সেটআপ (ত্রুটি দেখার জন্য) ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- কনফিগারেশন (Render Environment Variables থেকে নেওয়া হবে) ---
# এগুলো কোডের মধ্যে বসাবেন না, Render এর সেটিংসে বসাবেন
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Google Gemini AI সেটআপ ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # মডেল কনফিগারেশন (যাতে উত্তরগুলো সৃজনশীল হয়)
    generation_config = {
        "temperature": 0.9,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 256,
    }
    model = genai.GenerativeModel('gemini-pro', generation_config=generation_config)
except Exception as e:
    print(f"Gemini AI Error: {e}")

# --- বটের আচরণ (System Prompt) ---
# এখানে বলে দিন আপনি কেমন আচরণ করতে চান
SYSTEM_PROMPT = """
তুমি এখন আমার হয়ে আমার বন্ধুদের সাথে চ্যাট করছ।
তোমার আচরণ হবে:
১. খুব ক্যাজুয়াল এবং বন্ধুসুলভ।
২. উত্তরগুলো খুব বড় করবে না, ছোট এবং প্রাসঙ্গিক রাখবে।
৩. রোবটের মতো কথা বলবে না। ইমোজি ব্যবহার করতে পারো।
৪. বাংলা এবং বাংলিশ (Banglish) মিশিয়ে কথা বলবে।
"""

# --- Flask সার্ভার (Render এ ২৪ ঘণ্টা অন রাখার জন্য) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Userbot is Running smoothly!"

def run_flask():
    # Render এর দেওয়া পোর্টে রান করবে অথবা ডিফল্ট ৮০০০
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- টেলিগ্রাম ক্লায়েন্ট সেটআপ ---
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)
else:
    print("Error: SESSION_STRING is missing!")
    exit()

# --- ইনকামিং মেসেজ হ্যান্ডলার ---
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    sender = await event.get_sender()
    message_text = event.text

    # ১. গ্রুপ মেসেজ বা নিজের পাঠানো মেসেজ ইগনোর করা
    if event.is_group or event.sender_id == (await client.get_me()).id:
        return

    # ২. লগ প্রিন্ট করা (Render Logs এ দেখার জন্য)
    print(f"New Message from {sender.first_name}: {message_text}")

    try:
        # ৩. AI এর কাছে মেসেজ পাঠানো
        chat = model.start_chat(history=[])
        full_instruction = f"{SYSTEM_PROMPT}\n\nUser said: {message_text}\nReply:"
        
        response = chat.send_message(full_instruction)
        ai_reply = response.text

        # ৪. মানুষের মতো ভাব আনতে 'Typing...' দেখানো এবং দেরি করা
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(3) # ৩ সেকেন্ড টাইপিং দেখাবে
            await event.reply(ai_reply)
            print(f"Replied: {ai_reply}")
            
    except Exception as e:
        print(f"Reply Error: {e}")

# --- মেইন ফাংশন ---
if __name__ == '__main__':
    # ১. Flask সার্ভার আলাদা থ্রেডে চালানো
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # ২. টেলিগ্রাম ইউজারবট চালানো
    print("Userbot System Started...")
    client.start()
    client.run_until_disconnected()