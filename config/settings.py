import os
from dotenv import load_dotenv
load_dotenv()
# Токен вашей группы ВКонтакте
VK_API_TOKEN = os.getenv(
    "VK_API_TOKEN"
)  # Убедитесь, что вы установили эту переменную окружения

# ID вашей группы ВКонтакте
VK_GROUP_ID = os.getenv("VK_GROUP_ID")  # Тоже необходимо установить



# Ключ для шифрования токенов пользователей
ENCRYPTION_KEY = os.getenv(
    "ENCRYPTION_KEY"
)  # Генерируется один раз и хранится в безопасности

# Настройки логирования
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "DEBUG")
