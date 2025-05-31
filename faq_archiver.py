import asyncio
from telethon import TelegramClient
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys

# Load environment variables from the .env file
load_dotenv()

# Replace these with your actual API details
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
api_id = os.getenv('TELEGRAM_API_ID')     # From Telegram Developer Portal
api_hash = os.getenv('TELEGRAM_API_HASH') # From Telegram Developer Portal
CHANNEL_USERNAME = "tariproject"          # tariproject OrderOfSoon Your target channel/group username
phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')  # Your own Telegram phone number
days_history = 3  # Number of days of history to fetch
# Files/folders for output
output_html_file = 'archive/channel_history.html'
output_text_file = 'archive/channel_history.txt'
media_folder = 'media_files'  # Folder to save media


# Ensure media folder exists
if not os.path.exists(media_folder):
    os.makedirs(media_folder)

# Set up logging to print to console
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    stream=sys.stdout
)

# Initialize the Telegram client for user login
client = TelegramClient('session_name', api_id, api_hash)

# To store a mapping of message ID to its content (used for "reply to" info)
message_dict = {}

# Flag to choose between HTML or text output
output_as_text = True  # Set to True for plain text output, False for HTML output

async def get_last_24h_messages(channel_username):
    """
    Fetches all messages from the given channel that are less than 24 hours old.
    Sorts them in chronological order (oldest first) before writing out.
    """
    now_utc_naive = datetime.utcnow()  # naive UTC
    cutoff_time_naive = now_utc_naive - timedelta(days=days_history)

    offset_id = 0
    limit = 100
    all_messages = []

    logging.info(f"Starting to fetch messages from the last 24h in channel: {channel_username}")

    while True:
        # Fetch up to 'limit' messages (newest first)
        messages = await client.get_messages(
            channel_username,
            limit=limit,
            offset_id=offset_id
        )
        
        if not messages:
            logging.info("No more messages found. Stopping.")
            break

        # The oldest message in this batch
        batch_oldest_date = messages[-1].date.replace(tzinfo=None)

        # Keep only messages less than 24h old
        for msg in messages:
            msg_date_naive = msg.date.replace(tzinfo=None)
            if msg_date_naive >= cutoff_time_naive:
                all_messages.append(msg)

        # If the oldest message in the batch is older than 24h, stop
        if batch_oldest_date < cutoff_time_naive:
            break

        # Prepare to fetch older messages next time
        offset_id = messages[-1].id

        # Sleep to respect Telegram rate limits
        await asyncio.sleep(1)

    # Sort final list in chronological order (oldest to newest)
    all_messages.sort(key=lambda m: m.date)

    logging.info(f"Finished fetching. Total messages (last 24h): {len(all_messages)}")

    # Write them to file
    if output_as_text:
        await write_text_history(all_messages, output_text_file)
    else:
        await write_html_history(all_messages, output_html_file)

    # Count unique senders
    unique_senders = set()
    for msg in all_messages:
        sender = await msg.get_sender()
        if sender:
            # If the user has no username, fall back to user ID
            unique_senders.add(sender.username if sender.username else str(sender.id))
        else:
            # Some system/channel messages have no sender
            unique_senders.add("System")

    unique_count = len(unique_senders)
    logging.info(f"Number of unique senders (last 24h): {unique_count}")
    # Print to console if you want it outside logs:
    print(f"\nNumber of unique senders in the last 24h: {unique_count}")

async def write_text_history(messages, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        for msg in messages:
            sender = await msg.get_sender()
            username = sender.username if sender else "Unknown"
            date_str = msg.date.strftime('%Y-%m-%d %H:%M:%S')
            content = msg.text or "Media message"

            # Check if message is a reply to another
            if msg.reply_to_msg_id:
                replied_message = message_dict.get(msg.reply_to_msg_id, "Unknown message")
                reply_info = f"(Replying to: {replied_message})"
            else:
                reply_info = ""

            # Add message content to dictionary for future replies
            message_dict[msg.id] = content

            f.write(f"User: {username} | Date: {date_str}\n")
            f.write(f"Message: {content} {reply_info}\n")
            f.write('-' * 50 + '\n')  # Separator

    logging.info(f"Text chat history saved to {os.path.abspath(filepath)}")

async def write_html_history(messages, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        # Basic HTML skeleton
        f.write('<html><head><title>Channel History</title><style>')
        f.write('body { font-family: Arial, sans-serif; background-color: #f4f4f9; }')
        f.write('.message { padding: 10px; margin-bottom: 20px; border-bottom: 1px solid #ddd; }')
        f.write('.reply { font-size: 0.9em; color: #555; margin-left: 20px; }')
        f.write('.user { font-weight: bold; }')
        f.write('.date { font-size: 0.8em; color: #999; }')
        f.write('.media { margin-top: 10px; }')
        f.write('</style></head><body>')
        f.write(f'<h1>Chat History for {CHANNEL_USERNAME}</h1><hr>')

        for msg in messages:
            sender = await msg.get_sender()
            username = sender.username if sender else "Unknown"
            date_str = msg.date.strftime('%Y-%m-%d %H:%M:%S')
            content = msg.text or ""

            # Reply info
            if msg.reply_to_msg_id:
                replied_message = message_dict.get(msg.reply_to_msg_id, "Unknown message")
                reply_info = f'<div class="reply">Replying to: {replied_message}</div>'
            else:
                reply_info = ""

            media_reference = ""
            if msg.media:
                try:
                    media_path = await msg.download_media(file=media_folder)
                    if media_path:
                        media_filename = os.path.basename(media_path)
                        if media_filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            media_reference = (
                                f'<div class="media">'
                                f'<img src="{media_folder}/{media_filename}" alt="Image" width="300">'
                                '</div>'
                            )
                        elif media_filename.lower().endswith(('.mp4', '.webm', '.mkv')):
                            media_reference = (
                                f'<div class="media">'
                                f'<video width="300" controls>'
                                f'<source src="{media_folder}/{media_filename}" type="video/mp4">'
                                'Your browser does not support the video tag.'
                                '</video></div>'
                            )
                        else:
                            media_reference = (
                                f'<div class="media">'
                                f'<a href="{media_folder}/{media_filename}" download>'
                                f'Download {media_filename}</a></div>'
                            )
                    else:
                        logging.warning(f"Failed to download media for message {msg.id}")
                except Exception as e:
                    logging.error(f"Error downloading media for message {msg.id}: {e}")

            # Store for future replies
            message_dict[msg.id] = content if content else "Media message"

            # HTML output
            f.write('<div class="message">')
            f.write(f'<div class="user">{username}</div>')
            f.write(f'<div class="date">{date_str}</div>')
            f.write(f'<div class="content">{content}</div>')
            f.write(reply_info)
            f.write(media_reference)
            f.write('</div>')

        f.write('</body></html>')

    logging.info(f"HTML chat history saved to {os.path.abspath(filepath)}")


async def main():
    await client.start(phone=phone_number)
    await get_last_24h_messages(CHANNEL_USERNAME)

# Run the client until complete
with client:
    client.loop.run_until_complete(main())
