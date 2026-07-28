import os
import io
import threading
from flask import Flask
import telebot
from telebot import types
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Initialize Flask server for UptimeRobot
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running fine!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Your Telegram Bot Token
TOKEN = "8200851113:AAEc2_HdU9GIT7bR2hi7zkHZl8cB7uu9MWw"
bot = telebot.TeleBot(TOKEN)

# User session storage
user_data = {}

def get_user_session(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            'images': [],
            'layout': '1',        # '1', '2', or '4'
            'compress': False,    # True or False
            'pdf_name': 'converted_document'
        }
    return user_data[user_id]

# Start Command
@bot.message_handler(commands=['start', 'clear'])
def send_welcome(message):
    user_id = message.chat.id
    user_data[user_id] = {
        'images': [],
        'layout': '1',
        'compress': False,
        'pdf_name': 'converted_document'
    }
    bot.reply_to(message, "👋 Welcome! Send me photos one by one.\nWhen done, tap /settings or click 'Generate PDF Now' button.")

# Photo Handler
@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    user = get_user_session(message.chat.id)
    
    # Download highest resolution photo
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    img = Image.open(io.BytesIO(downloaded_file))
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    user['images'].append(img)
    
    # Control Keyboard
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("⚙️ Settings / Options", callback_data="settings"),
        types.InlineKeyboardButton("📄 Generate PDF Now", callback_data="make_pdf")
    )
    bot.reply_to(message, f"✅ Photo #{len(user['images'])} received!", reply_markup=markup)

# Callback Query Handler (Buttons)
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user = get_user_session(call.message.chat.id)
    
    if call.data == "settings":
        show_settings(call.message)
    elif call.data.startswith("set_layout_"):
        user['layout'] = call.data.split("_")[-1]
        show_settings(call.message)
    elif call.data == "toggle_compress":
        user['compress'] = not user['compress']
        show_settings(call.message)
    elif call.data == "set_name":
        msg = bot.send_message(call.message.chat.id, "✏️ Please type the new filename for your PDF:")
        bot.register_next_step_handler(msg, process_pdf_name)
    elif call.data == "make_pdf":
        generate_and_send_pdf(call.message)

def process_pdf_name(message):
    user = get_user_session(message.chat.id)
    clean_name = "".join([c for c in message.text if c.isalnum() or c in (' ', '_', '-')]).strip()
    user['pdf_name'] = clean_name if clean_name else 'converted_document'
    bot.reply_to(message, f"✅ PDF name set to: `{user['pdf_name']}.pdf`", parse_mode="Markdown")
    show_settings(message)

def show_settings(message):
    user = get_user_session(message.chat.id)
    
    layout_str = f"Layout: {user['layout']} image(s) per page"
    compress_str = "Compression: ON (Smaller size)" if user['compress'] else "Compression: OFF (Original Quality)"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1 Per Page", callback_data="set_layout_1"),
        types.InlineKeyboardButton("2 Per Page", callback_data="set_layout_2"),
        types.InlineKeyboardButton("4 Per Page (2x2)", callback_data="set_layout_4")
    )
    markup.add(types.InlineKeyboardButton(f"⚙️ {compress_str}", callback_data="toggle_compress"))
    markup.add(types.InlineKeyboardButton(f"✏️ Rename ({user['pdf_name']})", callback_data="set_name"))
    markup.add(types.InlineKeyboardButton("🚀 Generate PDF Now", callback_data="make_pdf"))
    
    bot.send_message(message.chat.id, f"<b>PDF Settings:</b>\n• {layout_str}\n• {compress_str}\n• Filename: {user['pdf_name']}.pdf", parse_mode="HTML", reply_markup=markup)

def generate_and_send_pdf(message):
    user_id = message.chat.id
    user = get_user_session(user_id)
    
    if not user['images']:
        bot.send_message(user_id, "⚠️ No photos uploaded yet! Please send images first.")
        return
        
    bot.send_message(user_id, "⚙️ Generating your customized PDF, please wait...")
    
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    page_width, page_height = A4
    
    images = user['images']
    
    # Process images and convert to ImageReader
    processed_readers = []
    for img in images:
        img_io = io.BytesIO()
        if user['compress']:
            img.save(img_io, format='JPEG', quality=50, optimize=True)
        else:
            img.save(img_io, format='JPEG', quality=85)
        img_io.seek(0)
        processed_readers.append((ImageReader(img_io), img.size[0], img.size[1]))

    layout = user['layout']
    
    if layout == '1':
        for img_reader, img_w, img_h in processed_readers:
            ratio = min((page_width - 20) / img_w, (page_height - 20) / img_h)
            draw_w, draw_h = img_w * ratio, img_h * ratio
            x = (page_width - draw_w) / 2
            y = (page_height - draw_h) / 2
            
            c.drawImage(img_reader, x, y, width=draw_w, height=draw_h)
            c.showPage()
            
    elif layout == '2':
        cell_h = page_height / 2
        for idx in range(0, len(processed_readers), 2):
            batch = processed_readers[idx:idx+2]
            for i, (img_reader, img_w, img_h) in enumerate(batch):
                ratio = min((page_width - 20) / img_w, (cell_h - 20) / img_h)
                draw_w, draw_h = img_w * ratio, img_h * ratio
                x = (page_width - draw_w) / 2
                y = page_height - ((i + 1) * cell_h) + ((cell_h - draw_h) / 2)
                
                c.drawImage(img_reader, x, y, width=draw_w, height=draw_h)
            c.showPage()

    elif layout == '4':
        cell_w, cell_h = page_width / 2, page_height / 2
        for idx in range(0, len(processed_readers), 4):
            batch = processed_readers[idx:idx+4]
            coords = [
                (0, cell_h), (cell_w, cell_h),
                (0, 0),      (cell_w, 0)
            ]
            for i, (img_reader, img_w, img_h) in enumerate(batch):
                bx, by = coords[i]
                ratio = min((cell_w - 20) / img_w, (cell_h - 20) / img_h)
                draw_w, draw_h = img_w * ratio, img_h * ratio
                x = bx + (cell_w - draw_w) / 2
                y = by + (cell_h - draw_h) / 2
                
                c.drawImage(img_reader, x, y, width=draw_w, height=draw_h)
            c.showPage()

    c.save()
    pdf_buffer.seek(0)
    
    filename = f"{user['pdf_name']}.pdf"
    bot.send_document(user_id, (filename, pdf_buffer), caption="🎉 Here is your generated PDF!")
    
    # Reset user session
    user_data[user_id] = {
        'images': [],
        'layout': '1',
        'compress': False,
        'pdf_name': 'converted_document'
    }

def run_bot():
    bot.infinity_polling(skip_pending_updates=True)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
