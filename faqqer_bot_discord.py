import os
import logging
import discord
from discord import app_commands
from discord.ext import commands
import openai
from dotenv import load_dotenv
import json
import requests

# Load environment variables from the .env file
load_dotenv()

# Discord bot token and OpenAI API key
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))  # Replace with your server's ID or set in .env
openai.api_key = OPENAI_API_KEY

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Load the FAQ content
faq_file_path = 'faq_prompt.txt'
avoidance_faq_file_path = 'avoidance_faq_prompt.txt'

with open(faq_file_path, 'r', encoding='utf-8') as faq_file:
    faq_text = faq_file.read()

with open(avoidance_faq_file_path, 'r', encoding='utf-8') as avoidance_file:
    faq_avoidance_text = avoidance_file.read()

# Initialize the bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Function to query OpenAI GPT and handle errors
async def query_openai_gpt(system, faq_avoidance_text, prompt):
    system_prompt = (
        f"{system}\n\n"
        f"Do not talk about the following topics:\n"
        f"{faq_avoidance_text}\n\n"
        f"If you do not know the answer with certainty, tell the user that their question will be forwarded to support staff."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            temperature=0.4,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
        )
        result = response.choices[0].message.content
        logging.info(f"OpenAI response: {result}")
        return result
    except openai.error.OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        return "Sorry, I encountered an error while trying to answer your question. Please try again."

# Function to find FAQ answers
async def find_faq_answer(question):
    prompt = f"""
Search the FAQ for the answer.
Avoid mentioning banned topics.

Question: {question}
Answer in JSON format: {{'answer': '<answer>'}}
"""
    answer = await query_openai_gpt(faq_text, faq_avoidance_text, prompt)
    if answer:
        try:
            logging.info(f"Raw OpenAI response: {answer}")
            sanitized_answer = answer.replace("'", '"')  # Ensure valid JSON
            answer_json = json.loads(sanitized_answer)
            return answer_json.get('answer', "There was an error processing your request.")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON response: {e}")
            return "There was an error processing your request."
    else:
        return "No answer was found."

# Slash command: /faq
@bot.tree.command(name="faq", description="Ask a FAQ question.")
async def faq(interaction: discord.Interaction, question: str):
    logging.info(f"Received question: {question}")
    answer = await find_faq_answer(question)
    await interaction.response.send_message(answer)


# Slash command: /ask (alias for /faq)
@bot.tree.command(name="ask", description="Alias for FAQ.")
async def ask(interaction: discord.Interaction, question: str):
    await faq(interaction, question=question)

# Slash command: /faqqer (another alias)
@bot.tree.command(name="faqqer", description="Alias for FAQ.")
async def faqqer(interaction: discord.Interaction, question: str):
    await faq(interaction, question=question)

@bot.event
async def on_ready():
    logging.info(f"Bot ready! Application ID: {bot.application_id}")
    try:
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)  # Sync commands to the specific guild
        logging.info(f"Commands synced for guild ID {GUILD_ID}.")
        
        # Log all commands that were registered
        for command in bot.tree.get_commands():
            logging.info(f"Registered command: {command.name}")
    except Exception as e:
        logging.error(f"Error syncing commands: {e}")


# Run the bot
if __name__ == '__main__':
    bot.run(DISCORD_BOT_TOKEN)
