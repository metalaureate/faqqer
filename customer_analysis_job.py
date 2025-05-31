#!/usr/bin/env python3
"""
Customer Support Analysis Job
Analyzes recent chat messages for customer service issues and posts summaries.
"""

import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import json
from openai import OpenAI, OpenAIError
import traceback

# Import the archiver functionality
from faq_archiver import archive_channels, client as archiver_client

# Import configuration from blockchain_job (centralized config)
from blockchain_job import ANALYSIS_CHANNELS, ANALYSIS_HOURS, CUSTOMER_SERVICE_GROUP_ID
from telethon.tl.types import PeerChat, PeerChannel

# Analysis settings
ANALYSIS_MODEL = "gpt-4o"
ANALYSIS_TEMPERATURE = 0.3
ANALYSIS_TIMEOUT = 120
MAX_MESSAGE_LENGTH = 4000
MAX_EXAMPLE_LENGTH = 80
MAX_TOKENS_PER_REQUEST = 25000  # Leave room for response tokens (30k limit - 5k buffer)
CHARS_PER_TOKEN_ESTIMATE = 4    # Rough estimate: 1 token ≈ 4 characters

# Customer service analysis prompt
ANALYSIS_PROMPT = """
You are a customer service analyst for a cryptocurrency/blockchain project. Analyze the provided chat messages and categorize customer service issues.

IMPORTANT: 
- Translate any non-English text to English before analysis
- Present all results in English only
- Focus on actual customer problems/issues, not general questions

Look for these specific categories and any new ones you identify:

1. **Bridge reliability** - Issues with blockchain bridges, cross-chain transactions
2. **Network fragmentation** - Network connectivity, node communication issues  
3. **Node setup and sync issues** - Problems setting up or syncing blockchain nodes
4. **Wallet and swap fixes** - Wallet functionality, transaction swaps
5. **Mobile wallet, sync'ing, backup** - Mobile app wallet issues, syncing, backups
6. **Fork or Orphan Chain Issues** - Mentions of forks, orphan chains, users stuck on wrong chain
7. **Setup & Installation Problems** - Installing, updating, running software including:
   - Being stuck at installation steps
   - Missing DLLs or components
   - Software failing to launch or crashing
8. **Mining Rewards Too Low** - Complaints about mining rewards:
   - Discrepancies in estimated vs actual mining output
   - Questions about why mining returns dropped
9. **Universe Wallet & Balance Issues** - Problems with:
   - Incorrect balances
   - Missing funds
   - Balance discrepancies between devices/transactions
10. **Memory Leak Issues** - Reports of:
    - High RAM usage
    - Memory leaks
    - System running out of memory
11. **GPU Not Working** - Mentions of:
    - GPUs not being recognized
    - GPUs not turning on
    - Hash rates lower than expected
12. **Mobile App Issues** - Mobile wallet problems:
    - Syncing issues
    - Wallet balance not updating
    - Transactions failing to appear
    - Problems with wallet backups
13. **Anti-Virus, Firewalls, VPNs** - Issues with security software:
    - Anti-virus warnings/false positives
    - Firewalls blocking connections
    - VPN-related connection problems

For each category found, provide:
- The issue category name
- Total number of unique people mentioning it
- A representative example of the issue (actual message text if possible, translated to English)

IMPORTANT: Respond ONLY with valid JSON format. Do not include any text before or after the JSON. Do not wrap in code blocks or markdown.

Respond in JSON format with this exact structure:
{
  "analysis_summary": "Brief overview of main issues found",
  "total_issues_found": number,
  "categories": [
    {
      "category": "Issue Category Name",
      "count": number_of_people,
      "representative_example": "Example message in English"
    }
  ]
}
"""

def truncate_chat_content(chat_content, max_tokens=MAX_TOKENS_PER_REQUEST):
    """
    Truncate chat content to fit within token limits while preserving recent messages.
    Uses character count as proxy for token count (rough estimate: 1 token ≈ 4 chars)
    """
    max_chars = max_tokens * CHARS_PER_TOKEN_ESTIMATE
    
    if len(chat_content) <= max_chars:
        return chat_content
    
    logging.warning(f"Chat content too large ({len(chat_content)} chars, ~{len(chat_content)//CHARS_PER_TOKEN_ESTIMATE} tokens). Truncating to recent messages...")
    
    # Split into lines (messages)
    lines = chat_content.split('\n')
    
    # Keep the most recent messages that fit within the limit
    truncated_lines = []
    current_length = 0
    
    # Add lines from the end (most recent) until we hit the limit
    for line in reversed(lines):
        line_length = len(line) + 1  # +1 for newline
        if current_length + line_length > max_chars:
            break
        truncated_lines.append(line)
        current_length += line_length
    
    # Reverse back to chronological order
    truncated_lines.reverse()
    
    truncated_content = '\n'.join(truncated_lines)
    
    # Add header explaining truncation
    header = f"[TRUNCATED: Showing most recent {len(truncated_lines)} messages out of {len(lines)} total messages]\n\n"
    final_content = header + truncated_content
    
    logging.info(f"Truncated content: {len(lines)} -> {len(truncated_lines)} messages, {len(chat_content)} -> {len(final_content)} chars")
    
    return final_content

def query_openai_analysis(chat_content):
    """Query OpenAI for customer service analysis"""
    try:
        # Truncate content if it's too large
        truncated_content = truncate_chat_content(chat_content)
        
        client = OpenAI()
        full_prompt = ANALYSIS_PROMPT + "\n\n" + truncated_content
        
        # Estimate total tokens for logging
        estimated_tokens = len(full_prompt) // CHARS_PER_TOKEN_ESTIMATE
        logging.info(f"Sending analysis request: ~{estimated_tokens} tokens ({len(full_prompt)} chars)")
        
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            temperature=ANALYSIS_TEMPERATURE,
            response_format={"type": "json_object"},  # Force JSON response
            messages=[
                {"role": "user", "content": full_prompt}
            ],
            timeout=ANALYSIS_TIMEOUT,
        )
        
        result = response.choices[0].message.content
        logging.info(f"OpenAI analysis response received: {len(result)} characters")
        
        # Log the actual response for debugging
        logging.info(f"Raw OpenAI response: {result[:500]}...")
        
        return result
        
    except OpenAIError as e:
        error_info = {
            "message": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        logging.error(f"OpenAI analysis error: {error_info}")
        return None

async def send_message_to_group(telegram_client, message, target_group_id=None):
    """Send message to specified group or the configured default group"""
    # Use provided target_group_id or fall back to configured default
    group_id = target_group_id if target_group_id is not None else CUSTOMER_SERVICE_GROUP_ID
    
    if not group_id:
        logging.error("No group ID provided or configured")
        return False
        
    try:
        # Determine if the ID is for a channel/supergroup (PeerChannel) or regular group (PeerChat)
        if group_id < 0:  # This indicates a channel or supergroup
            peer = PeerChannel(group_id)
        else:  # This is a regular group
            peer = PeerChat(group_id)

        # Send the message to the group/channel
        await telegram_client.send_message(peer, message)
        logging.info(f"Posted customer service analysis to group ID {group_id}")
        return True
    except Exception as e:
        logging.error(f"Error posting analysis to group ID {group_id}: {e}")
        return False

def format_telegram_table(analysis_data, analysis_hours):
    """Format analysis results for Telegram (using clean text instead of tables)"""
    try:
        # First try to parse as direct JSON
        try:
            data = json.loads(analysis_data)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', analysis_data, re.DOTALL)
            if json_match:
                logging.info("Found JSON in markdown code block, extracting...")
                data = json.loads(json_match.group(1))
            else:
                # Try to find JSON-like content without code blocks
                json_match = re.search(r'(\{.*\})', analysis_data, re.DOTALL)
                if json_match:
                    logging.info("Found JSON-like content, attempting to parse...")
                    data = json.loads(json_match.group(1))
                else:
                    raise json.JSONDecodeError("No JSON content found", analysis_data, 0)
        
        # Check if no significant issues found
        if not data.get('categories') or len(data['categories']) == 0:
            return f"""
🔍 **Customer Service Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}**

📊 **Summary:** {data.get('analysis_summary', 'No significant customer service issues found in the analyzed period.')}

✅ No major customer service issues detected in the last {analysis_hours} hours.
"""
        
        # Build the clean formatted message
        message = f"""
🔍 **Customer Service Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}**

📊 **Summary:** {data.get('analysis_summary', 'Analysis completed')}

📈 **Total Issues Found:** {data.get('total_issues_found', len(data['categories']))}

**Issue Breakdown:**
"""
        
        for i, category in enumerate(data['categories'], 1):
            cat_name = category.get('category', 'Unknown')
            count = category.get('count', 0)
            example = category.get('representative_example', 'No example provided')
            
            # Truncate long examples
            if len(example) > MAX_EXAMPLE_LENGTH:
                example = example[:MAX_EXAMPLE_LENGTH-3] + "..."
            
            message += f"\n{i}. **{cat_name}** ({count} people)\n   └ _\"{example}\"_\n"
        
        message += f"\n📅 **Analysis Period:** Last {analysis_hours} hours"
        message += f"\n🔗 **Channels:** {', '.join(ANALYSIS_CHANNELS)}"
        
        return message
        
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing analysis JSON: {e}")
        logging.error(f"Raw analysis data (first 1000 chars): {analysis_data[:1000]}")
        return f"""
🔍 **Customer Service Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}**

❌ Error processing analysis results. Raw response was received but could not be parsed.

**Debug Info:** JSON decode error at position {e.pos if hasattr(e, 'pos') else 'unknown'}
"""
    except Exception as e:
        logging.error(f"Error formatting analysis results: {e}")
        return f"""
🔍 **Customer Service Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}**

❌ Error formatting analysis results: {str(e)}
"""

async def run_customer_service_analysis(telegram_client, target_group_id=None, hours=None):
    """Run the customer service analysis and post results
    
    Args:
        telegram_client: The Telegram client instance
        target_group_id: Optional specific group ID to post to. If None, uses CUSTOMER_SERVICE_GROUP_ID
        hours: Optional hours to analyze. If None, uses ANALYSIS_HOURS
    """
    analysis_hours = hours if hours is not None else ANALYSIS_HOURS
    
    try:
        # Check if phone number is available for user authentication
        import os
        phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')
        if not phone_number:
            logging.warning("TELEGRAM_PHONE_NUMBER not configured - customer analysis requires user account access")
            no_auth_msg = f"""
🔍 **Customer Service Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}**

⚠️ **Analysis Unavailable**
Customer service analysis requires a Telegram user account to read channel history.
Bot accounts cannot access historical messages from channels.

**To enable this feature:**
• Configure TELEGRAM_PHONE_NUMBER environment variable
• Ensure the user account has access to the analyzed channels

**Current Configuration:**
• Analysis would cover: {', '.join(ANALYSIS_CHANNELS)}
• Time period: Last {analysis_hours} hours
"""
            await send_message_to_group(telegram_client, no_auth_msg, target_group_id)
            return
        
        logging.info(f"Starting customer service analysis for last {analysis_hours} hours...")
        
        # Use the archiver to get recent messages
        logging.info(f"Fetching messages from channels: {ANALYSIS_CHANNELS}")
        stats = await archive_channels(
            channels=ANALYSIS_CHANNELS,
            hours_history=analysis_hours,
            output_dir="temp_analysis",
            output_as_text=True
        )
        
        if stats['total_messages'] == 0:
            logging.info("No messages found for analysis")
            no_messages_msg = f"""
🔍 **Customer Service Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}**

📊 No messages found in the last {analysis_hours} hours to analyze.
"""
            await send_message_to_group(telegram_client, no_messages_msg, target_group_id)
            return
        
        logging.info(f"Analyzing {stats['total_messages']} messages from {len(stats['channels_processed'])} channels")
        
        # Read the archived messages for analysis
        try:
            with open("temp_analysis/combined_channel_history.txt", 'r', encoding='utf-8') as f:
                chat_content = f.read()
        except FileNotFoundError:
            logging.error("Analysis archive file not found")
            return
        
        # Analyze with OpenAI
        analysis_result = query_openai_analysis(chat_content)
        if not analysis_result:
            logging.error("Failed to get analysis from OpenAI")
            error_msg = f"""
🔍 **Customer Service Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}**

❌ Analysis failed due to AI service error. Please try again later.
"""
            await send_message_to_group(telegram_client, error_msg, target_group_id)
            return
        
        # Format and send the results
        formatted_message = format_telegram_table(analysis_result, analysis_hours)
        
        # Split message if it's too long (Telegram limit ~4096 characters)
        if len(formatted_message) > MAX_MESSAGE_LENGTH:
            # Send in parts
            parts = [formatted_message[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(formatted_message), MAX_MESSAGE_LENGTH)]
            for i, part in enumerate(parts):
                if i == 0:
                    await send_message_to_group(telegram_client, part, target_group_id)
                else:
                    continuation_msg = f"**(continued...)**\n{part}"
                    await send_message_to_group(telegram_client, continuation_msg, target_group_id)
                await asyncio.sleep(1)  # Rate limiting
        else:
            await send_message_to_group(telegram_client, formatted_message, target_group_id)
        
        logging.info("Customer service analysis completed and posted")
        
    except Exception as e:
        logging.error(f"Error in customer service analysis: {e}")
        logging.error(traceback.format_exc())
        
        # Send error notification
        try:
            error_msg = f"""
🔍 **Customer Service Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}**

❌ Analysis failed with error: {str(e)}
"""
            await send_message_to_group(telegram_client, error_msg, target_group_id)
        except:
            pass  # Don't fail if we can't send error message

def schedule_customer_analysis_job(telegram_client, loop):
    """Schedule the customer service analysis job to run every 3 hours"""
    scheduler = BackgroundScheduler()
    
    # Run every 3 hours (0 minutes, every 3rd hour)
    scheduler.add_job(
        lambda: loop.create_task(run_customer_service_analysis(telegram_client)),
        CronTrigger.from_crontab("0 */3 * * *")  # Every 3 hours at minute 0
    )
    
    scheduler.start()
    logging.info("Customer service analysis scheduler started (every 3 hours)")

# Manual trigger function for bot commands
async def manual_analysis_trigger(telegram_client, target_group_id=None, hours=None):
    """Manually trigger analysis for bot commands
    
    Args:
        telegram_client: The Telegram client instance  
        target_group_id: Optional specific group ID to post to. If None, uses CUSTOMER_SERVICE_GROUP_ID
        hours: Optional hours to analyze. If None, uses ANALYSIS_HOURS
    """
    await run_customer_service_analysis(telegram_client, target_group_id, hours)

if __name__ == "__main__":
    # Test the analysis
    import sys
    sys.path.append('.')
    
    async def test_analysis():
        print("Testing customer service analysis...")
        
        # You would need to set up the telegram client here for testing
        # For now, just test the archiver part
        stats = await archive_channels(
            channels=ANALYSIS_CHANNELS,
            hours_history=ANALYSIS_HOURS,
            output_dir="temp_analysis",
            output_as_text=True
        )
        
        print(f"Found {stats['total_messages']} messages to analyze")
        
        if stats['total_messages'] > 0:
            with open("temp_analysis/combined_channel_history.txt", 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"Content length: {len(content)} characters")
            print("First 500 characters:")
            print(content[:500])
    
    # Run test
    with archiver_client:
        archiver_client.loop.run_until_complete(test_analysis())
