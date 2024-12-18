import os
import re
import traceback
import logging
from telethon import TelegramClient, events
from openai import OpenAI, OpenAIError
import openai
from dotenv import load_dotenv
import json
from block_height_job import schedule_block_height_job  # Import the block height job
import asyncio
from telethon.tl.types import Channel

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
CHANNEL_USERNAME = os.getenv('TELEGRAM_CHANNEL_USERNAME')  # The channel you want to archive

# Initialize the Telegram bot client
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Load the FAQ from the uploaded text file
faq_file_path = 'faq_prompt.txt'

# Read the FAQ content
with open(faq_file_path, 'r', encoding='utf-8') as faq_file:
    faq_text = faq_file.read()

with open("avoidance_" + faq_file_path, 'r', encoding='utf-8') as faq_file:
    faq_avoidance_text = faq_file.read()


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
            model="gpt-4o-2024-08-06",  # gpt-3.5-turbo
            response_format={"type": "json_object"},
            temperature=0.4,

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
    
    # Search the FAQ for a relevant answer
    answer = find_faq_answer(user_message)

    # Respond to the user with the answer
    await event.reply(f"{answer}")

# Get the current event loop
loop = asyncio.get_event_loop()

# Schedule the block height job
# schedule_block_height_job(client , loop)
# Start the Telegram bot
logging.info("Bot is running...")
client.run_until_disconnected()
