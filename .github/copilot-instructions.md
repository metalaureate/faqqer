# FAQQer Bot - AI Coding Instructions

## Project Overview
A Telegram bot with three core functions: AI-powered FAQ responses, blockchain statistics monitoring, and customer service analysis for the Tari cryptocurrency project.

## Architecture & Key Components

### 1. Main Bot (`faqqer_bot.py`)
- **Entry point** - Starts Telegram client, schedules jobs, handles commands
- **FAQ System** - Multi-source FAQ loading: combines local `.txt` files and remote content from `.url` files in `faqs/`
- **OpenAI Integration** - Uses GPT-4o with JSON response format, temperature 0.3
- **Periodic Refresh** - FAQ content auto-refreshes every hour via `periodic_faq_refresh()`
- **Commands**: `/faq`, `/ask`, `/faqqer` (FAQ queries), `/refresh_faq`, `/analyze_support [hours] [question]`, `/version`

### 2. Blockchain Stats (`blockchain_job.py`)
- **Centralized Config** - THIS IS THE SINGLE SOURCE OF TRUTH for group IDs and customer analysis settings
- **Important constants**:
  - `group_ids = [-1002281038272, -1188782007]` - Where to post blockchain stats and analysis
  - `ANALYSIS_CHANNELS`, `ANALYSIS_HOURS`, `CUSTOMER_SERVICE_GROUP_ID` - Customer analysis config
- **Scheduled Jobs** - Posts hash rates every 3 hours via APScheduler with cron triggers
- **Data Source** - Fetches from `https://textexplore.tari.com/?json` for block height and hash rates

### 3. Customer Analysis (`customer_analysis_job.py`)
- **Purpose** - Analyzes Telegram chat messages for customer service issues using OpenAI
- **Key Feature** - Custom focused analysis: `/analyze_support [hours] <specific question>` narrows scope
- **Token Management** - Truncates messages to fit ~25k token limit (keeps most recent messages)
- **Language Handling** - Translates non-English messages to English for analysis
- **Categories** - Pre-defined issue categories (Bridge reliability, Node setup, Wallet issues, etc.)
- **Shared Client** - Requires user client (not bot) - imports `archiver_client` from `faq_archiver.py`

### 4. Archiver (`faq_archiver.py`)
- **Purpose** - Fetches chat history from Telegram channels for analysis
- **Auth Type** - Uses **user authentication** (phone number), not bot token
- **Session Files** - Creates `.session` files for persistent login
- **Default Channels** - `["tariproject", "OrderOfSoon"]`

## Critical Development Patterns

### Configuration Management
**ALL group IDs and channel settings MUST be in `blockchain_job.py`** - other modules import from there:
```python
from blockchain_job import ANALYSIS_CHANNELS, CUSTOMER_SERVICE_GROUP_ID
```

### Telegram Client Patterns
Two distinct client types exist:
1. **Bot Client** (`faqqer_bot.py`) - Uses bot token, limited to bot API
2. **User Client** (`faq_archiver.py`) - Requires phone number, can read full chat history

### FAQ Content Loading
- **Multi-source**: Scans `faqs/` for `.txt` (local) and `.url` (remote URLs) files
- **HTML Detection**: Skips URLs returning HTML instead of raw text
- **Combination**: Remote + local content merged, with source attribution headers

### OpenAI Response Format
Always use JSON mode for structured responses:
```python
response = client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    temperature=0.3,
    timeout=60
)
```

### Job Scheduling Pattern
Jobs use APScheduler with BackgroundScheduler + CronTrigger:
```python
scheduler.add_job(lambda: loop.create_task(post_hash_power(client)),
                  CronTrigger.from_crontab('0 */3 * * *'))
```

## Environment Variables Required
```bash
TELEGRAM_BOT_TOKEN          # Required for bot functionality
TELEGRAM_API_ID             # From https://my.telegram.org/apps
TELEGRAM_API_HASH           # From https://my.telegram.org/apps
TELEGRAM_PHONE_NUMBER       # Optional - only for customer analysis (user client)
OPENAI_API_KEY              # For GPT-4o queries (loaded by OpenAI SDK)
```

## Running & Debugging

### Local Development
```bash
pip install -r requirements.txt
python faqqer_bot.py  # Starts bot with all jobs
```

### Docker Deployment
```bash
docker build -t faqqer-bot .
docker run -d --env-file .env faqqer-bot
```

### Testing Individual Components
```bash
python blockchain_job.py  # Tests hash rate fetching
python faq_archiver.py    # Tests message archiving
```

## Common Gotchas

1. **Version Updates** - Update both `FAQQER_VERSION` and `BUILD_DATE` constants in `faqqer_bot.py`
2. **Group IDs** - Negative IDs indicate channels/supergroups, use `PeerChannel`; positive use `PeerChat`
3. **FAQ Avoidance** - `avoidance_faq_prompt.txt` contains topics bot should refuse (e.g., "money value of XTM")
4. **Session Files** - `.session` files persist user login - delete to re-authenticate
5. **Token Limits** - Customer analysis truncates to ~25k tokens (100k chars) to avoid OpenAI limits
6. **Hash Rates** - Manual trigger with `/faq hash rates` calls `post_hash_power()` immediately

## File Organization
- `faqs/` - FAQ content sources (`.txt` local, `.url` remote)
- `archive/` - Archived chat history output
- `media_files/` - Downloaded media from chats
- `temp_analysis/` - Temporary analysis data
- `*.session*` - Telethon session files (don't commit!)

## Dependencies of Note
- **Telethon** - Telegram client library (not python-telegram-bot!)
- **OpenAI** - GPT-4o for FAQ answers and analysis
- **APScheduler** - Background job scheduling
- **python-dotenv** - Environment variable management
