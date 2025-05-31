# Faqqer Bot

A Telegram bot with three core functions:

## Core Components

### 1. FAQ Bot (`faqqer_bot.py`)
- **Purpose**: Main bot that listens to channels and responds to questions using OpenAI
- **Function**: Provides intelligent FAQ responses based on trained knowledge
- **Usage**: Responds automatically to questions in configured channels

### 2. Blockchain Stats Job (`blockchain_job.py`)
- **Purpose**: Posts blockchain statistics (block height, hash rates) hourly
- **Output**: Posts to configured group IDs with network statistics
- **Schedule**: Runs every hour automatically

### 3. Customer Service Analysis Job (`customer_analysis_job.py`)
- **Purpose**: Analyzes chat messages for customer service issues
- **Process**: 
  - Fetches last 3 hours of messages from channels
  - Uses OpenAI to categorize customer issues
  - Posts analysis summary to customer service group
- **Schedule**: Runs every 3 hours automatically
- **Manual trigger**: `/analyze_support` command

## Configuration

All configuration is centralized in `blockchain_job.py`:

```python
# Group IDs for posting announcements
group_ids = [-2165121610, -1002281038272, -1188782007]

# Customer Analysis Settings
ANALYSIS_CHANNELS = ["tariproject", "OrderOfSoon"]  # Channels to monitor
ANALYSIS_HOURS = 3  # Hours of history to analyze
CUSTOMER_SERVICE_GROUP_ID = group_ids[0]  # Where to post analysis results
```

## Usage

1. **Setup**: Configure `.env` file with Telegram API credentials
2. **Run**: `python faqqer_bot.py` 
3. **Monitor**: Bot runs all three functions automatically

The bot will:
- Respond to FAQ questions in real-time
- Post blockchain stats every hour
- Analyze customer issues every 3 hours

## Group Output

- **Blockchain stats**: Posted to `group_ids[0]` (Order of Soon)
- **Customer analysis**: Posted to `CUSTOMER_SERVICE_GROUP_ID` (Order of Soon)
- **FAQ responses**: Posted directly in the channels where questions are asked

## Installation

1. Install dependencies: `pip install -r requirements.txt`
2. Configure `.env` with Telegram and OpenAI API keys
3. Run: `python faqqer_bot.py`
