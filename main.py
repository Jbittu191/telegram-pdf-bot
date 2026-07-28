import os
import threading
from flask import Flask
import telebot

# Initialize Flask server for UptimeRobot pings
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Initialize Telegram Bot
TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your actual bot token
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! Send me photos to convert them into a PDF.")

# Add your existing photo/PDF handling handlers here...

def run_bot():
    bot.infinity_polling(skip_pending_updates=True)

if __name__ == "__main__":
    # Start Flask in a background thread
    threading.Thread(target=run_flask).start()
    # Start Telegram Bot polling
    run_bot()
2
