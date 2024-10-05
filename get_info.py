from telethon.errors import ChannelInvalidError
from telethon.tl.types import Channel
from telethon import TelegramClient, events
import logging
import os
import asyncio
from dotenv import load_dotenv
# Load environment variables from the .env file
load_dotenv()
# Replace these with your actual API details
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
api_id = os.getenv('TELEGRAM_API_ID')  # From Telegram Developer Portal
api_hash = os.getenv('TELEGRAM_API_HASH')  # From Telegram Developer Portal
async def get_channel_from_invite(client, invite_link):
    try:
        # Fetch the entity using the invite link
        entity = await client.get_entity(invite_link)

        # Check if the entity is a Channel
        if isinstance(entity, Channel):
            logging.info(f"Channel name: {entity.title}, Channel ID: {entity.id}")
            return entity
        else:
            logging.error(f"The entity is not a channel: {invite_link}")
            return None
    except ChannelInvalidError:
        logging.error(f"Invalid channel or invite link: {invite_link}")
    except Exception as e:
        logging.error(f"Error accessing channel: {e}")
        return None

# Example usage in your bot
async def on_start():
    invite_link = 'https://t.me/+NMJ1QztkOPcyMjMx'  # Replace with your actual invite link
    channel_entity = await get_channel_from_invite(client, invite_link)
    if channel_entity:
        print(f"Channel name is: {channel_entity.title}, Channel ID: {channel_entity.id}")
    else:
        print("Failed to fetch the channel.")

# Initialize the Telegram bot client
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Start the event loop and call on_start
client.loop.run_until_complete(on_start())
client.run_until_disconnected()
