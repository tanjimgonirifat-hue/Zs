import telebot
import pyotp
import requests
import random
import time
import os
import threading
from flask import Flask
from faker import Faker
from concurrent.futures import ThreadPoolExecutor

# --- কনফিগারেশন ---
# আপনার দেওয়া নতুন বট টোকেন
TOKEN = '8783194900:AAH__MsqIgqwKn_-Pzg2NdxQsIJ1OjvAVY8' 
# আপনার গুগল শিট URL
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzUbzyLxxuH__wp3n_ntaEpeYpQ7OeAsayOoXe3XAztEZa28sP735Em65p9gL2DIHIlqA/exec"
ADMIN_ID = 8061525743 

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=15)
app = Flask(__name__)
fake = Faker()
executor = ThreadPoolExecutor(max_workers=10)

user_tasks = {}

@app.route('/')
def home():
    return "🚀 System Active with New Token and URL!"

# ডাটা দ্রুত পাঠানোর জন্য ফাংশন
def send_to_sheet(row):
    try:
        requests.post(WEB_APP_URL, json={"row": row}, headers={"Content-Type": "application/json"}, timeout=15)
    except:
        pass

# মেইন মেনু
def main_menu(user_id):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton('📋 Tasks'))
    markup.add(
        telebot.types.KeyboardButton('💰 Profile'), 
        telebot.types.KeyboardButton('💸 Withdraw'), 
        telebot.types.KeyboardButton('👥 My Referrals')
    )
    markup.add(telebot.types.KeyboardButton('📞 Support'))
    if user_id == ADMIN_ID:
        markup.add(telebot.types.KeyboardButton('⚙️ Admin Panel'))
    return markup

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(message.chat.id, "👋 স্বাগতম! কাজ শুরু করতে মেনু ব্যবহার করুন।", reply_markup=main_menu(message.from_user.id))

# ৪ মিনিটের টাইমার ফাংশন
def start_timeout_timer(chat_id):
    time.sleep(240)
    if chat_id in user_tasks and 'completed' not in user_tasks[chat_id]:
        bot.send_message(chat_id, "⏰ Time's up! Task cancelled.")
        bot.clear_step_handler_by_chat_id(chat_id)
        user_tasks.pop(chat_id, None)

@bot.message_handler(func=lambda message: message.text == "📋 Tasks")
def show_tasks(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📱 Create Inst (2FA)  ($0.0170)", callback_data="task_inst"))
    bot.send_message(message.chat.id, "👇 একটি টাস্ক বেছে নিন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "task_inst")
def start_task(call):
    f_name = f"{fake.first_name()} {fake.last_name()}"
    login = f"{fake.user_name()}{random.randint(10, 99)}"
    pwd = fake.password(length=10)
    
    user_tasks[call.message.chat.id] = {"name": f_name, "login": login, "pass": pwd, "start_time": time.time()}
    
    info = (f"👤 **Name:** `{f_name}`\n"
            f"👤 **Login:** `{login}`\n"
            f"🔑 **Pass:** `{pwd}`\n\n"
            f"⏳ আপনার হাতে ৪ মিনিট সময় আছে। এর মধ্যে **2FA Key** দিন।")
    bot.send_message(call.message.chat.id, info, parse_mode="Markdown")
    
    threading.Thread(target=start_timeout_timer, args=(call.message.chat.id,)).start()
    bot.register_next_step_handler(call.message, get_otp)

def get_otp(message):
    chat_id = message.chat.id
    if message.text in ['📋 Tasks', '💰 Profile', '⚙️ Admin Panel']: return
    
    key = message.text.replace(" ", "")
    try:
        totp = pyotp.TOTP(key)
        otp = totp.now()
        user_tasks[chat_id]['2fa_key'] = key
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ Account registered", callback_data="final_submit"))
        bot.send_message(chat_id, f"🔢 **OTP:** `{otp}`\n\nসব শেষ হলে বাটনে ক্লিক করুন।", reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(chat_id, "❌ ভুল কী! আবার সঠিক কী দিন।")
        bot.register_next_step_handler(message, get_otp)

@bot.callback_query_handler(func=lambda call: call.data == "final_submit")
def submit_data(call):
    chat_id = call.message.chat.id
    data = user_tasks.get(chat_id)
    if data:
        user_tasks[chat_id]['completed'] = True
        row = [time.ctime(), str(chat_id), data['name'], data['login'], data['pass'], data.get('2fa_key', 'N/A'), "Pending"]
        
        executor.submit(send_to_sheet, row)
        bot.edit_message_text("✅ আপনার রিপোর্ট জমা হয়েছে। অ্যাডমিন চেক করলে ব্যালেন্স পাবেন।", chat_id, call.message.message_id)
        user_tasks.pop(chat_id, None)

@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Panel" and message.from_user.id == ADMIN_ID)
def admin_panel(message):
    bot.send_message(message.chat.id, "🛠 **Admin Panel Active**\n\nগুগল শিটে 'Approved' লিখলে ইউজার নোটিফিকেশন পাবে।")

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    bot.infinity_polling()
        
