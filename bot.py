
import os
import re
import subprocess
import requests
import random
import base64
import string
from urllib.parse import quote
from urllib3 import disable_warnings
from uuid import uuid4
import logging
from telegram.ext import Updater, MessageHandler, Filters, CallbackQueryHandler, CommandHandler
from moviepy.editor import VideoFileClip
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from progressbar import ProgressBar, Bar, Percentage, ETA, FileTransferSpeed

# Set the token for your Telegram bot
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # Use environment variable for sensitive information

# Set up libtorrent for torrent downloading
import libtorrent as lt

class Bot:
    def __init__(self, token, authorized_users):
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.authorized_users = authorized_users
        self.tokens = set()

# Define your authorized users' IDs
AUTHORIZED_USERS = [123456789, 987654321]  # Replace with your actual user IDs
SHORTENER = "https://atglinks.com/"
SHORTENER_API = "498ee7efdd27b59fa6436070a5a3eb28d1a39e80"

# Create an instance of the Bot class with your Telegram bot token and authorized users
bot = Bot(TELEGRAM_BOT_TOKEN, AUTHORIZED_USERS)

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Function to check if the user is authorized
def is_authorized(user_id):
    return user_id in bot.authorized_users

# Function to download a torrent file using libtorrent
def download_torrent(torrent_link, save_path='./'):
    try:
        ses = lt.session()
        info = lt.torrent_info(torrent_link)
        h = ses.add_torrent({'ti': info, 'save_path': save_path})

        widgets = ['Downloading: ', Percentage(), ' ', Bar(marker='#', left='[', right=']'), ' ', ETA(), ' ', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets)

        for _ in pbar(range(100)):
            s = h.status()
            if s.progress >= 1:
                break

            lt.sleep(1000)

        return os.path.join(save_path, h.name(), f"{h.name()}.mkv")

    except Exception as e:
        logging.error(f"Error downloading torrent: {e}")
        return None

# Function to convert a video file using ffmpeg
def convert_video(file_path, resolution):
    try:
        output_file_path = f"{file_path[:-4]}_{resolution}.mp4"
        command = f"ffmpeg -i {file_path} -s hd{resolution} -c:v libx264 -crf 23 -c:a aac -strict -2 {output_file_path}"
        subprocess.call(command, shell=True)
        return output_file_path
    except Exception as e:
        logging.error(f"Error converting video: {e}")
        return None

# Function to upload a file to Telegram chat
def upload_file(file_path, chat_id):
    try:
        with open(file_path, 'rb') as file:
            bot.updater.bot.send_document(chat_id, document=file)
        return file_path

    except Exception as e:
        logging.error(f"Error uploading file: {e}")
        return None

def generate_random_string(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def short_url(longurl):
    disable_warnings()
    random_string = generate_random_string()
    short_url = f'{SHORTENER}{random_string}'
    return requests.get(f'{short_url}api?api={SHORTENER_API}&url={longurl}&format=text').text

# Function to check access based on tokens
def checking_access(user_id, button=None):
    if not bot.tokens:
        return None, button

    if user_id not in bot.tokens:
        if button is None:
            button = ButtonMaker()  # Assuming ButtonMaker is defined elsewhere
        button.ubutton('Refresh Token', short_url(f'https://t.me/{bot_name}?start={uuid4()}'))
        return 'Invalid token, refresh your token and try again.', button

    return None, button

# Handler function for the '/lecomp' command
def lecomp(update, context):
    user_id = update.message.from_user.id
    token = context.args[0] if context.args else None

    if token and token not in bot.tokens:
        bot.tokens.add(token)

    error_message, button = checking_access(user_id)
    if error_message:
        update.message.reply_text(error_message, reply_markup=button)
        return

    if len(context.args) < 2:
        update.message.reply_text("Please provide a torrent link and resolution after /lecomp.")
        return

    torrent_link = context.args[0]
    resolution_keyboard = [
        [InlineKeyboardButton("480p", callback_data='480p')],
        [InlineKeyboardButton("720p", callback_data='720p')],
    ]
    reply_markup = InlineKeyboardMarkup(resolution_keyboard)

    context.user_data['torrent_link'] = torrent_link
    context.user_data['resolution_keyboard'] = resolution_keyboard

    update.message.reply_text('Please choose the desired encoding resolution:', reply_markup=reply_markup)
    
# Handler function for inline keyboard button callbacks
def button(update, context):
    user_id = update.callback_query.from_user.id

    error_message, _ = checking_access(user_id)
    if error_message:
        query = update.callback_query
        query.answer(error_message)
        return

    query = update.callback_query
    query.answer()

    resolution = query.data
    torrent_link = context.user_data.get('torrent_link')

    downloaded_file_path = download_torrent(torrent_link)

    if downloaded_file_path:
        update.message.reply_text(f"Torrent downloaded successfully: {downloaded_file_path}")

        converted_file_path = convert_video(downloaded_file_path, resolution)

        if converted_file_path:
            update.message.reply_text(f"Video converted successfully: {converted_file_path}")

            # Replace 'YOUR_CHAT_ID' with the actual chat ID where you want to upload the file
            uploaded_file_path = upload_file(converted_file_path, 'YOUR_CHAT_ID')

            if uploaded_file_path:
                update.message.reply_text(f"Video uploaded successfully: {uploaded_file_path}")
                os.remove(uploaded_file_path)  # Remove the uploaded file to save space after upload
            else:
                update.message.reply_text('Error uploading video. Please try again.')
        else:
            update.message.reply_text('Error converting video. Please try again.')
    else:
        update.message.reply_text('Error downloading torrent. Please try again.')

# Handler function for handling non-command messages
def handle_text(update, context):
    user_id = update.message.from_user.id

    error_message, _ = checking_access(user_id)
    if error_message:
        update.message.reply_text(error_message)
        return
      
def leech_file(update, context):
    commands = update.message.text.lower().split(' ')
    url = ''  # Placeholder for the URL of the file to be leech

    for command in commands:
        if 'url=' in command:
            url = command.split('=')[1]

    # Leech the desired file from the provided URL
    # Implement your logic here to leech the file to your desired destination

    # Set up the encoding options based on user preferences
    keyboard = [[InlineKeyboardButton('480p', callback_data='480p'),
                 InlineKeyboardButton('720p', callback_data='720p')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Prompt the user to choose the desired encoding option
    context.bot.send_message(chat_id=update.message.chat_id,
                             text='Please choose the resolution for encoding:',
                             reply=                             markup=reply_markup)

def encode_resolution(update, context):
    query = update.callback_query
    resolution = query.data

    # Use the chosen resolution to perform encoding and add metadata
    input_file = ''  # Placeholder for the input file path
    output_file = ''  # Placeholder for the output file path

    # Implement your logic to perform the encoding based on the resolution
    if resolution == '480p':
        # Encoding options for 480p resolution
        encoding_options = "-preset veryfast -c:v libx265 -s 846x480 -x265-params 'bframes=8:psy-rd=1:ref=3:aq-mode=3:aq-strength=0.8:deblock=1,1' -pix_fmt yuv420p -crf 28 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 -threads 1"

        # Add metadata to the video
        metadata_options = '-metadata title="anime zenith"'

        # Set the output file path
        output_file = 'output_480p.mp4'  # Modify the output file name as needed

        # Perform encoding using FFmpeg
        encode_command = f'ffmpeg -i {input_file} {encoding_options} {metadata_options} {output_file}'
        subprocess.run(encode_command, shell=True)

    elif resolution == '720p':
        # Encoding options for 720p resolution
        encoding_options = "-preset veryfast -c:v libx265 -s 1280x720 -x265-params 'bframes=8:psy-rd=1:ref=3:aq-mode=3:aq-strength=0.8:deblock=1,1' -pix_fmt yuv420p -crf 26 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 -threads 1"

        # Add metadata to the video
        metadata_options = '-metadata title="anime zenith"'

        # Set the output file path
        output_file = 'output_720p.mp4'  # Modify the output file name as needed

        # Perform encoding using FFmpeg
        encode_command = f'ffmpeg -i {input_file} {encoding_options} {metadata_options} {output_file}'
        subprocess.run(encode_command, shell=True)

    # Provide a confirmation message to the user
    context.bot.send_message(chat_id=query.message.chat_id, text=f'Encoding completed in {resolution} resolution!')

    # Send the encoded file to the user
    context.bot.send_video(chat_id=query.message.chat_id, video=open(output_file, 'rb'))

def main():
    # Create an updater and dispatcher for the bot
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Add handlers for commands and inline keyboard callbacks
    dispatcher.add_handler(CommandHandler('lecomp', lecomp))
    dispatcher.add_handler(CallbackQueryHandler(encode_resolution))
    dispatcher.add_handler(MessageHandler(Filters.command, leech_file))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

