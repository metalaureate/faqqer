#!/usr/bin/env python3
"""
Retrieve Hash Rate Posts from Telegram Channel
Fetches all hash rate statistics posts from tariproject channel since May 6, 2025
"""

import asyncio
from telethon import TelegramClient
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Telegram API credentials
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize the Telegram client for user login (needed to read channel history)
client = TelegramClient('session_name', api_id, api_hash)

# Configuration
CHANNEL_USERNAME = "tariproject"
START_DATE = datetime(2025, 5, 6, 0, 0, 0)  # May 6, 2025
OUTPUT_FILE = "hash_rate_history.txt"

async def retrieve_hash_rate_posts():
    """
    Retrieve all hash rate posts from the tariproject channel since START_DATE
    """
    
    await client.start(phone=phone_number)
    logging.info(f"Connected to Telegram as {phone_number}")
    
    # Container for hash rate posts
    hash_rate_posts = []
    
    logging.info(f"Fetching messages from {CHANNEL_USERNAME} since {START_DATE.strftime('%Y-%m-%d')}")
    
    offset_id = 0
    limit = 100
    total_messages_checked = 0
    
    try:
        while True:
            # Fetch messages
            messages = await client.get_messages(
                CHANNEL_USERNAME,
                limit=limit,
                offset_id=offset_id
            )
            
            if not messages:
                logging.info("No more messages found. Stopping.")
                break
            
            total_messages_checked += len(messages)
            
            # Check each message
            for msg in messages:
                # Skip if no text content
                if not msg.text:
                    continue
                
                # Convert message date to naive datetime for comparison
                msg_date = msg.date.replace(tzinfo=None)
                
                # Stop if we've gone past our start date
                if msg_date < START_DATE:
                    logging.info(f"Reached messages before {START_DATE.strftime('%Y-%m-%d')}. Stopping.")
                    # Process remaining messages in this batch first
                    break
                
                # Check if this is a hash rate post (contains the signature format)
                if "📊 Current Tari Network Stats 📊" in msg.text and "Block Height:" in msg.text:
                    hash_rate_posts.append({
                        'date': msg_date,
                        'text': msg.text,
                        'message_id': msg.id
                    })
                    logging.info(f"Found hash rate post from {msg_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check if the last message in this batch is before our start date
            last_msg_date = messages[-1].date.replace(tzinfo=None)
            if last_msg_date < START_DATE:
                break
            
            # Prepare for next iteration
            offset_id = messages[-1].id
            
            # Rate limiting
            await asyncio.sleep(1)
            
            if total_messages_checked % 500 == 0:
                logging.info(f"Checked {total_messages_checked} messages, found {len(hash_rate_posts)} hash rate posts so far...")
        
        # Sort posts chronologically (oldest first)
        hash_rate_posts.sort(key=lambda x: x['date'])
        
        logging.info(f"\n{'='*80}")
        logging.info(f"Total messages checked: {total_messages_checked}")
        logging.info(f"Total hash rate posts found: {len(hash_rate_posts)}")
        logging.info(f"Date range: {hash_rate_posts[0]['date'].strftime('%Y-%m-%d')} to {hash_rate_posts[-1]['date'].strftime('%Y-%m-%d')}" if hash_rate_posts else "No posts found")
        logging.info(f"{'='*80}\n")
        
        # Write to output file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(f"Hash Rate History from {CHANNEL_USERNAME}\n")
            f.write(f"Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Date Range: {START_DATE.strftime('%Y-%m-%d')} onwards\n")
            f.write(f"Total Posts: {len(hash_rate_posts)}\n")
            f.write("="*80 + "\n\n")
            
            for post in hash_rate_posts:
                f.write(f"Date: {post['date'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Message ID: {post['message_id']}\n")
                f.write("-" * 80 + "\n")
                f.write(post['text'])
                f.write("\n" + "="*80 + "\n\n")
        
        logging.info(f"✅ Hash rate posts saved to: {OUTPUT_FILE}")
        
        # Also create a CSV-friendly format for easier processing
        csv_output = OUTPUT_FILE.replace('.txt', '.csv')
        with open(csv_output, 'w', encoding='utf-8') as f:
            # Write header
            f.write("Date,Block Height,RandomX Tari,RandomX XMR,SHA3x,Cuckaroo29\n")
            
            for post in hash_rate_posts:
                date_str = post['date'].strftime('%Y-%m-%d %H:%M:%S')
                
                # Extract values using regex
                block_height = re.search(r'Block Height:\s*([\d,]+)', post['text'])
                rx_tari = re.search(r'RandomX \(Tari\):\s*([\d.]+\s*[A-Z]+)', post['text'])
                rx_xmr = re.search(r'RandomX \(Merged-Mined XMR\):\s*([\d.]+\s*[A-Z]+)', post['text'])
                sha3x = re.search(r'SHA3x:\s*([\d.]+\s*[A-Z]+)', post['text'])
                cuckaroo = re.search(r'Cuckaroo 29:\s*([\d.]+\s*[A-Z]+)', post['text'])
                
                # Build CSV row
                row = [
                    date_str,
                    block_height.group(1).replace(',', '') if block_height else '',
                    rx_tari.group(1) if rx_tari else '',
                    rx_xmr.group(1) if rx_xmr else '',
                    sha3x.group(1) if sha3x else '',
                    cuckaroo.group(1) if cuckaroo else ''
                ]
                
                f.write(','.join(row) + '\n')
        
        logging.info(f"✅ CSV format saved to: {csv_output}")
        
        return hash_rate_posts
        
    except Exception as e:
        logging.error(f"Error retrieving messages: {e}")
        import traceback
        traceback.print_exc()
        return []

async def main():
    try:
        posts = await retrieve_hash_rate_posts()
        
        if posts:
            print(f"\n✅ Successfully retrieved {len(posts)} hash rate posts")
            print(f"📄 Output files:")
            print(f"   - {OUTPUT_FILE} (full text)")
            print(f"   - {OUTPUT_FILE.replace('.txt', '.csv')} (CSV format)")
        else:
            print("\n⚠️ No hash rate posts found in the specified date range")
            
    finally:
        await client.disconnect()
        logging.info("Disconnected from Telegram")

if __name__ == "__main__":
    asyncio.run(main())
