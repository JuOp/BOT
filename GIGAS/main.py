# main.py - Main entry point for the bot
import os
import logging
import sys

# Import the full bot functionality
from bot import main as run_bot
if __name__ == '__main__':
    # Check for Telegram token
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TOKEN:
        print("ERROR: Telegram token not found. Add TELEGRAM_TOKEN to Replit environment variables.")
        sys.exit(1)

    print("Starting NoFap Support Bot...")
    # Run the main function from bot.py
    run_bot()