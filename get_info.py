import asyncio
from telethon import TelegramClient
import os
from dotenv import load_dotenv
import logging
from telethon.tl.types import Chat, Channel
import sys

# Load environment variables from the .env file
load_dotenv()

# Replace these with your actual API details
api_id = os.getenv('TELEGRAM_API_ID')  # From Telegram Developer Portal
api_hash = os.getenv('TELEGRAM_API_HASH')  # From Telegram Developer Portal
phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')  # Your own Telegram account phone number

# Set up logging to print to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the Telegram client for user login
client = TelegramClient('session_name', api_id, api_hash)

async def get_group_id(group_username):
    try:
        # Get the entity for the group or channel
        entity = await client.get_entity(group_username)
        
        # Check if the entity is a Chat (basic group) or a Channel (supergroup/channel)
        if isinstance(entity, Chat):
            print(f"Basic Group Name: {entity.title}, ID: {entity.id}")
        elif isinstance(entity, Channel):
            print(f"Supergroup/Channel Name: {entity.title}, ID: {entity.id}")
        else:
            print(f"Unknown entity type for {group_username}")
        
    except Exception as e:
        print(f"Error: {e}")

async def main():
    # Start the client and log in as a user
    await client.start(phone=phone_number)

    # Check if group username is provided as a command line argument
    if len(sys.argv) < 2:
        print("Usage: python get_info.py <group_username>")
        print("Example: python get_info.py @group_name")
        return
    
    # Get the group username from command line
    group_username = sys.argv[1]
    print(f"Getting info for group: {group_username}")
    
    # Get the group or channel ID
    await get_group_id(group_username)

# Run the client and get the ID
with client:
    client.loop.run_until_complete(main())
