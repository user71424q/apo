import sqlite3
from utils.logger import logger
from utils.encryption import encrypt, decrypt
import os
from datetime import datetime


class UserManager:
    def __init__(self):
        logger.debug("Инициализация UserManager")
        # Подключение к базе данных SQLite
        self.db_path = os.path.join("data", "users.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        # Создание таблицы users
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                role_name TEXT DEFAULT 'user'
            )
        """
        )

        # Создание таблицы auto_buff
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auto_buff (
                user_id INTEGER,
                chat_id INTEGER,
                group_chat_id INTEGER,
                token TEXT,
                role TEXT,
                buff_list TEXT,
                PRIMARY KEY (user_id, chat_id),
                CONSTRAINT unique_user_group UNIQUE (user_id, group_chat_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            """
        )

        # Создание таблицы profiles с указанными полями
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                strength INTEGER,
                agility INTEGER,
                endurance INTEGER,
                level INTEGER,
                attack INTEGER,
                defense INTEGER,
                luck INTEGER,
                last_updated DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """
        )

        # Сохранение изменений
        self.connection.commit()
        logger.debug("Таблицы в базе данных созданы или уже существуют.")

    def add_user(self, user_id, role_name="user"):
        # logger.debug(f"Добавление пользователя {user_id} с ролью {role_name}")
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO users (user_id, role_name)
            VALUES (?, ?)
        """,
            (user_id, role_name),
        )
        self.connection.commit()

    def set_auto_buff(
        self, user_id, chat_id, group_chat_id, token, role, buff_list=None
    ):
        logger.debug(f"Настройка авто бафа для пользователя {user_id} в чате {chat_id}")
        encrypted_token = encrypt(token)
        buff_list_str = buff_list if buff_list else ""
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO auto_buff (user_id, chat_id, group_chat_id, token, role, buff_list)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (user_id, chat_id, group_chat_id, encrypted_token, role, buff_list_str),
        )
        self.connection.commit()

    def get_auto_buff_by_group_chat_id(self, user_id, group_chat_id):
        logger.debug(
            f"Получение настроек авто бафа для пользователя {user_id} в чате {group_chat_id}"
        )
        self.cursor.execute(
            """
            SELECT token, role, chat_id, group_chat_id, buff_list FROM auto_buff WHERE user_id = ? AND group_chat_id = ?
        """,
            (user_id, group_chat_id),
        )
        result = self.cursor.fetchone()
        if result:
            token_encrypted, role, chat_id, group_chat_id, buff_list = result
            token = decrypt(token_encrypted)
            return {
                "token": token,
                "role": role,
                "group_chat_id": group_chat_id,
                "chat_id": chat_id,
                "buff_list": buff_list,
            }
        return None

    def remove_auto_buff_by_group_chat_id(self, user_id, group_chat_id):
        logger.debug(
            f"Удаление авто бафа для пользователя {user_id} в чате {group_chat_id}"
        )
        self.cursor.execute(
            """
            DELETE FROM auto_buff WHERE user_id = ? AND group_chat_id = ?
        """,
            (user_id, group_chat_id),
        )
        self.connection.commit()

    def get_all_auto_buffs(self, user_id):
        logger.debug(f"Получение всех настроек авто бафа для пользователя {user_id}")
        self.cursor.execute(
            """
            SELECT group_chat_id, chat_id, token, role, buff_list FROM auto_buff WHERE user_id = ?
        """,
            (user_id,),
        )
        results = self.cursor.fetchall()
        auto_buffs = []
        for row in results:
            group_chat_id, chat_id, token_encrypted, role, buff_list = row
            token = decrypt(token_encrypted)
            auto_buffs.append(
                {
                    "token": token,
                    "role": role,
                    "chat_id": chat_id,
                    "buff_list": buff_list,
                    "group_chat_id": group_chat_id,
                }
            )
        return auto_buffs

    def update_profile(
        self, user_id, strength, agility, endurance, level, attack, defense, luck
    ):
        logger.debug(f"Обновление профиля пользователя {user_id}")
        last_updated = datetime.now()
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO profiles (user_id, strength, agility, endurance, level, attack, defense, luck, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                strength,
                agility,
                endurance,
                level,
                attack,
                defense,
                luck,
                last_updated,
            ),
        )
        self.connection.commit()

    def get_profile(self, user_id):
        logger.debug(f"Получение профиля пользователя {user_id}")
        self.cursor.execute(
            """
            SELECT strength, agility, endurance, level, attack, defense, luck, last_updated
            FROM profiles WHERE user_id = ?
        """,
            (user_id,),
        )
        result = self.cursor.fetchone()
        if result:
            strength, agility, endurance, level, attack, defense, luck, last_updated = (
                result
            )
            return {
                "strength": strength,
                "agility": agility,
                "endurance": endurance,
                "level": level,
                "attack": attack,
                "defense": defense,
                "luck": luck,
                "last_updated": last_updated,
            }
        return None

    def get_users_by_role_in_chat(self, role, group_chat_id):
        self.cursor.execute(
            """
            SELECT user_id, buff_list, chat_id FROM auto_buff WHERE role = ? AND group_chat_id = ?
        """,
            (role, group_chat_id),
        )
        results = self.cursor.fetchall()
        users = []
        for row in results:
            user_id, buff_list, chat_id = row
            users.append(
                {"user_id": user_id, "buff_list": buff_list, "chat_id": chat_id}
            )
        return users
    
    
    def is_admin(self, user_id):
        self.cursor.execute("""
            SELECT role_name FROM users WHERE user_id = ?""", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0] == "admin":
            return True
        return False
    

    def close(self):
        # Закрытие соединения с базой данных
        self.connection.close()
        logger.debug("Соединение с базой данных закрыто.")
        
        

    def set_user_role(self, user_id, role_name):
        """
        Устанавливает роль для пользователя в базе данных.
        :param user_id: ID пользователя.
        :param role_name: Название роли.
        """
        self.cursor.execute(
            """
            UPDATE users
            SET role_name = ?
            WHERE user_id = ?
        """,
            (role_name, user_id),
        )
        self.connection.commit()
        logger.debug(f"Установлена роль '{role_name}' для пользователя {user_id}")
