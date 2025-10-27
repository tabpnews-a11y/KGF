import os
import telebot
import logging
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import certifi
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# --- CONFIG ---
TOKEN = '8205368169:AAHcff32byoFa2PCtz1p8K29kaNVTvEOjic'
MONGO_URI = 'mongodb+srv://ihatemosquitos9:JvOK4gNs0SH5SVw9@cluster0.1pd5kt5.mongodb.net/?appName=Cluster0'
CHANNEL_ID = -1002979156858  # replace if needed

# --- Setup ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['NOOB']
users_collection = db.users
bot = telebot.TeleBot(TOKEN)

REQUEST_INTERVAL = 1
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_admin = is_user_admin(user_id, CHANNEL_ID)
    if not is_admin:
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    cmd_parts = message.text.split()
    if len(cmd_parts) < 2:
        bot.send_message(chat_id, "*Invalid command format. Use /approve <user_id> <plan> <days> or /disapprove <user_id>.*", parse_mode='Markdown')
        return

    action = cmd_parts[0]
    target_user_id = int(cmd_parts[1])
    plan = int(cmd_parts[2]) if len(cmd_parts) >= 3 else 0
    days = int(cmd_parts[3]) if len(cmd_parts) >= 4 else 0
    if action == '/approve':
        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else datetime.now().date().isoformat()
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": plan, "valid_until": valid_until, "access_count": 0}},
            upsert=True
        )
        msg_text = f"*✅ User {target_user_id} approved for plan {plan} *"
    else:
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": 0, "valid_until": "", "access_count": 0}},
            upsert=True
        )
        msg_text = f"*User {target_user_id} disapproved*"

    bot.send_message(chat_id, msg_text, parse_mode='Markdown')
    try:
        bot.send_message(CHANNEL_ID, msg_text, parse_mode='Markdown')
    except Exception:
        pass

@bot.message_handler(commands=['Attack'])
def attack_command(message):
    try:
        bot.send_message(
            message.chat.id,
            "*Please provide the details for the attack simulation in the following format:\n\n`<IP> <Port> <Duration>`*",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, process_attack_command)
    except Exception as e:
        logging.error(f"Error in attack command: {e}")

def process_attack_command(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "*Invalid Format\n\nUse `<IP> <Port> <Duration>`*", parse_mode='Markdown')
            return

        target_ip, target_port_str, duration_str = args[0], args[1], args[2]

        # basic validation
        try:
            target_port = int(target_port_str)
            duration = int(duration_str)
        except ValueError:
            bot.send_message(message.chat.id, "*Port and Duration must be numbers.*", parse_mode='Markdown')
            return

        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"*Port {target_port} is blocked. Please use a different port.*", parse_mode='Markdown')
            return

        if duration > 420:
            bot.send_message(message.chat.id, f"*Maximum duration allowed is 420 seconds.*", parse_mode='Markdown')
            return

        username = message.from_user.username or message.from_user.first_name

        # SAFE: Do NOT execute any external attack binary.
        start_msg = bot.send_message(
            message.chat.id,
            f"*🟢 Simulation Acknowledged (NO ACTION EXECUTED)*\n\n"
            f"📌 **Target (sim):** {target_ip}:{target_port}\n"
            f"⏰ **Duration (sim):** {duration} seconds\n"
            f"👤 **Requested by:** @{username}\n\n"
            f"_This is a simulation only — no external command was run._",
            parse_mode='Markdown'
        )

        # log simulation in DB
        users_collection.insert_one({
            "user_id": message.from_user.id,
            "username": username,
            "target_ip": target_ip,
            "target_port": target_port,
            "duration": duration,
            "timestamp": datetime.utcnow(),
            "type": "simulation"
        })

        # delete message after a short time for cleanliness
        time.sleep(15)
        try:
            bot.delete_message(message.chat.id, start_msg.message_id)
        except Exception:
            pass

    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")

def is_user_admin(user_id, chat_id):
    try:
        return bot.get_chat_member(chat_id, user_id).status in ['administrator', 'creator']
    except Exception:
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    btn1 = KeyboardButton("Attack 🚀")
    btn2 = KeyboardButton("My Info ℹ️")
    btn3 = KeyboardButton("Buy Access! 💰")
    btn4 = KeyboardButton("Rules 🔰")

    markup.add(btn1, btn2, btn3, btn4)

    bot.send_message(message.chat.id, "*🔆 WELCOME (SIMULATION MODE) 🔆*", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == "Buy Access! 💰":
        bot.reply_to(message, "*SIMULATION PRICES\n\n[Premium]\n> DAY - 200 INR\n> WEEK - 700 INR\n\n[Platinum]\n> MONTH - 1600 INR\n\nDM TO BUY *", parse_mode='Markdown')
    elif message.text == "Attack 🚀":
        attack_command(message)
    elif message.text == "Rules 🔰":
        bot.send_message(message.chat.id, "*RULES (SIMULATION)\n1. This bot runs in simulation-only mode.\n2. No real network actions are performed.*", parse_mode='Markdown')
    elif message.text == "My Info ℹ️":
        user_id = message.from_user.id
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data:
            username = message.from_user.username or message.from_user.first_name
            plan = user_data.get('plan', 'N/A')
            valid_until = user_data.get('valid_until', 'N/A')
            response = (f"*USERNAME: @{username}\n"
                        f"USER ID: {user_id}\n"
                        f"PLAN: {plan} days\n"
                        f"METHOD: simulation*")
        else:
            response = "*No account information found.*"
        bot.reply_to(message, response, parse_mode='Markdown')
    else:
        bot.reply_to(message, "*Invalid option*", parse_mode='Markdown')

if __name__ == "__main__":
    logging.info("Starting Telegram bot (SIMULATION MODE)...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"An error occurred while polling: {e}")
        time.sleep(REQUEST_INTERVAL)