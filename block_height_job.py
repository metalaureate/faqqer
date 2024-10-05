import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from telethon.tl.types import PeerChat, PeerChannel
from apscheduler.triggers.cron import CronTrigger
import requests

# Initialize logging
logging.basicConfig(level=logging.INFO)
group_ids = [-2165121610, -1002281038272]
# Function to get the latest block height and metadata
def get_latest_block_info():
    url = "https://textexplore-nextnet.tari.com/?json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return int(data['tipInfo']['metadata']['best_block_height'])  # Latest block height
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")

async def post_block_height(client):
    try:
        # Fetch the block height stats
        block_height = get_latest_block_info()
        block_height_stats = f"Current Tari Universe block height: ~{block_height:,}. Try /faq <question> to get your question answered first."

        # Loop over the group IDs and send the message
        for group_id in group_ids:
            try:
                # Determine if the ID is for a channel/supergroup (PeerChannel) or regular group (PeerChat)
                if group_id < 0:  # This indicates a channel or supergroup
                    peer = PeerChannel(group_id)
                else:  # This is a regular group
                    peer = PeerChat(group_id)

                # Send the message to the group/channel
                await client.send_message(peer, block_height_stats)
                logging.info(f"Posted block height stats to group ID {group_id}: {block_height_stats}")
            except Exception as e:
                logging.error(f"Error posting block height stats to group ID {group_id}: {e}")
    except Exception as e:
        logging.error(f"Error fetching block height stats: {e}")
def schedule_block_height_job(client, loop):
    # Initialize the scheduler
    scheduler = BackgroundScheduler()

    # Add the job to post block height every minute
    scheduler.add_job(lambda: loop.create_task(post_block_height(client)),
                      CronTrigger.from_crontab('*/30 * * * *'))

    # Start the scheduler
    scheduler.start()

    logging.info("Scheduler started for block height job")

