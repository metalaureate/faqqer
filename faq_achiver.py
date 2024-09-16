import asyncio
from telethon import TelegramClient
import os
import logging
from datetime import datetime
import pytz

from dotenv import load_dotenv
import json
# Load environment variables from the .env file
load_dotenv()
# Replace these with your actual API details
bot_token=os.getenv('TELEGRAM_BOT_TOKEN')
api_id = os.getenv('TELEGRAM_API_ID')  # From Telegram Developer Portal
api_hash = os.getenv('TELEGRAM_API_HASH')  # From Telegram Developer Portal
CHANNEL_USERNAME = os.getenv('TELEGRAM_CHANNEL_USERNAME')  # The channel you want to archive

phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')  # Your own Telegram account phone number

# File to save the messages
output_html_file = 'archive/channel_history.html'
output_text_file = 'archive/channel_history.txt'
media_folder = 'media_files'  # Folder to save media
# Define date range for filtering (Make sure they're timezone-aware)
timezone = pytz.utc  # Adjust the timezone as needed
start_date = timezone.localize(datetime(2024, 9, 15))  # Start date
end_date = timezone.localize(datetime(2025, 1, 1))  # End date
# Ensure media folder exists
if not os.path.exists(media_folder):
    os.makedirs(media_folder)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the Telegram client for user login
client = TelegramClient('session_name', api_id, api_hash)

# To store a mapping of message ID to its content
message_dict = {}



# Flag to choose between HTML or text output
output_as_text = False  # Set to True for plain text output, False for HTML output

async def get_full_channel_history(channel_username):
    # Initialize offset_id for pagination
    offset_id = 0
    limit = 100  # You can adjust this if you need more or fewer messages per batch
    all_messages = []  # Store all messages here
    
    total_fetched = 0  # Total number of messages fetched
    
    logging.info(f"Starting to fetch messages from channel: {channel_username}")
    
    while True:
        # Get messages with an offset
        messages = await client.get_messages(channel_username, limit=limit, offset_id=offset_id)

        # If no more messages are found, stop the loop
        if not messages:
            break
        
        # Filter messages based on the date range
        for message in messages:
            if start_date <= message.date <= end_date:
                all_messages.append(message)
        
        # Log the number of messages fetched
        total_fetched += len(messages)
        logging.info(f"Fetched {len(messages)} messages (Total so far: {total_fetched})")
        
        # Update offset_id to the ID of the last message
        offset_id = messages[-1].id

        # Sleep to respect rate limits (Telegram has limits on how quickly you can fetch data)
        await asyncio.sleep(1)
    
    logging.info(f"Finished fetching messages. Total messages fetched: {total_fetched}")
    
    # Sort messages in chronological order
    all_messages.sort(key=lambda msg: msg.date)

    if output_as_text:
        # Pure text output with reply context
        with open(output_text_file, 'w', encoding='utf-8') as f:
            for message in all_messages:
                sender = await message.get_sender()  # Get message sender
                username = sender.username if sender else "Unknown"
                date = message.date.strftime('%Y-%m-%d %H:%M:%S')  # Format date
                content = message.text or "Media message"

                # Check if message is a reply to another message
                if message.reply_to_msg_id:
                    replied_message = message_dict.get(message.reply_to_msg_id, "Unknown message")
                    reply_info = f"(Replying to: {replied_message})"
                else:
                    reply_info = ""

                # Add message to the dictionary for replies
                message_dict[message.id] = content

                # Write the message to the text file
                f.write(f"User: {username} | Date: {date}\n")
                f.write(f"Message: {content} {reply_info}\n")
                f.write('-' * 50 + '\n')  # Separator
        logging.info(f"Text chat history saved to {os.path.abspath(output_text_file)}")
    
    else:
        # HTML output
        with open(output_html_file, 'w', encoding='utf-8') as f:
            # Write basic HTML structure and CSS
            f.write('<html><head><title>Channel History</title><style>')
            f.write('body { font-family: Arial, sans-serif; background-color: #f4f4f9; }')
            f.write('.message { padding: 10px; margin-bottom: 20px; border-bottom: 1px solid #ddd; }')
            f.write('.reply { font-size: 0.9em; color: #555; margin-left: 20px; }')
            f.write('.user { font-weight: bold; }')
            f.write('.date { font-size: 0.8em; color: #999; }')
            f.write('.media { margin-top: 10px; }')
            f.write('</style></head><body>')
            f.write(f'<h1>Chat History for {channel_username}</h1><hr>')

            for message in all_messages:
                sender = await message.get_sender()  # Get message sender
                username = sender.username if sender else "Unknown"
                date = message.date.strftime('%Y-%m-%d %H:%M:%S')  # Format date

                # Check if message is a reply to another message
                if message.reply_to_msg_id:
                    replied_message = message_dict.get(message.reply_to_msg_id, "Unknown message")
                    reply_info = f'<div class="reply">Replying to: {replied_message}</div>'
                else:
                    reply_info = ""

                # Handle text and media messages
                content = message.text or ""
                media_reference = ""

                # Check if the message contains media
                if message.media:
                    try:
                        media_path = await message.download_media(file=media_folder)
                        if media_path:
                            media_filename = os.path.basename(media_path)
                            if media_filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                                media_reference = f'<div class="media"><img src="{media_folder}/{media_filename}" alt="Image" width="300"></div>'
                            elif media_filename.endswith(('.mp4', '.webm', '.mkv')):
                                media_reference = f'<div class="media"><video width="300" controls><source src="{media_folder}/{media_filename}" type="video/mp4">Your browser does not support the video tag.</video></div>'
                            else:
                                media_reference = f'<div class="media"><a href="{media_folder}/{media_filename}" download>Download {media_filename}</a></div>'
                        else:
                            logging.warning(f"Failed to download media for message {message.id}")
                    except Exception as e:
                        logging.error(f"Error downloading media for message {message.id}: {e}")

                # Add message to the dictionary for replies
                message_dict[message.id] = content if content else "Media message"

                # Write to the HTML file
                f.write('<div class="message">')
                f.write(f'<div class="user">{username}</div>')
                f.write(f'<div class="date">{date}</div>')
                f.write(f'<div class="content">{content}</div>')
                f.write(reply_info)
                f.write(media_reference)
                f.write('</div>')

            f.write('</body></html>')
        logging.info(f"HTML chat history saved to {os.path.abspath(output_html_file)}")

async def main():
    # Start the client and log in as a user
    await client.start(phone=phone_number)

    # Fetch the full chat history of the channel and write it to a file
    await get_full_channel_history(CHANNEL_USERNAME)

# Run the client until complete
with client:
    client.loop.run_until_complete(main())
