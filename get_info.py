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

async def get_group_info(identifier):
    try:
        # Check if the identifier is a number (group ID)
        if identifier.lstrip('-').isdigit():
            group_id = int(identifier)
            print(f"Looking up group ID: {group_id}")
            
            # For negative IDs, we need to handle them as channels/supergroups
            if group_id < 0:
                # Convert to proper format for channels/supergroups
                # Negative IDs in Telegram are usually supergroups/channels
                from telethon.tl.types import PeerChannel, PeerChat
                
                # Try as channel first (most common for negative IDs)
                try:
                    entity = await client.get_entity(PeerChannel(abs(group_id)))
                except:
                    # If that fails, try as chat
                    entity = await client.get_entity(PeerChat(abs(group_id)))
            else:
                entity = await client.get_entity(group_id)
        else:
            # It's a username
            entity = await client.get_entity(identifier)
            print(f"Looking up group username: {identifier}")
        
        # Display the entity information
        if isinstance(entity, Chat):
            print(f"✅ Basic Group")
            print(f"   Name: '{entity.title}'")
            print(f"   ID: {entity.id}")
        elif isinstance(entity, Channel):
            print(f"✅ Supergroup/Channel")
            print(f"   Name: '{entity.title}'")
            print(f"   ID: -{entity.id}")  # Show as negative for consistency
            if hasattr(entity, 'username') and entity.username:
                print(f"   Username: @{entity.username}")
        else:
            print(f"❌ Unknown entity type for {identifier}")
        
    except Exception as e:
        print(f"❌ Error looking up {identifier}: {e}")

async def lookup_blockchain_groups():
    """Look up all the groups from blockchain_job.py"""
    try:
        from blockchain_job import group_ids
        print("🔍 Looking up all blockchain job group IDs:")
        print("=" * 50)
        
        for i, group_id in enumerate(group_ids):
            print(f"\n[{i}] Group ID: {group_id}")
            try:
                from telethon.tl.types import PeerChannel, PeerChat
                
                if group_id < 0:
                    # Negative ID - try as channel first
                    try:
                        entity = await client.get_entity(PeerChannel(abs(group_id)))
                    except:
                        entity = await client.get_entity(PeerChat(abs(group_id)))
                else:
                    entity = await client.get_entity(group_id)
                
                if isinstance(entity, Chat):
                    print(f"    ✅ '{entity.title}' (Basic Group)")
                elif isinstance(entity, Channel):
                    print(f"    ✅ '{entity.title}' (Supergroup/Channel)")
                    if hasattr(entity, 'username') and entity.username:
                        print(f"       Username: @{entity.username}")
                        
            except Exception as e:
                print(f"    ❌ Error: {e}")
                
    except ImportError:
        print("❌ Could not import blockchain_job.py")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    # Start the client and log in as a user
    await client.start(phone=phone_number)

    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python get_info.py <group_username_or_id>  - Look up specific group")
        print("  python get_info.py --all                   - Look up all blockchain job groups")
        print()
        print("Examples:")
        print("  python get_info.py @group_name")
        print("  python get_info.py -2165121610")
        print("  python get_info.py --all")
        return
    
    # Check if user wants to look up all blockchain groups
    if sys.argv[1] == "--all":
        await lookup_blockchain_groups()
    else:
        # Look up specific group
        identifier = sys.argv[1]
        await get_group_info(identifier)

# Run the client and get the ID
with client:
    client.loop.run_until_complete(main())
