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
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzGCZ__H484PUmhHTnaFGWAEiW6JwTHaS4ZDs0LkU0213Wc5r-7meMsbBEd1Wtye_9E/exec"
BOT_USERNAME = "FacebookGmailInstagramTopMarketBot" # আপনার বটের ইউজারনেম এখানে দিন (বিনা @ এ)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
fake = Faker()

# ডাটাবেস (সাময়িকভাবে মেমোরিতে রাখা হচ্ছে)
user_tasks = {}
user_balances = {} # {user_id: balance}
user_referrals = {} # {user_id: [list of referred users]}

@app.route('/')
def home():
    return "✅ Tanjim's Mega Bot is Online!"

# --- মেইন মেনু কিবোর্ড ---
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

# --- স্টার্ট কমান্ড (রেফারেল লজিক সহ) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    chat_id = message.chat.id
    # নতুন ইউজার হলে ব্যালেন্স ০ করে দেওয়া
    if chat_id not in user_balances:
        user_balances[chat_id] = 0.0
        user_referrals[chat_id] = []

    # রেফারেল চেক
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id.isdigit() and int(referrer_id) != chat_id:
            referrer_id = int(referrer_id)
            if referrer_id in user_referrals and chat_id not in [u for sub in user_referrals.values() for u in sub]:
                user_referrals[referrer_id].append(chat_id)
                # রেফারকারীকে একটি মেসেজ দেওয়া (অপশনাল)
                # bot.send_message(referrer_id, "🔔 নতুন একজন আপনার রেফারে জয়েন করেছে!")

    bot.send_message(chat_id, f"👋 স্বাগতম {message.from_user.first_name}!\nকাজ শুরু করতে নিচের মেনু ব্যবহার করুন।", reply_markup=main_menu())

# --- ৪ মিনিটের টাইমার ফাংশন ---
def start_timeout_timer(chat_id):
    time.sleep(240) # ৪ মিনিট
    if chat_id in user_tasks and 'completed' not in user_tasks[chat_id]:
        bot.send_message(chat_id, "⏰ Time's up! Task cancelled.")
        bot.clear_step_handler_by_chat_id(chat_id)
        user_tasks.pop(chat_id, None)

# --- টাস্ক মেনু ---
@bot.message_handler(func=lambda message: message.text == "📋 Tasks")
def show_tasks(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📱 Create Inst (2FA)  ($0.0170)", callback_data="task_inst"))
    markup.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_task"))
    bot.send_message(message.chat.id, "👇 Please select a task:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "task_inst")
def start_task(call):
    f_name = fake.first_name() + " " + fake.last_name()
    login = fake.user_name() + str(random.randint(10, 99))
    pwd = fake.password(length=10)
    
    user_tasks[call.message.chat.id] = {"name": f_name, "login": login, "pass": pwd}
    
    info = (f"👤 **Name:** `{f_name}`\n"
            f"👤 **Login:** `{login}`\n"
            f"🔑 **Pass:** `{pwd}`\n\n"
            f"⏳ আপনার হাতে ৪ মিনিট সময় আছে। এর মধ্যে **2FA Key** টি এখানে পাঠান।")
    bot.send_message(call.message.chat.id, info, parse_mode="Markdown")
    
    threading.Thread(target=start_timeout_timer, args=(call.message.chat.id,)).start()
    bot.register_next_step_handler(call.message, get_otp)

def get_otp(message):
    if message.text in ['📋 Tasks', '💰 Profile', '💸 Withdraw', '👥 My Referrals']: return
    chat_id = message.chat.id
    key = message.text.replace(" ", "")
    try:
        totp = pyotp.TOTP(key)
        otp = totp.now()
        user_tasks[chat_id]['2fa_key'] = key
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ Account registered", callback_data="final_submit"))
        bot.send_message(chat_id, f"🔢 **OTP:** `{otp}`\n\nকাজ শেষ হলে নিচের বাটনে ক্লিক করুন।", reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(chat_id, "❌ ভুল কী! আবার সঠিক কী দিন।")
        bot.register_next_step_handler(message, get_otp)

# --- সাবমিট লজিক ---
@bot.callback_query_handler(func=lambda call: call.data == "final_submit")
def submit_data(call):
    chat_id = call.message.chat.id
    data = user_tasks.get(chat_id)
    if data:
        user_tasks[chat_id]['completed'] = True
        row = [str(time.ctime()), str(chat_id), data['name'], data['login'], data['pass'], data.get('2fa_key', 'N/A'), "Pending"]
        try:
            requests.post(WEB_APP_URL, json={"row": row}, timeout=10)
            bot.edit_message_text("✅ আপনার রিপোর্ট জমা হয়েছে। অ্যাডমিন চেক করলে ব্যালেন্স পাবেন।", chat_id, call.message.message_id)
            user_tasks.pop(chat_id, None)
        except:
            bot.send_message(chat_id, "❌ সাবমিট এরর! আবার চেষ্টা করুন।")

# --- My Referrals বাটন ---
@bot.message_handler(func=lambda message: message.text == "👥 My Referrals")
def my_referrals(message):
    chat_id = message.chat.id
    ref_link = f"https://t.me/{BOT_USERNAME}?start={chat_id}"
    count = len(user_referrals.get(chat_id, []))
    
    ref_msg = (f"👥 **Referral Program**\n\n"
               f"🔗 **Your Link:** `{ref_link}`\n\n"
               f"🎁 আপনার লিঙ্কে কেউ জয়েন করে কাজ করলে আপনি কমিশন পাবেন।\n"
               f"📊 **Total Referrals:** {count}")
    bot.send_message(chat_id, ref_msg, parse_mode="Markdown")

# --- প্রোফাইল ও সাপোর্ট ---
@bot.message_handler(func=lambda message: message.text in ['💰 Profile', '💸 Withdraw', '📞 Support'])
def handle_menu(message):
    chat_id = message.chat.id
    if message.text == '💰 Profile':
        balance = user_balances.get(chat_id, 0.0)
        bot.send_message(chat_id, f"👤 **ID:** `{chat_id}`\n💰 **Balance:** ${balance:.4f}", parse_mode="Markdown")
    elif message.text == '💸 Withdraw':
        bot.send_message(chat_id, "📉 Min Withdraw: $0.20\nআপনার USDT (BEP-20) অ্যাড্রেসটি এখানে দিন:")
    elif message.text == '📞 Support':
        bot.send_message(chat_id, "📞 Admin: @Tanjim_Admin")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_task")
def cancel_task(call):
    user_tasks.pop(call.message.chat.id, None)
    bot.edit_message_text("❌ Task Cancelled.", call.message.chat.id, call.message.message_id)

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    bot.infinity_polling()
    
