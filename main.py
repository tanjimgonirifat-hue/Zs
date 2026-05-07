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
    return "✅ Tanjim's Pro Task Bot is Online!"

# --- কিবোর্ড মেনু (স্থায়ী বাটন) ---
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton('📋 Tasks'))
    markup.add(
        telebot.types.KeyboardButton('💰 Profile'),
        telebot.types.KeyboardButton('💸 Withdraw'),
        telebot.types.KeyboardButton('👥 My Referrals')
    )
    markup.add(
        telebot.types.KeyboardButton('🌍 Language'),
        telebot.types.KeyboardButton('📞 Support')
    )
    return markup

@bot.message_handler(commands=['start'])
def welcome(message):
    welcome_text = (f"👋 Welcome {message.from_user.first_name}!\n\n"
                    f"Earn money by completing simple tasks. "
                    f"Use the buttons below to navigate.")
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

# --- টাস্ক বাটন (📋 Tasks) ---
@bot.message_handler(func=lambda message: message.text == "📋 Tasks")
def show_tasks(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📱 Create Inst (2FA) ($0.0170)", callback_data="task_info"))
    bot.send_message(message.chat.id, "👇 Please select a task:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "task_info")
def task_details(call):
    text = (f"📋 **Task: 📱 Create Inst (2FA)**\n\n"
            f"📄 **Description:** Create a new account using our info. "
            f"You must setup 2FA to complete this task.\n\n"
            f"⏳ **Review time:** 64 min\n\n"
            f"👇 Click Start to get information.")
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("▶️ Start", callback_data="get_info"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# --- তথ্য প্রদান (▶️ Start) ---
@bot.callback_query_handler(func=lambda call: call.data == "get_info")
def provide_info(call):
    first_name = fake.first_name() + " " + fake.last_name()
    login_user = fake.user_name() + str(random.randint(10, 99))
    password = fake.password(length=11)
    
    user_tasks[call.message.chat.id] = {"name": first_name, "login": login_user, "pass": password}
    
    info_text = (f"👤 **First name:** `{first_name}`\n"
                 f"👤 **Login:** `{login_user}`\n"
                 f"🔑 **Password:** `{password}`\n\n"
                 f"📥 **Step:** Use these to register. After setting 2FA, send the **2FA Key** here.")
    
    bot.send_message(call.message.chat.id, info_text, parse_mode="Markdown")
    bot.register_next_step_handler(call.message, generate_2fa_code)

# --- ২এফএ ওটিপি জেনারেটর ---
def generate_2fa_code(message):
    if message.text in ['📋 Tasks', '💰 Profile', '💸 Withdraw']: return
    
    key = message.text.replace(" ", "")
    try:
        totp = pyotp.TOTP(key)
        code = totp.now()
        user_tasks[message.chat.id]['2fa_key'] = key
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ Account registered", callback_data="final_submit"))
        
        bot.send_message(message.chat.id, f"🔍 **Searching for OTP...**\n\n🔢 **Code:** `{code}`\n\n👆 Tap to copy. Submit when done.", reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ Invalid Key! Please send the correct 2FA key.")
        bot.register_next_step_handler(message, generate_2fa_code)

# --- প্রোফাইল, উইথড্র ও অন্যান্য ---
@bot.message_handler(func=lambda message: message.text in ['💰 Profile', '💸 Withdraw', '👥 My Referrals', '📞 Support'])
def handle_menu(message):
    if message.text == '💰 Profile':
        bot.send_message(message.chat.id, f"👤 **Your profile:**\n\nℹ️ **ID:** `{message.from_user.id}`\n💰 **Balance:** $0.00", parse_mode="Markdown")
    elif message.text == '💸 Withdraw':
        bot.send_message(message.chat.id, "❓ **Choose withdraw method:**\n\nUSDT (BEP-20)\nMin: $0.20", parse_mode="Markdown")
    elif message.text == '📞 Support':
        bot.send_message(message.chat.id, "📞 Support: @Tanjim_Admin")
    else:
        bot.send_message(message.chat.id, "Updating soon...")

# --- ফাইনাল সাবমিশন ---
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
            bot.send_message(call.message.chat.id, "❌ Submission failed! Try again.")

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    bot.infinity_polling()

