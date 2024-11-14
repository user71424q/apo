import logging
from logging.handlers import RotatingFileHandler
import sys
from config.settings import LOGGING_LEVEL

# Создание логгера
logger = logging.getLogger("vk_bot")
logger.setLevel(LOGGING_LEVEL)

# Формат логирования
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Создание обработчика для вывода в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(LOGGING_LEVEL)
console_handler.setFormatter(formatter)

# Создание обработчика для записи в файл
file_handler = RotatingFileHandler('logs/bot.log', maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(LOGGING_LEVEL)
file_handler.setFormatter(formatter)

# Добавление обработчиков к логгеру
logger.addHandler(console_handler)
# logger.addHandler(file_handler)
