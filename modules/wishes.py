# modules/wishes.py

import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from utils.logger import logger
import sqlite3
import os


class WishManager:
    """
    Менеджер желаний пользователей.
    Обрабатывает команды для добавления, отображения и управления желаниями.
    """

    # Сопоставление команд с регулярными выражениями
    COMMAND_PATTERNS = {
        "add_wish": re.compile(r'^/хочу\s+(.+)', re.IGNORECASE),
        "remove_wish": re.compile(r'^/не\s+хочу\s+(.+)', re.IGNORECASE),
        "who_wants": re.compile(r'^/кому\s+(.+)', re.IGNORECASE),
        "set_name_tagged": re.compile(r'^/я\s+\.\s+(.+)', re.IGNORECASE),
        "set_name": re.compile(r'^/я\s+(.+)', re.IGNORECASE),
        "show_wishes": re.compile(r'^/что\s+хочу', re.IGNORECASE),
        "help": re.compile(r'^/команды хотелки', re.IGNORECASE),
        "delete_user": re.compile(r'^/f\s+(\d+)', re.IGNORECASE),

    }

    def __init__(self, db_path: str = 'data/wishes.db'):
        """
        Инициализация менеджера желаний.
        Создаёт необходимые таблицы, если они не существуют.
        :param db_path: Путь к базе данных SQLite.
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()
        logger.debug("Инициализация WishManager")

    def create_tables(self):
        """
        Создание таблиц в базе данных, если они не существуют.
        """
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                display_name TEXT,
                is_tagged BOOLEAN DEFAULT 0
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT UNIQUE NOT NULL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS aliases (
                alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                alias_name TEXT UNIQUE NOT NULL,
                FOREIGN KEY(item_id) REFERENCES items(item_id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS wishes (
                user_id INTEGER,
                item_id INTEGER,
                PRIMARY KEY (user_id, item_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(item_id) REFERENCES items(item_id)
            )
        """)

        self.connection.commit()
        logger.debug("Таблицы в базе данных созданы или уже существуют.")

    def add_item(self, item_name: str) -> int:
        """
        Добавление нового предмета в базу данных.
        :param item_name: Название предмета.
        :return: ID добавленного предмета.
        """
        item_name = item_name.lower()
        self.cursor.execute("INSERT OR IGNORE INTO items (item_name) VALUES (?)", (item_name,))
        self.connection.commit()
        self.cursor.execute("SELECT item_id FROM items WHERE item_name = ?", (item_name,))
        result = self.cursor.fetchone()
        return result[0] if result else -1

    def add_alias(self, item_name: str, alias_name: str) -> None:
        """
        Добавление псевдонима для предмета.
        :param item_name: Название предмета.
        :param alias_name: Псевдоним предмета.
        """
        item_name = item_name.lower()
        alias_name = alias_name.lower()
        self.cursor.execute("SELECT item_id FROM items WHERE item_name = ?", (item_name,))
        result = self.cursor.fetchone()
        if result:
            item_id = result[0]
            self.cursor.execute("INSERT OR IGNORE INTO aliases (item_id, alias_name) VALUES (?, ?)", (item_id, alias_name))
            self.connection.commit()
            logger.debug(f"Добавлен псевдоним '{alias_name}' для предмета '{item_name}'")
        else:
            logger.warning(f"Предмет '{item_name}' не найден. Псевдоним '{alias_name}' не добавлен.")

    def get_item_id(self, name: str) -> Optional[int]:
        """
        Получение ID предмета по его названию или псевдониму.
        :param name: Название или псевдоним предмета.
        :return: ID предмета или None, если не найден.
        """
        name = name.lower()
        self.cursor.execute("SELECT item_id FROM items WHERE item_name = ?", (name,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        self.cursor.execute("SELECT item_id FROM aliases WHERE alias_name = ?", (name,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_wish(self, user_id: int, item_id: int) -> bool:
        """
        Добавление предмета в список желаний пользователя.
        :param user_id: ID пользователя.
        :param item_id: ID предмета.
        :return: True, если добавлено, False, если уже в списке.
        """
        try:
            self.cursor.execute("INSERT INTO wishes (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
            self.connection.commit()
            logger.debug(f"Пользователь {user_id} добавил предмет {item_id} в свой список желаний.")
            return True
        except sqlite3.IntegrityError:
            logger.debug(f"Пользователь {user_id} уже имеет предмет {item_id} в своем списке желаний.")
            return False

    def remove_wish(self, user_id: int, item_id: int) -> bool:
        """
        Удаление предмета из списка желаний пользователя.
        :param user_id: ID пользователя.
        :param item_id: ID предмета.
        :return: True, если удалено, False, если предмет не был в списке.
        """
        self.cursor.execute("DELETE FROM wishes WHERE user_id = ? AND item_id = ?", (user_id, item_id))
        self.connection.commit()
        if self.cursor.rowcount > 0:
            logger.debug(f"Пользователь {user_id} удалил предмет {item_id} из своего списка желаний.")
            return True
        else:
            logger.debug(f"Пользователь {user_id} попытался удалить предмет {item_id}, которого нет в списке.")
            return False


    def get_users_with_wish(self, item_id: int) -> List[Dict[str, Any]]:
        """
        Получение списка пользователей, желающих данный предмет.
        :param item_id: ID предмета.
        :return: Список словарей с информацией о пользователях.
        """
        self.cursor.execute("""
            SELECT user_id, display_name, is_tagged FROM users
            WHERE user_id IN (
                SELECT user_id FROM wishes WHERE item_id = ?
            )
        """, (item_id,))
        results = self.cursor.fetchall()
        users = []
        for row in results:
            user = {
                "user_id": row[0],
                "display_name": row[1],
                "is_tagged": bool(row[2])
            }
            users.append(user)
        return users

    def set_display_name(self, user_id: int, display_name: str, is_tagged: bool = False) -> None:
        """
        Установка отображаемого имени пользователя.
        :param user_id: ID пользователя.
        :param display_name: Отображаемое имя.
        :param is_tagged: Флаг, указывающий, должно ли имя быть с тегом.
        """
        if is_tagged:
            display_name = f"[id{user_id}|{display_name}]"
        self.cursor.execute("""
            INSERT INTO users (user_id, display_name, is_tagged)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name=excluded.display_name,
                is_tagged=excluded.is_tagged
        """, (user_id, display_name, int(is_tagged)))
        self.connection.commit()
        logger.debug(f"Установлено имя для пользователя {user_id}: {display_name} (is_tagged={is_tagged})")
        
    def delete_user(self, target_user_id: int) -> bool:
        """
        Полное удаление пользователя из базы данных, включая его желания.
        :param target_user_id: ID пользователя для удаления.
        :return: True, если пользователь был удалён, False, если пользователь не найден.
        """
        self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_user_id,))
        user_exists = self.cursor.fetchone()
        if not user_exists:
            logger.debug(f"Пользователь {target_user_id} не найден в базе данных.")
            return False

        # Удаление из таблицы wishes
        self.cursor.execute("DELETE FROM wishes WHERE user_id = ?", (target_user_id,))
        # Удаление из таблицы users
        self.cursor.execute("DELETE FROM users WHERE user_id = ?", (target_user_id,))
        self.connection.commit()
        logger.debug(f"Пользователь {target_user_id} полностью удалён из базы данных.")
        return True


    def get_user_wishes(self, user_id: int) -> List[str]:
        """
        Получение списка желаний пользователя.
        :param user_id: ID пользователя.
        :return: Список названий предметов.
        """
        self.cursor.execute("""
            SELECT items.item_name FROM items
            JOIN wishes ON items.item_id = wishes.item_id
            WHERE wishes.user_id = ?
        """, (user_id,))
        results = self.cursor.fetchall()
        return [row[0] for row in results]

    async def check_wish_events(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Обработка входящих сообщений и выполнение соответствующих команд.
        :param message: Словарь сообщения.
        :return: Ответное сообщение или None.
        """
        text = message.get('text', '').strip()
        user_id = message.get('from_id')  # ID пользователя, отправившего сообщение
        peer_id = message.get('peer_id', 0)
        logger.debug(f"Получено сообщение для wishes: user_id={user_id}, peer_id={peer_id}, text='{text}'")

        if not text or not user_id:
            logger.debug("Пустое сообщение или отсутствует user_id. Пропуск.")
            return None

        # Проверка на каждую команду
        for command, pattern in self.COMMAND_PATTERNS.items():
            match = pattern.match(text)
            if match:
                if command == "add_wish":
                    item_name = match.group(1).strip()
                    return self.handle_add_wish(user_id, item_name)
                elif command == "remove_wish":
                    item_name = match.group(1).strip()
                    return self.handle_remove_wish(user_id, item_name)
                elif command == "who_wants":
                    item_name = match.group(1).strip()
                    return self.handle_who_wants(item_name)
                elif command == "set_name_tagged":
                    name = match.group(1).strip()
                    return self.handle_set_name(user_id, name, is_tagged=True)
                elif command == "set_name":
                    name = match.group(1).strip()
                    return self.handle_set_name(user_id, name, is_tagged=False)
                elif command == "show_wishes":
                    return self.handle_show_wishes(user_id)
                elif command == "help":
                    return self.handle_help()
                elif command == "delete_user":
                    target_user_id = int(match.group(1))
                    return self.handle_delete_user(target_user_id)
        # Если сообщение не соответствует ни одной команде, возвращаем None
        return None

    def handle_add_wish(self, user_id: int, item_name: str) -> Optional[str]:
        """
        Обработка команды добавления желания.
        :param user_id: ID пользователя.
        :param item_name: Название предмета или его псевдоним.
        :return: Ответное сообщение или None.
        """
        # Проверка наличия пользователя в таблице users
        self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user_exists = self.cursor.fetchone()
        if not user_exists:
            return "Пожалуйста, установите своё имя с помощью команды /я перед добавлением желаний."
        
        item_id = self.get_item_id(item_name)
        if not item_id:
            logger.debug(f"Предмет '{item_name}' не найден.")
            return f"Предмет '{item_name}' не найден."
        success = self.add_wish(user_id, item_id)
        if success:
            return f"Предмет '{item_name}' добавлен в ваш список желаний."
        else:
            return f"Предмет '{item_name}' уже в вашем списке желаний."


    def handle_who_wants(self, item_name: str) -> Optional[str]:
        """
        Обработка команды просмотра, кто желает данный предмет.
        :param item_name: Название предмета или его псевдоним.
        :return: Ответное сообщение или None.
        """
        item_id = self.get_item_id(item_name)
        if not item_id:
            logger.debug(f"Предмет '{item_name}' не найден.")
            return f"Предмет '{item_name}' не найден."

        users = self.get_users_with_wish(item_id)
        if not users:
            return f"Никто не желает предмет '{item_name}'."

        response = f"{item_name} интересует:"
        for user in users:
            response += f"\n{user['display_name']}"
        return response


    def handle_delete_user(self, target_user_id: int) -> Optional[str]:
        """
        Обработка секретной команды удаления пользователя из базы данных.
        :param target_user_id: ID пользователя для удаления.
        :return: Ответное сообщение или None.
        """
        success = self.delete_user(target_user_id)
        if success:
            return f"Пользователь с ID {target_user_id} успешно удалён из базы данных."
        else:
            return f"Пользователь с ID {target_user_id} не найден в базе данных."


    def handle_set_name(self, user_id: int, name: str, is_tagged: bool) -> Optional[str]:
        """
        Обработка команды установки отображаемого имени.
        :param user_id: ID пользователя.
        :param name: Отображаемое имя.
        :param is_tagged: Флаг, указывающий, нужно ли тегировать имя.
        :return: Ответное сообщение или None.
        """
        self.set_display_name(user_id, name, is_tagged)
        return f"Ваше имя установлено как {name}."

    def handle_show_wishes(self, user_id: int) -> Optional[str]:
        """
        Обработка команды показа списка желаний пользователя.
        :param user_id: ID пользователя.
        :return: Ответное сообщение или None.
        """
        wishes = self.get_user_wishes(user_id)
        if not wishes:
            return "Ты познал дзен и ничего не хочешь"
        wish_list = "\n".join([f"- {item}" for item in wishes])
        return f"Ваш список желаний:\n{wish_list}"
    
    
    def handle_remove_wish(self, user_id: int, item_name: str) -> Optional[str]:
        """
        Обработка команды удаления желания.
        :param user_id: ID пользователя.
        :param item_name: Название предмета или его псевдоним.
        :return: Ответное сообщение или None.
        """
        item_id = self.get_item_id(item_name)
        if not item_id:
            logger.debug(f"Предмет '{item_name}' не найден.")
            return f"Предмет '{item_name}' не найден."

        success = self.remove_wish(user_id, item_id)
        if success:
            return f"Предмет '{item_name}' удалён из вашего списка желаний."
        else:
            return f"А хотел?"

    
    
    def handle_help(self) -> Optional[str]:
        """
        Обработка команды помощи.
        :return: Ответное сообщение со справкой или None.
        """
        help_text = (
            "📜 **Список доступных команд для управления желаниями:**\n\n"
            "**/хочу [предмет]**\n"
            "Добавляет указанный предмет в ваш список желаний.\n\n"
            "**/не хочу [предмет]**\n"
            "Удаляет указанный предмет из вашего списка желаний.\n\n"
            "**/кому [предмет]**\n"
            "Показывает список пользователей, которые желают указанный предмет.\n\n"
            "**/я [имя]**\n"
            "Устанавливает ваше отображаемое имя без тега.\n\n"
            "**/я . [имя]**\n"
            "Устанавливает ваше отображаемое имя с тегом. Пример: [id123456|Ваше Имя]\n\n"
            "**/что хочу**\n"
            "Показывает ваш текущий список желаний.\n\n"
            "**/команды хотелки**\n"
            "Показывает это справочное сообщение."
        )
        return help_text


