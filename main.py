import os
from PIL import Image
import telebot

# Your Telegram Bot Token added directly below:
TOKEN = "8200851113:AAEc2_HdU9GIT7bR2hi7zkHZl8cB7uu9MWw"
bot = telebot.TeleBot(TOKEN)

# Dictionary to store uploaded images per user
user_images = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 Welcome to Image to PDF Bot!\n\n"
        "1️⃣ Forward or send me images.\n"
        "2️⃣ Type /convert when you are finished.\n"
        "3️⃣ Type /clear to remove stored images."
    )
    bot.reply_to(message, text)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    
    # Download the highest resolution photo
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    user_dir = f"temp_{user_id}"
    os.makedirs(user_dir, exist_ok=True)

    if user_id not in user_images:
        user_images[user_id] = []

    image_path = os.path.join(user_dir, f"img_{len(user_images[user_id])}.jpg")
    with open(image_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    user_images[user_id].append(image_path)
    bot.reply_to(message, f"📸 Image added! Total: {len(user_images[user_id])}. Send more or type /convert.")

@bot.message_handler(commands=['convert'])
def convert_to_pdf(message):
    user_id = message.from_user.id
    
    if user_id not in user_images or not user_images[user_id]:
        bot.reply_to(message, "⚠️ No images found! Send some images first.")
        return

    msg = bot.reply_to(message, "⏳ Converting images to PDF...")
    
    pdf_path = f"output_{user_id}.pdf"
    image_list = []

    try:
        for img_path in user_images[user_id]:
            img = Image.open(img_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            image_list.append(img)

        # Merge images into a single multi-page PDF
        image_list[0].save(
            pdf_path, 
            "PDF", 
            resolution=100.0, 
            save_all=True, 
            append_images=image_list[1:]
        )

        with open(pdf_path, 'rb') as pdf_file:
            bot.send_document(message.chat.id, pdf_file, caption="📄 Here is your PDF file!")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

    finally:
        bot.delete_message(message.chat.id, msg.message_id)
        cleanup_user_data(user_id, pdf_path)

@bot.message_handler(commands=['clear'])
def clear_images(message):
    user_id = message.from_user.id
    cleanup_user_data(user_id)
    bot.reply_to(message, "🗑️ Cleared all your cached images.")

def cleanup_user_data(user_id, pdf_path=None):
    user_dir = f"temp_{user_id}"
    if os.path.exists(user_dir):
        for file in os.listdir(user_dir):
            os.remove(os.path.join(user_dir, file))
        os.rmdir(user_dir)

    if pdf_path and os.path.exists(pdf_path):
        os.remove(pdf_path)

    if user_id in user_images:
        del user_images[user_id]

print("Bot is successfully running!")
bot.infinity_polling()
