import telebot
import pyotp
import requests
import random
import time
import os
import threading
from flask import Flask
from faker import Faker

# --- কনফিগারেশন ---
TOKEN = '8619212784:AAGNRWitsKF5EScwGnTvhUMAzatrGjj2Glo' 
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxz544RAW9A3s2vkDT5Q7M-h7-NBr37892CFEmv6U3nRqhabuy0BTE7uJK4XGZ2A9VD/exec"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
fake = Faker()

user_tasks = {}

@app.route('/')
def home():
    return "✅ Tanjim's Pro Bot is Online!"

# --- কিবোর্ড মেনু ---
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton('📋 Tasks'))
    markup.add(
        telebot.types.KeyboardButton('💰 Profile'),
        telebot.types.KeyboardButton('💸 Withdraw'),
        telebot.types.KeyboardButton('👥 My Referrals')
    )
    markup.add(telebot.types.KeyboardButton('📞 Support'))
    return markup

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(message.chat.id, "👋 স্বাগতম! কাজ শুরু করতে নিচের মেনু ব্যবহার করুন।", reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == "📋 Tasks")
def show_tasks(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📱 Create Inst (2FA)  ($0.0170)", callback_data="task_inst"))
    markup.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_task"))
    bot.send_message(message.chat.id, "👇 Please select a task:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "task_inst")
def start_task(call):
    # রেনডম নাম ও পাসওয়ার্ড জেনারেট
    f_name = fake.first_name() + " " + fake.last_name()
    login = fake.user_name() + str(random.randint(10, 99))
    pwd = fake.password(length=10)
    
    user_tasks[call.message.chat.id] = {"name": f_name, "login": login, "pass": pwd}
    
    info = (f"👤 **Name to use:** `{f_name}`\n"
            f"👤 **Login:** `{login}`\n"
            f"🔑 **Password:** `{pwd}`\n\n"
            f"👉 অ্যাকাউন্ট খুলে আপনার **2FA Key** টি এখানে পাঠান।")
    bot.send_message(call.message.chat.id, info, parse_mode="Markdown")
    bot.register_next_step_handler(call.message, get_otp)

def get_otp(message):
    if message.text in ['📋 Tasks', '💰 Profile']: return
    key = message.text.replace(" ", "")
    try:
        totp = pyotp.TOTP(key)
        otp = totp.now()
        user_tasks[message.chat.id]['2fa_key'] = key
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ Account registered", callback_data="final_submit"))
        
        bot.send_message(message.chat.id, f"🔢 **OTP:** `{otp}`\n\nকাজ শেষ হলে নিচের বাটনে ক্লিক করুন।", reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ ভুল কী! আবার সঠিক কী দিন।")
        bot.register_next_step_handler(message, get_otp)

@bot.callback_query_handler(func=lambda call: call.data == "final_submit")
def submit_data(call):
    data = user_tasks.get(call.message.chat.id)
    if data:
        # তথ্যগুলো: Date, User ID, Target Name, Login, Pass, 2FA, Status
        row = [
            str(time.ctime()), 
            str(call.from_user.id), 
            data['name'], # যে নামে আইডি খোলা হয়েছে
            data['login'], 
            data['pass'], 
            data.get('2fa_key', 'N/A'), 
            "Pending"
        ]
        try:
            requests.post(WEB_APP_URL, json={"row": row}, timeout=10)
            bot.edit_message_text("✅ আপনার রিপোর্ট জমা হয়েছে। অ্যাডমিন চেক করলে ব্যালেন্স পাবেন।", call.message.chat.id, call.message.message_id)
            user_tasks.pop(call.message.chat.id, None)
        except:
            bot.send_message(call.message.chat.id, "❌ সাবমিট এরর!")

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    bot.infinity_polling()
    
