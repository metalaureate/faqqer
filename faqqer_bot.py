import os
import re
import traceback
import logging
from datetime import datetime
from telethon import TelegramClient, events
from openai import OpenAI, OpenAIError
import openai
from dotenv import load_dotenv
import json
import requests
from blockchain_job import schedule_block_height_job, schedule_hash_power_job  # Import the block height job
from customer_analysis_job import schedule_customer_analysis_job, manual_analysis_trigger  # Import customer analysis job
import asyncio
from telethon.tl.types import Channel

# FAQQer Bot Version
FAQQER_VERSION = "1.2.0"
BUILD_DATE = "2025-05-31"

# Load environment variables from the .env file
load_dotenv()

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,  # Set the logging level to INFO (you can change it to DEBUG if needed)
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This ensures that logs go to stdout, which Docker captures
    ]
)

# Replace these with your actual API details
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
api_id = os.getenv('TELEGRAM_API_ID')  # From Telegram Developer Portal
api_hash = os.getenv('TELEGRAM_API_HASH')  # From Telegram Developer Portal

# Initialize the Telegram bot client (don't start it yet)
client = TelegramClient('bot', api_id, api_hash)

# Load the FAQ from the uploaded text file
faq_file_path = os.path.join('faqs', 'faq_prompt.txt')

# Function to fetch FAQ content from multiple remote sources
def fetch_remote_faq_content():
    import os
    import glob
    
    # Path to the FAQs folder
    faqs_folder = os.path.join(os.path.dirname(__file__), 'faqs')
    
    combined_content = ""
    successful_fetches = 0
    total_sources = 0
    
    if not os.path.exists(faqs_folder):
        logging.error(f"FAQs folder not found: {faqs_folder}")
        return None
    
    # Process .url files (remote URLs)
    url_files = glob.glob(os.path.join(faqs_folder, '*.url'))
    for url_file in url_files:
        total_sources += 1
        try:
            with open(url_file, 'r', encoding='utf-8') as f:
                url = f.read().strip()
                
            logging.info(f"Fetching from URL file {os.path.basename(url_file)}: {url}")
            response = requests.get(url)
            
            if response.status_code == 200:
                # Check if the content is HTML (indicating web page rather than raw content)
                content_type = response.headers.get('content-type', '').lower()
                is_html = 'text/html' in content_type or response.text.strip().startswith('<!doctype html') or response.text.strip().startswith('<html')
                
                if is_html:
                    logging.warning(f"Skipping {url} - returns HTML web page instead of raw content")
                    continue
                    
                logging.info(f"Successfully fetched FAQ from {url}")
                combined_content += f"\n\n=== Content from {os.path.basename(url_file)} ({url}) ===\n\n"
                combined_content += response.text
                successful_fetches += 1
            else:
                logging.error(f"Failed to fetch FAQ from {url}: Status code {response.status_code}")
        except Exception as e:
            logging.error(f"Error processing URL file {url_file}: {e}")
    
    # Process .txt files (local text content)
    txt_files = glob.glob(os.path.join(faqs_folder, '*.txt'))
    for txt_file in txt_files:
        total_sources += 1
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            logging.info(f"Successfully loaded local FAQ file: {os.path.basename(txt_file)}")
            combined_content += f"\n\n=== Content from {os.path.basename(txt_file)} ===\n\n"
            combined_content += content
            successful_fetches += 1
        except Exception as e:
            logging.error(f"Error reading local FAQ file {txt_file}: {e}")
    
    if successful_fetches > 0:
        logging.info(f"Successfully loaded content from {successful_fetches} out of {total_sources} FAQ sources")
        return combined_content
    else:
        logging.error("Failed to load content from any FAQ sources")
        return None

# Global variables for FAQ content that will be refreshed periodically
faq_text = ""
local_faq_text = ""
faq_avoidance_text = ""

# Function to refresh FAQ content
def refresh_faq_content():
    global faq_text, local_faq_text, faq_avoidance_text
    
    try:
        # Read the local FAQ content
        with open(faq_file_path, 'r', encoding='utf-8') as faq_file:
            local_faq_text = faq_file.read()
        
        # Read the avoidance FAQ content
        avoidance_file_path = 'avoidance_faq_prompt.txt'
        with open(avoidance_file_path, 'r', encoding='utf-8') as faq_file:
            faq_avoidance_text = faq_file.read()
        
        # Fetch and combine with remote content
        remote_faq_text = fetch_remote_faq_content()
        if remote_faq_text:
            faq_text = remote_faq_text + "\n\n" + local_faq_text
            logging.info("FAQ content refreshed: Combined content from remote sources and local file")
        else:
            faq_text = local_faq_text
            logging.warning("FAQ content refreshed: Using only local FAQ content as remote fetch failed")
            
    except Exception as e:
        logging.error(f"Error refreshing FAQ content: {e}")

# Async function to periodically refresh FAQ content
async def periodic_faq_refresh():
    while True:
        try:
            await asyncio.sleep(3600)  # Wait 1 hour (3600 seconds)
            logging.info("Starting periodic FAQ content refresh...")
            refresh_faq_content()
        except Exception as e:
            logging.error(f"Error in periodic FAQ refresh: {e}")

# Initialize FAQ content on startup
refresh_faq_content()


async def list_channels(client):
    dialogs = await client.get_dialogs()  # Retrieve all dialogs the bot is part of

    channels = [dialog for dialog in dialogs if isinstance(dialog.entity, Channel)]
    
    if channels:
        logging.info("Bot is subscribed to the following channels:")
        for channel in channels:
            logging.info(f"Channel Name: {channel.name}, Channel ID: {channel.id}")
    else:
        logging.info("Bot is not subscribed to any channels.")


# Function to query OpenAI GPT-4o and handle any API errors
def query_openai_gpt(system, faq_avoidance_text, prompt):

    system = system + "\n\nDo not talk about the following topics:\n" + faq_avoidance_text + \
             "\n\nIf you do not know the answer with certainty, tell the user that their question will be forwarded to support staff for answering.\n\nIf the questions seems missing, remind the user that the format for interacting with you is '/faq <type your question inline>'. Give an example, e.g., /faq What is Tari Universe?"
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",  # gpt-3.5-turbo
            response_format={"type": "json_object"},
            temperature=0.3,

            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            timeout=60,
        )
        result = response.choices[0].message.content
        logging.info(f"OpenAI response: {result}")
        return result

    except OpenAIError as e:  # Handle OpenAI API errors
        error_info = {
            "message": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        logging.error(f"OpenAI error: {error_info}")
        return """
        {'answer': 'Sorry, I encountered an error while trying to answer your question. Please try again.'}
        """

# Function to search the FAQ for relevant information using GPT-4o
def find_faq_answer(question):
    # Create the prompt to send to GPT-4o

    prompt = """
    Search the FAQ for the answer.
    Avoid mentioning banned topics.
    If you can't find the answer, use your knowledge of cryptocurrency and blockchain to provide a relevant answer.
    If you don't know the answer, say that the question will be forwarded to support staff for answering.
     
    Question:  %s
    Answer in JSON format: {'answer': '<answer>'}
    """ % question

    # Get the response from OpenAI GPT-4o
    answer = query_openai_gpt(faq_text, faq_avoidance_text, prompt)
    if answer:
        # get json object from the answer
        try:
            answer = json.loads(answer)['answer']
            logging.info(f"FAQ answer found: {answer}")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON response: {e}")
            return "There was an error processing your request."

    return answer



# Telegram bot event handler
@client.on(events.NewMessage(pattern=r'/(ask|faq|faqqer)'))
async def handler(event):
    # Extract the user's question from the message
    user_message = event.message.text[len('/ask '):]
    
    # Check if it's a request for hash rates information
    if user_message.lower().strip() == "hash rates" or user_message.lower().strip() == "hashrates" or user_message.lower().strip() == "hash rate":
        logging.info("Hash rates request received. Triggering hash power job.")
        # Directly call the post_hash_power function to get an immediate update
        from blockchain_job import post_hash_power
        await post_hash_power(client)
        return
    
    # Search the FAQ for a relevant answer
    answer = find_faq_answer(user_message)

    # Respond to the user with the answer
    await event.reply(f"{answer}")

# Manual FAQ refresh command handler
@client.on(events.NewMessage(pattern=r'/refresh_faq'))
async def refresh_handler(event):
    try:
        logging.info("Manual FAQ refresh requested")
        await event.reply("🔄 Refreshing FAQ content...")
        refresh_faq_content()
        await event.reply("✅ FAQ content has been refreshed successfully!")
    except Exception as e:
        logging.error(f"Error in manual FAQ refresh: {e}")
        await event.reply("❌ Failed to refresh FAQ content. Please try again later.")

# Manual customer analysis command handler
@client.on(events.NewMessage(pattern=r'/analyze_support(?:\s+(\d+))?'))
async def analyze_support_handler(event):
    try:
        logging.info("Manual customer service analysis requested")
        
        # Extract hours argument (default to 3 if not provided)
        match = event.pattern_match
        hours = int(match.group(1)) if match.group(1) else 3
        
        await event.reply(f"🔍 Starting customer service analysis for the last {hours} hours...")
        
        # Get the chat ID where the command was issued
        chat_id = event.chat_id
        logging.info(f"Posting analysis results to originating chat: {chat_id}")
        
        await manual_analysis_trigger(client, target_group_id=chat_id, hours=hours)
        # The analysis function will post results directly to the originating channel
    except Exception as e:
        logging.error(f"Error in manual customer analysis: {e}")
        await event.reply("❌ Failed to run customer service analysis. Please try again later.")

# Version command handler
@client.on(events.NewMessage(pattern=r'/version'))
async def version_handler(event):
    try:
        logging.info("Version command requested")
        
        # Get current timestamp for runtime info
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        version_info = f"""
🤖 **FAQQer Bot Version Information**

**Version:** {FAQQER_VERSION}
**Build Date:** {BUILD_DATE}
**Runtime:** {current_time}

**Features:**
• FAQ answering with OpenAI GPT-4o
• Hash rate monitoring
• Periodic FAQ content refresh
• Customer service analysis
• Multi-source FAQ loading (local + remote)

**Commands:**
• `/faq <question>` - Ask a question
• `/version` - Show version info
• `/refresh_faq` - Refresh FAQ content
• `/analyze_support [hours]` - Run customer analysis
"""
        
        await event.reply(version_info)
        
    except Exception as e:
        logging.error(f"Error in version command: {e}")
        await event.reply("❌ Failed to retrieve version information.")

# Main execution function
async def main():
    # Start the Telegram client
    await client.start(bot_token=bot_token)
    logging.info(f"FAQQer Bot v{FAQQER_VERSION} (Build: {BUILD_DATE}) - Telegram client started successfully")
    
    # Print version and FAQ content for debugging
    print("\n" + "="*80)
    print(f"FAQQER BOT v{FAQQER_VERSION}")
    print(f"Build Date: {BUILD_DATE}")
    print("="*80)
    print("CURRENT FAQ CONTENT:")
    print("="*80)
    print(f"FAQ Text Length: {len(faq_text)} characters")
    print(f"Local FAQ Length: {len(local_faq_text)} characters")
    print(f"Avoidance FAQ Length: {len(faq_avoidance_text)} characters")
    print("\nFirst 500 characters of FAQ content:")
    print("-" * 50)
    print(faq_text[:500] + "..." if len(faq_text) > 500 else faq_text)
    print("="*80 + "\n")
    
    # Start the periodic FAQ refresh task
    asyncio.create_task(periodic_faq_refresh())
    
    # Schedule jobs
    #schedule_block_height_job(client, asyncio.get_event_loop())
    schedule_hash_power_job(client, asyncio.get_event_loop())
    #schedule_customer_analysis_job(client, asyncio.get_event_loop())  # Customer service analysis every 3 hours
    
    # Start the Telegram bot
    logging.info(f"FAQQer Bot v{FAQQER_VERSION} is running with hourly FAQ refresh and hash power monitoring...")
    await client.run_until_disconnected()

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
