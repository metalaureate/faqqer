import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from telethon.tl.types import PeerChat, PeerChannel
from apscheduler.triggers.cron import CronTrigger
import requests

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Function to get the latest block height and metadata
def get_latest_block_info():
    url = "https://textexplore-nextnet.tari.com/?json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return int(data['tipInfo']['metadata']['best_block_height'])  # Latest block height
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")

async def post_block_height(client, group_id):
    try:
        # Fetch the block height stats
        block_height = get_latest_block_info()
        block_height_stats = f"Nextnet block height: ~{block_height:,}. Try /faq <question> to get your question answered first."

        # Send the message to the group using the Group ID
        await client.send_message(PeerChannel(group_id), block_height_stats)
        logging.info(f"Posted block height stats to group ID {group_id}: {block_height_stats}")
    except Exception as e:
        logging.error(f"Error posting block height stats: {e}")

def schedule_block_height_job(client, group_id, loop):
    # Initialize the scheduler
    scheduler = BackgroundScheduler()

    # Add the job to post block height every minute
    scheduler.add_job(lambda: loop.create_task(post_block_height(client, group_id)),
                      CronTrigger.from_crontab('*/15 * * * *'))

    # Start the scheduler
    scheduler.start()

    logging.info("Scheduler started for block height job")

