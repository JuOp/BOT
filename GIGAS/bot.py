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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токена бота из переменной окружения
TOKEN = os.environ['TELEGRAM_TOKEN']

# Константы для ConversationHandler
MAIN_MENU, HELP_MENU, EMERGENCY_HELP = range(3)

# Мотивационные цитаты
QUOTES = [
    "Самоконтроль сегодня - это сила завтра.",
    "Каждый день без зависимости - это победа над собой.",
    "Сложно сегодня - легче завтра.",
    "Твоя сила не в том, чтобы не упасть, а в том, чтобы подняться.",
    "Преодолей себя сегодня и стань сильнее завтра.",
    "Настоящая сила - уметь сказать 'нет' своим слабостям.",
    "Ты сильнее, чем думаешь.",
    "Каждый новый день - это новая возможность стать лучше.",
    "Твоя жизнь меняется, когда меняешься ты сам.",
    "Дисциплина - это мост между целями и достижениями."
]

# Задания для пользователей
TASKS = [
    "Сделай 20 отжиманий, когда почувствуешь искушение.",
    "Выпей стакан воды и сделай 10 глубоких вдохов.",
    "Выйди на 10-минутную прогулку на свежем воздухе.",
    "Примите холодный душ.",
    "Почитай книгу в течение 30 минут.",
    "Позвони другу или члену семьи.",
    "Медитируй в течение 10 минут.",
    "Запиши свои мысли и чувства в дневник.",
    "Сделай растяжку или йогу в течение 15 минут.",
    "Нарисуй или напиши о своих целях на будущее."
]

# Экстренная помощь
EMERGENCY_TIPS = [
    "Сделай 20 отжиманий прямо сейчас!",
    "Немедленно выйди из комнаты и пройдись.",
    "Включи холодный душ и постой под ним 30 секунд.",
    "Позвони другу прямо сейчас.",
    "Сделай 50 прыжков на месте.",
    "Сконцентрируйся на дыхании: вдох на 4 счета, задержка на 4, выдох на 4.",
    "Выпей стакан холодной воды.",
    "Сделай планку на 1 минуту.",
    "Закрой глаза и сосчитай до 100.",
    "Включи любимую энергичную музыку и подвигайся под неё."
]

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    # Создание таблицы пользователей
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
    
    # Создание таблицы достижений
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement TEXT,
        achieved_date TEXT,
        PRIMARY KEY (user_id, achievement)
    )
    ''')
    
    # Создание таблицы для чата
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

# Функция для регистрации пользователя
def register_user(user_id, username):
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    # Проверка, зарегистрирован ли пользователь
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

# Функция для проверки достижений
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
            achievements.append("🥉 3 дня без срывов!")
    
    if streak >= 7:
        cursor.execute(
            "INSERT OR IGNORE INTO achievements (user_id, achievement, achieved_date) VALUES (?, ?, ?)",
            (user_id, "7_days", today)
        )
        if cursor.rowcount > 0:
            achievements.append("🥈 7 дней без срывов!")
    
    if streak >= 14:
        cursor.execute(
            "INSERT OR IGNORE INTO achievements (user_id, achievement, achieved_date) VALUES (?, ?, ?)",
            (user_id, "14_days", today)
        )
        if cursor.rowcount > 0:
            achievements.append("🥇 14 дней без срывов!")
    
    if streak >= 28:
        cursor.execute(
            "INSERT OR IGNORE INTO achievements (user_id, achievement, achieved_date) VALUES (?, ?, ?)",
            (user_id, "28_days", today)
        )
        if cursor.rowcount > 0:
            achievements.append("🏆 28 дней без срывов! Ты победитель!")
    
    conn.commit()
    conn.close()
    
    return achievements

# Функция для отправки напоминаний
def send_reminders(context: CallbackContext):
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    current_time = datetime.datetime.now().strftime("%H:%M")
    
    # Получение пользователей, у которых включены напоминания и текущее время совпадает с временем напоминания
    cursor.execute(
        "SELECT user_id FROM users WHERE reminder_enabled = 1 AND reminder_time = ?",
        (current_time,)
    )
    
    users = cursor.fetchall()
    conn.close()
    
    for user in users:
        try:
            quote = random.choice(QUOTES)
            message = f"📝 *Ежедневное напоминание*\n\n_{quote}_\n\nНе забудьте отметиться сегодня! /checkin"
            
            context.bot.send_message(
                chat_id=user[0],
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания: {e}")

# Команда /start
def start(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    
    # Регистрация пользователя
    is_new = register_user(user.id, user.username or user.first_name)
    
    if is_new:
        message = (
            f"👋 Привет, {user.first_name}! Я бот, который поможет тебе преодолеть зависимость и "
            f"стать лучшей версией себя.\n\n"
            f"🔰 *Что я умею:*\n"
            f"✅ Ежедневные отметки для отслеживания прогресса\n"
            f"📝 Ежедневные задания для личностного роста\n"
            f"🖼 Мотивационные цитаты и изображения\n"
            f"🆘 Экстренная помощь в моменты слабости\n"
            f"🏆 Система достижений\n\n"
            f"Используй /help для получения списка команд."
        )
    else:
        message = (
            f"С возвращением, {user.first_name}! Рад видеть тебя снова.\n\n"
            f"Используй /help для получения списка команд или воспользуйся меню ниже."
        )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Отметиться", callback_data="checkin"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton("📝 Задание дня", callback_data="task"),
            InlineKeyboardButton("🖼 Мотивация", callback_data="motivation")
        ],
        [
            InlineKeyboardButton("🆘 Экстренная помощь", callback_data="emergency"),
            InlineKeyboardButton("🏆 Достижения", callback_data="achievements")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return MAIN_MENU

# Команда /help
def help_command(update: Update, context: CallbackContext) -> int:
    help_text = (
        "*Список команд:*\n\n"
        "/start - Начать работу с ботом\n"
        "/checkin - Отметиться на сегодня\n"
        "/stats - Показать вашу статистику\n"
        "/task - Получить задание дня\n"
        "/motivation - Получить мотивационную цитату\n"
        "/emergency - Экстренная помощь при искушении\n"
        "/achievements - Посмотреть свои достижения\n"
        "/reminder - Настроить ежедневные напоминания\n"
        "/chat - Присоединиться к чату сообщества\n"
        "/help - Показать эту справку"
    )
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return HELP_MENU

# Обработка кнопок
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

# Показать главное меню
def show_main_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Отметиться", callback_data="checkin"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton("📝 Задание дня", callback_data="task"),
            InlineKeyboardButton("🖼 Мотивация", callback_data="motivation")
        ],
        [
            InlineKeyboardButton("🆘 Экстренная помощь", callback_data="emergency"),
            InlineKeyboardButton("🏆 Достижения", callback_data="achievements")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="Главное меню. Выберите действие:",
        reply_markup=reply_markup
    )
    
    return MAIN_MENU

# Отметка о прохождении дня
def checkin(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('nofap_bot.db')
    cursor = conn.cursor()
    
    # Получение текущей даты
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Проверка, отмечался ли пользователь сегодня
    cursor.execute(
        "SELECT last_check_in, streak FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if result:
        last_check_in, streak = result
        
        # Проверка, не отмечался ли уже сегодня
        if last_check_in == today:
            if isinstance(update.callback_query, type(None)):
                update.message.reply_text("Вы уже отметились сегодня! Приходите завтра.")
            else:
                update.callback_query.edit_message_text("Вы уже отметились сегодня! Приходите завтра.")
        else:
            # Вычисление разницы дней
            last_date = datetime.datetime.strptime(last_check_in, "%Y-%m-%d")
            current_date = datetime.datetime.strptime(today, "%Y-%m-%d")
            days_diff = (current_date - last_date).days
            
            if days_diff == 1:
                # Последовательные дни, увеличиваем streak
                new_streak = streak + 1
                message = f"✅ Отлично! Ваша серия без срывов: {new_streak} дней подряд!"
            elif days_diff > 1:
                # Пропущены дни, сбрасываем streak
                new_streak = 1
                message = "✅ Отметка принята. К сожалению, ваша серия была сброшена из-за пропущенных дней. Новая серия: 1 день."
            else:
                # Что-то не так с датами
                new_streak = streak
                message = "✅ Отметка принята."
            
            # Обновление данных пользователя
            cursor.execute(
                "UPDATE users SET last_check_in = ?, streak = ?, longest_streak = MAX(longest_streak, ?) WHERE user_id = ?",
                (today, new_streak, new_streak, user_id)
            )
            conn.commit()
            
            # Проверка достижений
            achievements = check_achievements(user_id, new_streak)
            
            if achievements:
                message += "\n\n🏆 *Новые достижения:*\n" + "\n".join(achievements)
                
                # Проверка на 28 дней
                if new_streak >= 28:
                    message += "\n\n🎁 *Поздравляем с достижением 28 дней!*\nВаш подарок: [Перейти на сайт](https://вашссылка.ru)"
            
            if isinstance(update.callback_query, type(None)):
                update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            else:
                update.callback_query.edit_message_text(text=message, parse_mode=ParseMode.MARKDOWN)
    
    conn.close()
    
    # Если это была команда, а не callback, возвращаем ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Показать статистику
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
        
        # Вычисление общего количества дней с начала
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        today = datetime.datetime.now()
        total_days = (today - start).days + 1
        
        stats_text = (
            f"📊 *Ваша статистика:*\n\n"
            f"📅 Дата начала: {start_date}\n"
            f"📈 Текущая серия: {streak} дней\n"
            f"🏆 Рекордная серия: {longest_streak} дней\n"
            f"⏱ Всего дней с начала пути: {total_days}"
        )
        
        keyboard = [
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if isinstance(update.callback_query, type(None)):
            update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            update.callback_query.edit_message_text(text=stats_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    conn.close()
    
    # Если это была команда, а не callback, возвращаем ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Ежедневное задание
def daily_task(update: Update, context: CallbackContext) -> int:
    task = random.choice(TASKS)
    
    task_text = f"📝 *Задание дня:*\n\n{task}\n\nВыполните это задание и станьте на шаг ближе к вашей цели!"
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update.callback_query, type(None)):
        update.message.reply_text(task_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        update.callback_query.edit_message_text(text=task_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    # Если это была команда, а не callback, возвращаем ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Мотивационная цитата
def motivation(update: Update, context: CallbackContext) -> int:
    quote = random.choice(QUOTES)
    
    motivation_text = f"🖼 *Мотивация дня:*\n\n_{quote}_"
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update.callback_query, type(None)):
        update.message.reply_text(motivation_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        update.callback_query.edit_message_text(text=motivation_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    # Если это была команда, а не callback, возвращаем ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Экстренная помощь
def emergency(update: Update, context: CallbackContext) -> int:
    emergency_text = (
        "🆘 *Экстренная помощь*\n\n"
        "Чувствуете искушение? Мы здесь, чтобы помочь вам!\n"
        "Выберите тип помощи ниже:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💪 Физическое упражнение", callback_data="emergency_tip_physical")],
        [InlineKeyboardButton("🧠 Ментальная техника", callback_data="emergency_tip_mental")],
        [InlineKeyboardButton("🚿 Холодный душ", callback_data="emergency_tip_shower")],
        [InlineKeyboardButton("🔄 Отвлечение", callback_data="emergency_tip_distraction")],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update.callback_query, type(None)):
        update.message.reply_text(emergency_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        update.callback_query.edit_message_text(text=emergency_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    # Если это была команда, а не callback, возвращаем EMERGENCY_HELP
    if isinstance(update.callback_query, type(None)):
        return EMERGENCY_HELP
    
    return EMERGENCY_HELP

# Отправка конкретного совета для экстренной помощи
def send_emergency_tip(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    tip_type = query.data.replace("emergency_tip_", "")
    
    tips = {
        "physical": [
            "Сделайте 20 отжиманий прямо сейчас!",
            "Выполните 30 приседаний.",
            "Сделайте планку на 1 минуту."
        ],
        "mental": [
            "Сконцентрируйтесь на дыхании: вдох на 4 счета, задержка на 4, выдох на 4.",
            "Закройте глаза и сосчитайте до 100.",
            "Медитируйте в течение 5 минут, фокусируясь на дыхании."
        ],
        "shower": [
            "Примите холодный душ на 30-60 секунд.",
            "Умойтесь холодной водой несколько раз.",
            "Подержите руки под холодной водой в течение минуты."
        ],
        "distraction": [
            "Позвоните другу или члену семьи.",
            "Выйдите на короткую прогулку.",
            "Включите любимую энергичную музыку и подвигайтесь под неё."
        ]
    }
    
    if tip_type in tips:
        tip = random.choice(tips[tip_type])
        emergency_text = f"🆘 *Экстренная помощь:*\n\n{tip}\n\nВы справитесь! Оставайтесь сильными!"
    else:
        tip = random.choice(EMERGENCY_TIPS)
        emergency_text = f"🆘 *Экстренная помощь:*\n\n{tip}\n\nВы справитесь! Оставайтесь сильными!"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Другой совет", callback_data="back_to_emergency")],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text=emergency_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return EMERGENCY_HELP

# Показать достижения
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
        "3_days": "🥉 3 дня без срывов",
        "7_days": "🥈 7 дней без срывов",
        "14_days": "🥇 14 дней без срывов",
        "28_days": "🏆 28 дней без срывов"
    }
    
    if achievements:
        text = "🏆 *Ваши достижения:*\n\n"
        
        for achievement, date in achievements:
            desc = achievement_descriptions.get(achievement, achievement)
            text += f"{desc} - получено {date}\n"
        
        # Показать неполученные достижения
        text += "\n*Предстоящие достижения:*\n"
        earned = [a[0] for a in achievements]
        
        for ach, desc in achievement_descriptions.items():
            if ach not in earned:
                text += f"☐ {desc}\n"
    else:
        text = (
            "🏆 *Достижения:*\n\n"
            "У вас пока нет достижений. Продолжайте стараться!\n\n"
            "*Доступные достижения:*\n"
            "☐ 🥉 3 дня без срывов\n"
            "☐ 🥈 7 дней без срывов\n"
            "☐ 🥇 14 дней без срывов\n"
            "☐ 🏆 28 дней без срывов"
        )
    
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update.callback_query, type(None)):
        update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    # Если это была команда, а не callback, возвращаем ConversationHandler.END
    if isinstance(update.callback_query, type(None)):
        return ConversationHandler.END
    
    return MAIN_MENU

# Настройка напоминаний
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
            f"⏰ *Настройки напоминаний*\n\n"
            f"Статус: {'Включены' if enabled else 'Выключены'}\n"
            f"Время: {time}\n\n"
            f"Чтобы изменить настройки, используйте следующие команды:\n"
            f"/reminder_on - Включить напоминания\n"
            f"/reminder_off - Выключить напоминания\n"
            f"/set_time ЧЧ:ММ - Установить время напоминания (например, /set_time 20:00)"
        )
        
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    conn.close()
    return ConversationHandler.END

# Включение напоминаний
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
        f"✅ Напоминания включены. Вы будете получать уведомления каждый день в {time}.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# Выключение напоминаний
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
        "❌ Напоминания выключены.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# Установка времени напоминаний
def set_reminder_time(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if not context.args or len(context.args) != 1:
        update.message.reply_text(
            "⚠️ Пожалуйста, укажите время в формате ЧЧ:ММ, например: /set_time 20:00",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    time_str = context.args[0]
    
    # Проверка формата времени
    try:
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError
    except ValueError:
        update.message.reply_text(
            "⚠️ Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ, например: 20:00",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Форматирование времени для сохранения
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
        f"⏰ Время напоминаний установлено на {formatted_time}.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# Функция для запуска чата
def start_chat(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    text = (
        "💬 *Чат сообщества*\n\n"
        "Здесь вы можете общаться с другими пользователями, делиться опытом и поддерживать друг друга.\n\n"
        "Просто отправьте сообщение, и оно будет видно всем участникам чата.\n"
        "Для выхода из чата используйте команду /exit_chat"
    )
    
    # Добавляем пользователя в словарь активных чатов
    context.user_data['in_chat'] = True
    
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # Отправляем уведомление всем в чате о новом пользователе
    broadcast_message(context, f"👋 Пользователь {username} присоединился к чату!", user_id)
    
    return ConversationHandler.END

# Функция для выхода из чата
def exit_chat(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Удаляем пользователя из словаря активных чатов
    if 'in_chat' in context.user_data:
        del context.user_data['in_chat']
    
    update.message.reply_text(
        "Вы вышли из чата сообщества. Используйте /chat, чтобы вернуться в чат.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Отправляем уведомление всем в чате о выходе пользователя
    broadcast_message(context, f"👋 Пользователь {username} покинул чат.", user_id)
    
    return ConversationHandler.END

# Обработка сообщений в чате
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