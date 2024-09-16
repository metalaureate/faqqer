import os
import re
import traceback
from telethon import TelegramClient, events
from openai import OpenAI, OpenAIError
import openai
from dotenv import load_dotenv
import json
# Load environment variables from the .env file
load_dotenv()
# Replace these with your actual API details
bot_token=os.getenv('TELEGRAM_BOT_TOKEN')
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

# Function to query OpenAI GPT-4o and handle any API errors
def query_openai_gpt(system,prompt):
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",  # gpt-3.5-turbo
            response_format={"type": "json_object"},
            temperature=0,

            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
                ],
            timeout=60,
        )
        result=response.choices[0].message.content
        print(result)
        return result

    except OpenAIError as e:  # Handle OpenAI API errors
        error_info = {
            "message": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        return f"An error occurred while processing your request: {error_info['message']}"

# Function to search the FAQ for relevant information using GPT-4o
def find_faq_answer(question):
    # Create the prompt to send to GPT-4o

    prompt = """
    Search the FAQ for the answer.
    Question:  %s
    Answer in JSON format: {'answer': '<answer>'}
    """ % question

    # Get the response from OpenAI GPT-4o
    answer = query_openai_gpt(faq_text, prompt)
    if answer:
        # get json object from the answer
        answer = json.loads(answer)['answer']

    return answer

# Telegram bot event handler
@client.on(events.NewMessage(pattern='/ask'))
async def handler(event):
    # Extract the user's question from the message
    user_message = event.message.text[len('/ask '):]
    
    # Search the FAQ for a relevant answer
    answer = find_faq_answer(user_message)

    # Respond to the user with the answer
    await event.reply(f"{answer}")
# Start the Telegram bot
print("Bot is running...")
client.run_until_disconnected()

