# main.py - Упрощенный файл для отладки
import os
import logging
import sys
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токена из переменных окружения
TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Простые функции обработчики
def start(update: Update, context: CallbackContext) -> None:
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    update.message.reply_text(f'Привет, {user.first_name}! Я тестовый бот.')

def help_command(update: Update, context: CallbackContext) -> None:
    """Отправляет сообщение при команде /help."""
    update.message.reply_text('Доступные команды: /start, /help')

def main() -> None:
    """Запуск бота."""
    print(f"Запуск бота с токеном: {TOKEN[:5]}...{TOKEN[-5:]} (скрыт для безопасности)")

    # Создание Updater и передача ему токена бота
    updater = Updater(TOKEN)

    # Получение диспетчера для регистрации обработчиков
    dispatcher = updater.dispatcher

    # Регистрация обработчиков команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # Запуск бота
    print("Бот запускается...")
    updater.start_polling()
    print("Бот успешно запущен!")
    # Работа бота до нажатия Ctrl-C или получения сигнала остановки
    updater.idle()

if __name__ == '__main__':
    # Проверяем наличие токена
    if not TOKEN:
        print("ОШИБКА: Не найден токен Telegram. Добавьте TELEGRAM_TOKEN в переменные окружения Replit.")
        sys.exit(1)

    print("Запуск упрощенной версии бота для диагностики...")
    main()