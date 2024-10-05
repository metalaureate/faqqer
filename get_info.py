import asyncio
from telethon import TelegramClient
import os
from dotenv import load_dotenv
import logging

# Load environment variables from the .env file
load_dotenv()

# Replace these with your actual API details
api_id = os.getenv('TELEGRAM_API_ID')  # From Telegram Developer Portal
api_hash = os.getenv('TELEGRAM_API_HASH')  # From Telegram Developer Portal
phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')  # Your own Telegram account phone number
group_username = os.getenv('TELEGRAM_CHANNEL_USERNAME')  # The group or channel username or invite link

# Set up logging to print to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the Telegram client for user login
client = TelegramClient('session_name', api_id, api_hash)

async def get_group_id(group_username):
    try:
        # Get the entity for the group or channel
        entity = await client.get_entity(group_username)

        # Print the group or channel ID and name
        print(f"Group/Channel Name: {entity.title}, Group/Channel ID: {entity.id}")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    # Start the client and log in as a user
    await client.start(phone=phone_number)

    # Get the group or channel ID
    await get_group_id(group_username)

# Run the client and get the ID
with client:
    client.loop.run_until_complete(main())
