
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
from telegram import Update
from telegram.ext import Updater, MessageHandler, CallbackQueryHandler, CommandHandler
from telegram import *
from moviepy.editor import VideoFileClip
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from progressbar import ProgressBar, Bar, Percentage, ETA, FileTransferSpeed

import libtorrent as lt  # has been moved to the top to be with other imports

# Define globally required constants
TELEGRAM_BOT_TOKEN = os.getenv('6498059135:AAEw4Vt4veJtIHOX2NOD-j0UsCD3zH_CyZQ')
AUTHORIZED_USERS = [6748415360]
SHORTENER = "https://atglinks.com/"
SHORTENER_API = "498ee7efdd27b59fa6436070a5a3eb28d1a39e80"

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Instance of Bot with Telegram bot token and authorized users
bot = Bot(TELEGRAM_BOT_TOKEN, AUTHORIZED_USERS)

def is_authorized(user_id):
   return user_id in bot.authorized_users

def download_torrent(torrent_link, save_path='./'):
   ses = lt.session()  # created session
   info = lt.torrent_info(torrent_link)  # retrieved torrent info
   h = ses.add_torrent({'ti': info, 'save_path': save_path})  # added torrent to session

   #Progress bar for downloading
   for _ in ProgressBar()(range(100)):  # make use of the external ProgressBar library
       s = h.status()
       if s.progress >= 1:
           break

       lt.sleep(1000)

   return os.path.join(save_path, h.name(), f"{h.name()}.mkv") if not Exception else None

def convert_video(file_path, resolution):
   output_file_path = f"{file_path[:-4]}_{resolution}.mp4"
   
   try:
       command = f"ffmpeg -i {file_path} -s hd{resolution} -c:v libx264 -crf 23 -c:a aac -strict -2 {output_file_path}"
       subprocess.call(command, shell=True)
   except Exception as e:
       logging.error(f"Error converting video: {e}")
       return None

   return output_file_path

def upload_file(file_path, chat_id):
   try:
       with open(file_path, 'rb') as file:
           bot.updater.bot.send_document(chat_id, document=file)
   except Exception as e:
       logging.error(f"Error uploading file: {e}")
       return None

   return file_path

def generate_random_string(length=8):
   characters = string.ascii_letters + string.digits
   return ''.join(random.choice(characters) for _ in range(length))

def short_url(longurl):
   disable_warnings()
   random_string = generate_random_string()
   short_url = f'{SHORTENER}{random_string}'
   return requests.get(f'{short_url}api?api={SHORTENER_API}&url={longurl}&format=text').text

def checking_access(user_id, button=None):
   if not bot.tokens or user_id not in bot.tokens:
       if button is None:
           button = ButtonMaker()  # Assuming ButtonMaker is defined elsewhere
       button.ubutton('Refresh Token', short_url(f'https://t.me/{bot_name}?start={uuid4()}'))

       return 'Invalid token, refresh your token and try again.', button

   return None, button

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

def handle_text(update, context):
   user_id = update.message.from_user.id

   error_message, _ = checking_access(user_id)
   if error_message:
       update.message.reply_text(error_message)
       return

def main():
   updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
   dispatcher = updater.dispatcher

   # Handlers for commands and inline keyboard callbacks
   dispatcher.add_handler(CommandHandler('lecomp', lecomp))
   dispatcher.add_handler(CallbackQueryHandler(button))
   dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
   
   updater.start_polling()
   updater.idle()

if __name__ == '__main__':
   main()
