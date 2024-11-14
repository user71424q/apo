import os
import sqlite3
import json
from typing import Optional, Dict, Any, List
from utils.logger import logger


class ChatManager:
    def __init__(self, db_path: str = 'data/chats.db'):
        """
        Инициализация ChatManager с использованием SQLite базы данных.
        :param db_path: Путь к файлу базы данных SQLite.
        """
        logger.debug("Инициализация ChatManager")
        self.db_path = db_path

        # Убедитесь, что директория для базы данных существует
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Инициализация базы данных и таблиц
        self._initialize_database()

    def _initialize_database(self):
        """
        Создаёт таблицы `chats` и `modules` в базе данных, если они ещё не существуют.
        Таблица `chats` содержит `chat_id` и `settings` в формате JSON.
        Таблица `modules` содержит информацию о доступных модулях.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Создание таблицы `chats`
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    settings TEXT NOT NULL
                )
            """)
            # Создание таблицы `modules`
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS modules (
                    module_name TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    description TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
            logger.debug("Таблицы 'chats' и 'modules' инициализированы в базе данных.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")

    def get_chat_settings(self, chat_id: int) -> Dict[str, Any]:
        """
        Получает настройки для заданного чата.
        :param chat_id: Идентификатор чата.
        :return: Словарь настроек чата или пустой словарь, если настройки не найдены.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT settings FROM chats WHERE chat_id = ?", (chat_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                settings = json.loads(row[0])
                logger.debug(f"Настройки для чата {chat_id} получены: {settings}")
                return settings
            else:
                logger.debug(f"Настройки для чата {chat_id} не найдены.")
                return {}
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Ошибка получения настроек для чата {chat_id}: {e}")
            return {}

    def get_chat_settings_string(self, chat_id: int) -> str:
        """
        Формирует строку с перечнем подключенных модулей и именем чата в читаемом формате.
        :param chat_id: Идентификатор чата.
        :return: Строка, описывающая имя чата и подключенные модули.
        """
        settings = self.get_chat_settings(chat_id)
        chat_name = settings.get("name", f"Чат #{chat_id}")
        modules = settings.get("modules", [])

        # Если нет модулей, возвращаем сообщение
        if not modules:
            return f"{chat_name}:\nНет подключенных модулей"

        # Получение информации о модулях из таблицы `modules`
        module_details = []
        for module in modules:
            module_info = self.get_module_info(module)
            if module_info:
                module_details.append(f"{module_info['display_name']}: {module_info['description']}")
            else:
                # Если информация о модуле не найдена, отображаем название из настроек
                module_details.append(f"{module}: Описание недоступно")

        return f"{chat_name}:\nПодключенные модули:\n" + "\n".join(module_details)

    def get_module_info(self, module_name: str) -> Optional[Dict[str, str]]:
        """
        Получает информацию о модуле из таблицы `modules`.
        :param module_name: Название модуля.
        :return: Словарь с `display_name` и `description`, или None, если модуль не найден.
        """
        logger.debug(f"Получение информации о модуле '{module_name}'")
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT display_name, description FROM modules WHERE module_name = ?", (module_name,))
            row = cursor.fetchone()
            conn.close()
            if row:
                info = {"display_name": row[0], "description": row[1]}
                logger.debug(f"Информация о модуле '{module_name}': {info}")
                return info
            else:
                logger.debug(f"Модуль '{module_name}' не найден в таблице 'modules'.")
                return None
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения информации о модуле '{module_name}': {e}")
            return None

    def set_chat_settings(self, chat_id: int, settings: Dict[str, Any]):
        """
        Сохраняет настройки для заданного чата в базе данных.
        :param chat_id: Идентификатор чата.
        :param settings: Словарь настроек чата.
        """
        logger.debug(f"Сохранение настроек для чата {chat_id}: {settings}")
        try:
            settings_json = json.dumps(settings, ensure_ascii=False)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chats (chat_id, settings)
                VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET settings=excluded.settings
            """, (chat_id, settings_json))
            conn.commit()
            conn.close()
            logger.debug(f"Настройки для чата {chat_id} сохранены.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка сохранения настроек для чата {chat_id}: {e}")

    def enable_module(self, chat_id: int, module_name: str):
        """
        Включает указанный модуль для заданного чата.
        :param chat_id: Идентификатор чата.
        :param module_name: Название модуля для включения.
        """
        logger.debug(f"Включение модуля '{module_name}' для чата {chat_id}")
        settings = self.get_chat_settings(chat_id)
        modules = settings.get("modules", [])
        if module_name not in modules:
            modules.append(module_name)
            settings["modules"] = modules
            self.set_chat_settings(chat_id, settings)
            logger.debug(f"Модуль '{module_name}' включён для чата {chat_id}.")
        else:
            logger.debug(f"Модуль '{module_name}' уже включён для чата {chat_id}.")

    def disable_module(self, chat_id: int, module_name: str):
        """
        Отключает указанный модуль для заданного чата.
        :param chat_id: Идентификатор чата.
        :param module_name: Название модуля для отключения.
        """
        logger.debug(f"Отключение модуля '{module_name}' для чата {chat_id}")
        settings = self.get_chat_settings(chat_id)
        modules = settings.get("modules", [])
        if module_name in modules:
            modules.remove(module_name)
            settings["modules"] = modules
            self.set_chat_settings(chat_id, settings)
            logger.debug(f"Модуль '{module_name}' отключён для чата {chat_id}.")
        else:
            logger.debug(f"Модуль '{module_name}' не был включён для чата {chat_id}.")

    def get_chats_with_module(self, module_name: str) -> List[Dict[str, Any]]:
        """
        Возвращает список чатов, в которых включен указанный модуль.
        :param module_name: Название модуля.
        :return: Список словарей с информацией о чатах.
        """
        logger.debug(f"Получение списка чатов с модулем '{module_name}'")
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT chat_id, settings FROM chats
                WHERE JSON_EXTRACT(settings, '$.modules') LIKE ?
            """, (f'%{module_name}%',))
            rows = cursor.fetchall()
            conn.close()
            chats_with_module = []
            for row in rows:
                chat_id, settings_json = row
                settings = json.loads(settings_json)
                chat_info = {
                    "id": chat_id,
                    "name": settings.get("name", f"Chat {chat_id}")
                }
                chats_with_module.append(chat_info)
                logger.debug(f"Чат с модулем '{module_name}' добавлен в список: {chat_info}")
            logger.debug(f"Найдено {len(chats_with_module)} чатов с модулем '{module_name}'.")
            return chats_with_module
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Ошибка при получении чатов с модулем '{module_name}': {e}")
            return []

    def add_module(self, module_name: str, display_name: str, description: str):
        """
        Добавляет новый модуль в таблицу `modules`.
        :param module_name: Уникальное название модуля.
        :param display_name: Отображаемое название модуля.
        :param description: Описание модуля.
        """
        logger.debug(f"Добавление нового модуля '{module_name}'")
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO modules (module_name, display_name, description)
                VALUES (?, ?, ?)
                ON CONFLICT(module_name) DO UPDATE SET display_name=excluded.display_name, description=excluded.description
            """, (module_name, display_name, description))
            conn.commit()
            conn.close()
            logger.debug(f"Модуль '{module_name}' добавлен или обновлён в таблице 'modules'.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления модуля '{module_name}': {e}")

    def remove_module(self, module_name: str):
        """
        Удаляет модуль из таблицы `modules`.
        :param module_name: Название модуля для удаления.
        """
        logger.debug(f"Удаление модуля '{module_name}' из таблицы 'modules'")
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM modules WHERE module_name = ?", (module_name,))
            conn.commit()
            conn.close()
            logger.debug(f"Модуль '{module_name}' удалён из таблицы 'modules'.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка удаления модуля '{module_name}': {e}")
