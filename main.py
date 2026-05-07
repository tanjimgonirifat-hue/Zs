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
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyPUCH-LmF-WOs6SyTYJ0zXtEtqA__YzSDJpLkMTjZmbHgnWpCYb8FT3iDcO97ar-pQ/exec"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
fake = Faker()

user_tasks = {}

@app.route('/')
def home():
    return "✅ Tanjim's Pro Bot is Live!"

# --- মেইন কিবোর্ড মেনু ---
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
    bot.send_message(
        message.chat.id, 
        f"👋 স্বাগতম {message.from_user.first_name}!\nকাজ শুরু করতে নিচের মেনু ব্যবহার করুন।", 
        reply_markup=main_menu()
    )

# --- টাস্ক সিলেকশন (ছবির মতো ডিজাইন) ---
@bot.message_handler(func=lambda message: message.text == "📋 Tasks")
def show_tasks(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("📱 Create Inst (2FA)  ($0.0170)", callback_data="task_inst")
    btn2 = telebot.types.InlineKeyboardButton("🍪 Cookies  ($0.0170)", callback_data="task_cookies")
    btn3 = telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_task")
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    bot.send_message(message.chat.id, "👇 Please select a task:", reply_markup=markup)

# --- ইনস্ট্রাগ্রাম টাস্ক শুরু ---
@bot.callback_query_handler(func=lambda call: call.data == "task_inst")
def inst_details(call):
    text = ("📋 Task: 📱 Create Inst (2FA)\n\n"
            "📄 Description: Create a new account using real device.\n"
            "⏳ Review time: 64 min\n\n"
            "👇 Click Start to get info.")
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("▶️ Start", callback_data="get_work_data"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- রেনডম ডাটা প্রদান ---
@bot.callback_query_handler(func=lambda call: call.data == "get_work_data")
def give_data(call):
    f_name = fake.first_name() + " " + fake.last_name()
    login = fake.user_name() + str(random.randint(10, 99))
    pwd = fake.password(length=10)
    
    user_tasks[call.message.chat.id] = {"name": f_name, "login": login, "pass": pwd}
    
    info_msg = (f"👤 First name: `{f_name}`\n"
                f"👤 Login: `{login}`\n"
                f"🔑 Password: `{pwd}`\n\n"
                f"👉 এখন অ্যাকাউন্ট খুলে আপনার **2FA Key** টি এখানে পাঠান।")
    bot.send_message(call.message.chat.id, info_msg, parse_mode="Markdown")
    bot.register_next_step_handler(call.message, process_2fa)

# --- 2FA OTP জেনারেশন (twofa.co এর মতো) ---
def process_2fa(message):
    if message.text in ['📋 Tasks', '💰 Profile', '💸 Withdraw']: return
    
    key = message.text.replace(" ", "")
    try:
        totp = pyotp.TOTP(key)
        code = totp.now()
        user_tasks[message.chat.id]['2fa_key'] = key
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ Account registered", callback_data="final_submit"))
        
        otp_text = (f"🔍 Searching for OTP...\n\n"
                    f"🔢 **OTP:** `{code}`\n"
                    f"📋 **Code from 2FA:** 👆 Tap to copy\n\n"
                    f"সব শেষ হলে নিচের বাটনে ক্লিক করুন।")
        bot.send_message(message.chat.id, otp_text, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ ভুল কী! আবার সঠিক কী দিন।")
        bot.register_next_step_handler(message, process_2fa)

# --- ডাটা সাবমিট (গুগল শিট) ---
@bot.callback_query_handler(func=lambda call: call.data == "final_submit")
def final_submit(call):
    data = user_tasks.get(call.message.chat.id)
    if data:
        row = [str(time.ctime()), str(call.from_user.id), data['name'], data['login'], data['pass'], data.get('2fa_key', 'N/A'), "Pending"]
        try:
            requests.post(WEB_APP_URL, json={"row": row}, timeout=10)
            bot.edit_message_text("✅ Your report has been received! Please wait.", call.message.chat.id, call.message.message_id)
            user_tasks.pop(call.message.chat.id, None)
        except:
            bot.send_message(call.message.chat.id, "❌ শিটে জমা দিতে সমস্যা হয়েছে।")

# --- প্রোফাইল ও সাপোর্ট ---
@bot.message_handler(func=lambda message: message.text in ['💰 Profile', '💸 Withdraw', '📞 Support'])
def other_menus(message):
    if message.text == '💰 Profile':
        bot.send_message(message.chat.id, f"👤 Your profile:\n\nℹ️ ID: `{message.from_user.id}`\n💰 Balance: $0.00", parse_mode="Markdown")
    elif message.text == '💸 Withdraw':
        bot.send_message(message.chat.id, "📉 Fee: $0.025\n🔢 Min: $0.20\n\nEnter your USDT (BEP-20) address:")
    elif message.text == '📞 Support':
        bot.send_message(message.chat.id, "📞 Admin: @Tanjim_Admin")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_task")
def cancel_task(call):
    bot.edit_message_text("❌ Task Canceled.", call.message.chat.id, call.message.message_id)

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    bot.infinity_polling()
    
