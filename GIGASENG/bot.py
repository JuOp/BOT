import os
import time
import logging
import sqlite3
import random
import datetime
from threading import Thread
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, CallbackQueryHandler,
    MessageHandler, Filters, ConversationHandler
)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
TOKEN = os.environ['TELEGRAM_TOKEN']

# Constants for ConversationHandler
MAIN_MENU, HELP_MENU, EMERGENCY_HELP = range(3)

# Motivational quotes
QUOTES = [
    "Self-control today is strength tomorrow.",
    "Every day without addiction is a victory over yourself.",
    "Difficult today - easier tomorrow.",
    "Your strength is not in avoiding falling, but in getting back up.",
    "Overcome yourself today and become stronger tomorrow.",
    "True strength is being able to say 'no' to your weaknesses.",
    "You are stronger than you think.",
    "Each new day is a new opportunity to become better.",
    "Your life changes when you change yourself.",
    "Discipline is the bridge between goals and achievements."
]

# Tasks for users
TASKS = [
    "Do 20 push-ups when you feel tempted.",
    "Drink a glass of water and take 10 deep breaths.",
    "Take a 10-minute walk in fresh air.",
    "Take a cold shower.",
    "Read a book for 30 minutes.",
    "Call a friend or family member.",
    "Meditate for 10 minutes.",
    "Write down your thoughts and feelings in a journal.",
    "Do stretching or yoga for 15 minutes.",
    "Draw or write about your goals for the future."
]

# Emergency help
EMERGENCY_TIPS = [
    "Do 20 push-ups right now!",
    "Leave the room immediately and take a walk.",
    "Turn on a cold shower and stand under it for 30 seconds.",
    "Call a friend right now.",
    "Do 50 jumps in place.",
    "Focus on your breathing: inhale for 4 counts, hold for 4, exhale for 4.",
    "Drink a glass of cold water.",
    "Hold a plank position for 1 minute.",
    "Close your eyes and count to 100.",
    "Turn on your favorite energetic music and move to it."
]

# Database initialization
def init_db():
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        start_date TEXT,
        last_check_in TEXT,
        streak INTEGER DEFAULT 0,
        longest_streak INTEGER DEFAULT 0,
        reminder_enabled INTEGER DEFAULT 1,
        reminder_time TEXT DEFAULT "20:00"
    )
    ''')
    
    # Create achievements table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement TEXT,
        achieved_date TEXT,
        PRIMARY KEY (user_id, achievement)
    )
    ''')
    
    # Create chat table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        message TEXT,
        timestamp TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

# Function to register a user
def register_user(user_id, username):
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    # Check if user is already registered
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT INTO users (user_id, username, start_date, last_check_in, streak) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, today, today, 0)
        )
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

# Function to check achievements
def check_achievements(user_id, streak):
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    achievements = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if streak >= 3:
        cursor.execute(
            "INSERT OR IGNORE INTO achievements (user_id, achievement, achieved_date) VALUES (?, ?, ?)",
            (user_id, "3_days", today)
        )
        if cursor.rowcount > 0:
            achievements.append("🥉 3 days without relapse!")
    
    if streak >= 7:
        cursor.execute(
            "INSERT OR IGNORE INTO achievements (user_id, achievement, achieved_date) VALUES (?, ?, ?)",
            (user_id, "7_days", today)
        )
        if cursor.rowcount > 0:
            achievements.append("🥈 7 days without relapse!")
    
    if streak >= 14:
        cursor.execute(
            "INSERT OR IGNORE INTO achievements (user_id, achievement, achieved_date) VALUES (?, ?, ?)",
            (user_id, "14_days", today)
        )
        if cursor.rowcount > 0:
            achievements.append("🥇 14 days without relapse!")
    
    if streak >= 28:
        cursor.execute(
            "INSERT OR IGNORE INTO achievements (user_id, achievement, achieved_date) VALUES (?, ?, ?)",
            (user_id, "28_days", today)
        )
        if cursor.rowcount > 0:
            achievements.append("🏆 28 days without relapse! You're a winner!")
    
    conn.commit()
    conn.close()
    
    return achievements

# Function to send reminders
def send_reminders(context: CallbackContext):
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    current_time = datetime.datetime.now().strftime("%H:%M")
    
    # Get users with enabled reminders and matching reminder time
    cursor.execute(
        "SELECT user_id FROM users WHERE reminder_enabled = 1 AND reminder_time = ?",
        (current_time,)
    )
    
    users = cursor.fetchall()
    conn.close()
    
    for user in users:
        try:
            quote = random.choice(QUOTES)
            message = f"📝 *Daily Reminder*\n\n_{quote}_\n\nDon't forget to check in today! /checkin"
            
            context.bot.send_message(
                chat_id=user[0],
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")

# /start command
def start(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    
    # Register user
    is_new = register_user(user.id, user.username or user.first_name)
    
    if is_new:
        message = (
            f"👋 Hello, {user.first_name}! I'm a bot that will help you overcome addiction and "
            f"become the best version of yourself.\n\n"
            f"🔰 *What I can do:*\n"
            f"✅ Daily check-ins to track progress\n"
            f"📝 Daily tasks for personal growth\n"
            f"🖼 Motivational quotes and images\n"
            f"🆘 Emergency help in moments of weakness\n"
            f"🏆 Achievement system\n\n"
            f"Use /help to get a list of commands."
        )
    else:
        message = (
            f"Welcome back, {user.first_name}! Glad to see you again.\n\n"
            f"Use /help to get a list of commands or use the menu below."
        )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Check In", callback_data="checkin"),
            InlineKeyboardButton("📊 Statistics", callback_data="stats")
        ],
        [
            InlineKeyboardButton("📝 Task of the Day", callback_data="task"),
            InlineKeyboardButton("🖼 Motivation", callback_data="motivation")
        ],
        [
            InlineKeyboardButton("🆘 Emergency Help", callback_data="emergency"),
            InlineKeyboardButton("🏆 Achievements", callback_data="achievements")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return MAIN_MENU

# /help command
def help_command(update: Update, context: CallbackContext) -> int:
    help_text = (
        "*Command List:*\n\n"
        "/start - Start working with the bot\n"
        "/checkin - Check in for today\n"
        "/stats - Show your statistics\n"
        "/task - Get task of the day\n"
        "/motivation - Get a motivational quote\n"
        "/emergency - Emergency help when tempted\n"
        "/achievements - View your achievements\n"
        "/reminder - Configure daily reminders\n"
        "/chat - Join the community chat\n"
        "/help - Show this help"
    )
    
    keyboard = [
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return HELP_MENU

# Button handler
def button_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "back_to_menu":
        return show_main_menu(update, context)
    elif query.data == "checkin":
        return checkin(update, context)
    elif query.data == "stats":
        return show_stats(update, context)
    elif query.data == "task":
        return daily_task(update, context)
    elif query.data == "motivation":
        return motivation(update, context)
    elif query.data == "emergency":
        return emergency(update, context)
    elif query.data == "achievements":
        return show_achievements(update, context)
    elif query.data.startswith("emergency_tip_"):
        return send_emergency_tip(update, context)
    elif query.data == "back_to_emergency":
        return emergency(update, context)
    
    return MAIN_MENU

# Show main menu
def show_main_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Check In", callback_data="checkin"),
            InlineKeyboardButton("📊 Statistics", callback_data="stats")
        ],
        [
            InlineKeyboardButton("📝 Task of the Day", callback_data="task"),
            InlineKeyboardButton("🖼 Motivation", callback_data="motivation")
        ],
        [
            InlineKeyboardButton("🆘 Emergency Help", callback_data="emergency"),
            InlineKeyboardButton("🏆 Achievements", callback_data="achievements")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="Main Menu. Select an action:",
        reply_markup=reply_markup
    )
    
    return MAIN_MENU

# Check in for the day
def checkin(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    # Get current date
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Check if user already checked in today
    cursor.execute(
        "SELECT last_check_in, streak FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if result:
        last_check_in, streak = result
        
        # Check if already checked in today
        if last_check_in == today:
            if isinstance(update.callback_query, type(None)):
                update.message.reply_text("You've already checked in today! Come back tomorrow.")
            else:
                update.callback_query.edit_message_text("You've already checked in today! Come back tomorrow.")
        else:
            # Calculate day difference
            last_date = datetime.datetime.strptime(last_check_in, "%Y-%m-%d")
            current_date = datetime.datetime.strptime(today, "%Y-%m-%d")
            days_diff = (current_date - last_date).days
            
            if days_diff == 1:
                # Consecutive days, increase streak
                new_streak = streak + 1
                message = f"✅ Great! Your streak without relapses: {new_streak} days in a row!"
            elif days_diff > 1:
                # Missed days, reset streak
                new_streak = 1
                message = "✅ Check-in accepted. Unfortunately, your streak was reset due to missed days. New streak: 1 day."
            else:
                # Something wrong with dates
                new_streak = streak
                message = "✅ Check-in accepted."
            
            # Update user data
            cursor.execute(
                "UPDATE users SET last_check_in = ?, streak = ?, longest_streak = MAX(longest_streak, ?) WHERE user_id = ?",
                (today, new_streak, new_streak, user_id)
            )
            conn.commit()
            
            # Check achievements
            achievements = check_achievements(user_id, new_streak)
            
            if achievements:
                message += "\n\n🏆 *New Achievements:*\n" + "\n".join(achievements)
                
                # Check for 28 days
                if new_streak >= 28:
                    message += "\n\n🎁 *Congratulations on reaching 28 days!*\nYour gift: [Go to website](https://yourlink.com)"
            
            if isinstance(update.callback_query, type(None)):
                update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            else:
                update.callback_query.edit_message_text(text=message, parse_mode=ParseMode.MARKDOWN)
    
    conn.close()
    
    # If this was a command, not a callback, return ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Show statistics
def show_stats(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT start_date, streak, longest_streak FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if result:
        start_date, streak, longest_streak = result
        
        # Calculate total days since start
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        today = datetime.datetime.now()
        total_days = (today - start).days + 1
        
        stats_text = (
            f"📊 *Your Statistics:*\n\n"
            f"📅 Start date: {start_date}\n"
            f"📈 Current streak: {streak} days\n"
            f"🏆 Record streak: {longest_streak} days\n"
            f"⏱ Total days since beginning: {total_days}"
        )
        
        keyboard = [
            [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if isinstance(update.callback_query, type(None)):
            update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            update.callback_query.edit_message_text(text=stats_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    conn.close()
    
    # If this was a command, not a callback, return ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Daily task
def daily_task(update: Update, context: CallbackContext) -> int:
    task = random.choice(TASKS)
    
    task_text = f"📝 *Task of the Day:*\n\n{task}\n\nComplete this task and get one step closer to your goal!"
    
    keyboard = [
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update.callback_query, type(None)):
        update.message.reply_text(task_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        update.callback_query.edit_message_text(text=task_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    # If this was a command, not a callback, return ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Motivational quote
def motivation(update: Update, context: CallbackContext) -> int:
    quote = random.choice(QUOTES)
    
    motivation_text = f"🖼 *Motivation of the Day:*\n\n_{quote}_"
    
    keyboard = [
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update.callback_query, type(None)):
        update.message.reply_text(motivation_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        update.callback_query.edit_message_text(text=motivation_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    # If this was a command, not a callback, return ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Emergency help
def emergency(update: Update, context: CallbackContext) -> int:
    emergency_text = (
        "🆘 *Emergency Help*\n\n"
        "Feeling tempted? We're here to help you!\n"
        "Choose a type of help below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💪 Physical Exercise", callback_data="emergency_tip_physical")],
        [InlineKeyboardButton("🧠 Mental Technique", callback_data="emergency_tip_mental")],
        [InlineKeyboardButton("🚿 Cold Shower", callback_data="emergency_tip_shower")],
        [InlineKeyboardButton("🔄 Distraction", callback_data="emergency_tip_distraction")],
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update.callback_query, type(None)):
        update.message.reply_text(emergency_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        update.callback_query.edit_message_text(text=emergency_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    # If this was a command, not a callback, return EMERGENCY_HELP
    if isinstance(update.callback_query, type(None)):
        return EMERGENCY_HELP
    
    return EMERGENCY_HELP

# Send specific emergency tip
def send_emergency_tip(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    tip_type = query.data.replace("emergency_tip_", "")
    
    tips = {
        "physical": [
            "Do 20 push-ups right now!",
            "Do 30 squats.",
            "Hold a plank position for 1 minute."
        ],
        "mental": [
            "Focus on your breathing: inhale for 4 counts, hold for 4, exhale for 4.",
            "Close your eyes and count to 100.",
            "Meditate for 5 minutes, focusing on breathing."
        ],
        "shower": [
            "Take a cold shower for 30-60 seconds.",
            "Wash your face with cold water several times.",
            "Hold your hands under cold water for a minute."
        ],
        "distraction": [
            "Call a friend or family member.",
            "Go for a short walk.",
            "Turn on your favorite energetic music and move to it."
        ]
    }
    
    if tip_type in tips:
        tip = random.choice(tips[tip_type])
        emergency_text = f"🆘 *Emergency Help:*\n\n{tip}\n\nYou can do this! Stay strong!"
    else:
        tip = random.choice(EMERGENCY_TIPS)
        emergency_text = f"🆘 *Emergency Help:*\n\n{tip}\n\nYou can do this! Stay strong!"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Another Tip", callback_data="back_to_emergency")],
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text=emergency_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return EMERGENCY_HELP

# Show achievements
def show_achievements(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT achievement, achieved_date FROM achievements WHERE user_id = ? ORDER BY achieved_date",
        (user_id,)
    )
    achievements = cursor.fetchall()
    
    achievement_descriptions = {
        "3_days": "🥉 3 days without relapse",
        "7_days": "🥈 7 days without relapse",
        "14_days": "🥇 14 days without relapse",
        "28_days": "🏆 28 days without relapse"
    }
    
    if achievements:
        text = "🏆 *Your Achievements:*\n\n"
        
        for achievement, date in achievements:
            desc = achievement_descriptions.get(achievement, achievement)
            text += f"{desc} - received on {date}\n"
        
        # Show unearned achievements
        text += "\n*Upcoming Achievements:*\n"
        earned = [a[0] for a in achievements]
        
        for ach, desc in achievement_descriptions.items():
            if ach not in earned:
                text += f"☐ {desc}\n"
    else:
        text = (
            "🏆 *Achievements:*\n\n"
            "You don't have any achievements yet. Keep trying!\n\n"
            "*Available Achievements:*\n"
            "☐ 🥉 3 days without relapse\n"
            "☐ 🥈 7 days without relapse\n"
            "☐ 🥇 14 days without relapse\n"
            "☐ 🏆 28 days without relapse"
        )
    
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update.callback_query, type(None)):
        update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    # If this was a command, not a callback, return ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Reminder settings
def reminder_settings(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT reminder_enabled, reminder_time FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if result:
        enabled, time = result
        
        text = (
            f"⏰ *Reminder Settings*\n\n"
            f"Status: {'Enabled' if enabled else 'Disabled'}\n"
            f"Time: {time}\n\n"
            f"To change settings, use the following commands:\n"
            f"/reminder_on - Enable reminders\n"
            f"/reminder_off - Disable reminders\n"
            f"/set_time HH:MM - Set reminder time (e.g., /set_time 20:00)"
        )
        
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    conn.close()
    return ConversationHandler.END

# Enable reminders
def reminder_on(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET reminder_enabled = 1 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    
    cursor.execute(
        "SELECT reminder_time FROM users WHERE user_id = ?",
        (user_id,)
    )
    time = cursor.fetchone()[0]
    
    conn.close()
    
    update.message.reply_text(
        f"✅ Reminders enabled. You will receive notifications every day at {time}.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# Disable reminders
def reminder_off(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET reminder_enabled = 0 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()
    
    update.message.reply_text(
        "❌ Reminders disabled.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# Set reminder time
def set_reminder_time(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if not context.args or len(context.args) != 1:
        update.message.reply_text(
            "⚠️ Please specify time in HH:MM format, for example: /set_time 20:00",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    time_str = context.args[0]
    
    # Check time format
    try:
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError
    except ValueError:
        update.message.reply_text(
            "⚠️ Invalid time format. Please use HH:MM format, for example: 20:00",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Format time for saving
    formatted_time = f"{hours:02d}:{minutes:02d}"
    
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET reminder_time = ? WHERE user_id = ?",
        (formatted_time, user_id)
    )
    conn.commit()
    conn.close()
    
    update.message.reply_text(
        f"⏰ Reminder time set to {formatted_time}.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# Function to start chat
def start_chat(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    text = (
        "💬 *Community Chat*\n\n"
        "Here you can chat with other users, share experiences, and support each other.\n\n"
        "Just send a message, and it will be visible to all chat participants.\n"
        "To exit the chat, use the command /exit_chat"
    )
    
    # Add user to active chat dictionary
    context.user_data['in_chat'] = True
    
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # Send notification to everyone in chat about new user
    broadcast_message(context, f"👋 User {username} has joined the chat!", user_id)
    
    return ConversationHandler.END

# Function to exit chat
def exit_chat(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Remove user from active chat dictionary
    if 'in_chat' in context.user_data:
        del context.user_data['in_chat']
    
    update.message.reply_text(
        "You have left the community chat. Use /chat to return to the chat.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Send notification to everyone in chat about user leaving
    broadcast_message(context, f"👋 User {username} has left the chat.", user_id)
    
    return ConversationHandler.END

# Handle chat messages
def handle_chat_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    message_text = update.message.text

    # Проверяем, находится ли пользователь в чате
    if not context.user_data.get('in_chat', False):
        return

    # Сохраняем сообщение в БД
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO chat_messages (user_id, username, message, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, username, message_text, timestamp)
    )
    conn.commit()
    conn.close()

    # Отправляем сообщение всем пользователям в чате
    formatted_message = f"💬 {username}: {message_text}"
    broadcast_message(context, formatted_message, user_id)

    return ConversationHandler.END

# Функция для рассылки сообщений всем пользователям в чате
def broadcast_message(context, message, sender_id=None):
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()

    # Получаем всех пользователей
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    conn.close()

    # Отправляем сообщение всем, кроме отправителя
    for user in users:
        user_id = user[0]
        if user_id != sender_id:
            try:
                context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

# Функция для проверки напоминаний
def check_reminders(context: CallbackContext):
    try:
        send_reminders(context)
    except Exception as e:
        logger.error(f"Ошибка при проверке напоминаний: {e}")

# Функция для поддержания работы Replit
def keep_alive():
    while True:
        time.sleep(60)

def main():
    # Инициализация базы данных
    init_db()

    # Создание Updater
    updater = Updater(TOKEN)

    # Получение диспетчера для регистрации обработчиков
    dispatcher = updater.dispatcher

    # Создание ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('help', help_command),
            CommandHandler('checkin', checkin),
            CommandHandler('stats', show_stats),
            CommandHandler('task', daily_task),
            CommandHandler('motivation', motivation),
            CommandHandler('emergency', emergency),
            CommandHandler('achievements', show_achievements),
            CommandHandler('reminder', reminder_settings),
            CommandHandler('reminder_on', reminder_on),
            CommandHandler('reminder_off', reminder_off),
            CommandHandler('set_time', set_reminder_time),
            CommandHandler('chat', start_chat),
            CommandHandler('exit_chat', exit_chat)
        ],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(button_handler)
            ],
            HELP_MENU: [
                CallbackQueryHandler(button_handler)
            ],
            EMERGENCY_HELP: [
                CallbackQueryHandler(button_handler)
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    dispatcher.add_handler(conv_handler)

    # Обработчик текстовых сообщений для чата
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_chat_message))

    # Запускаем Job для проверки напоминаний каждую минуту
    job_queue = updater.job_queue
    job_queue.run_repeating(check_reminders, interval=60, first=0)

    # Запуск бота в отдельном потоке для keep_alive
    Thread(target=keep_alive).start()

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()