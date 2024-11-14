from cryptography.fernet import Fernet
from config.settings import ENCRYPTION_KEY
import base64
import hashlib


# Генерация ключа для Fernet на основе ENCRYPTION_KEY
def get_cipher():
    # Преобразуем секретный ключ в 32-байтовый ключ для Fernet
    key = hashlib.sha256(ENCRYPTION_KEY.encode()).digest()
    # Кодируем ключ в формате base64
    key = base64.urlsafe_b64encode(key)
    return Fernet(key)


def encrypt(plain_text):
    cipher = get_cipher()
    # Шифруем текст, преобразовав его в байты
    encrypted_text = cipher.encrypt(plain_text.encode())
    # Преобразуем зашифрованные данные в строку для хранения
    return encrypted_text.decode()


def decrypt(encrypted_text):
    cipher = get_cipher()
    # Дешифруем данные, преобразовав их в байты
    decrypted_text = cipher.decrypt(encrypted_text.encode())
    # Возвращаем исходный текст
    return decrypted_text.decode()
