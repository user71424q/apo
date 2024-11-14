import asyncio
import sqlite3
import re
from typing import Optional, Tuple, List
from utils.logger import logger

class NoteManager:
    def __init__(self, db_path: str = 'data/notes.db'):
        """
        Инициализация менеджера заметок.
        :param db_path: Путь к файлу базы данных SQLite.
        """
        self.db_path = db_path
        self.lock = asyncio.Lock()
        self._create_table()

    def _create_table(self):
        """
        Синхронное создание таблицы заметок в базе данных.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peer_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                text TEXT NOT NULL,
                UNIQUE(peer_id, keyword)
            )
        """)
        conn.commit()
        conn.close()
        logger.debug("База данных и таблица 'notes' инициализированы.")

    async def get_note_text(self, keyword: str, peer_id: int) -> Optional[str]:
        """
        Получение текста заметки по ключевому слову и peer_id.
        :param keyword: Ключевое слово заметки.
        :param peer_id: Идентификатор чата (peer_id).
        :return: Текст заметки или None, если не найдено.
        """
        async with self.lock:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._get_note_text_sync,
                keyword,
                peer_id
            )
        return result

    def _get_note_text_sync(self, keyword: str, peer_id: int) -> Optional[str]:
        """
        Синхронное получение текста заметки из базы данных.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT text FROM notes
            WHERE peer_id = ? AND LOWER(keyword) = LOWER(?)
            """,
            (peer_id, keyword)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            logger.debug(f"Заметка найдена для ключевого слова '{keyword}' и peer_id '{peer_id}'.")
            return row[0]
        logger.debug(f"Заметка не найдена для ключевого слова '{keyword}' и peer_id '{peer_id}'.")
        return None

    async def get_keywords(self, peer_id: int) -> Optional[str]:
        """
        Получение списка доступных ключевых слов для заметок.
        :param peer_id: Идентификатор чата (peer_id).
        :return: Строка со списком ключевых слов или None, если заметок нет.
        """
        async with self.lock:
            keywords = await asyncio.get_event_loop().run_in_executor(
                None,
                self._get_keywords_sync,
                peer_id
            )
        if keywords:
            formatted_keywords = "\n- " + "\n- ".join(keywords)
            return f"Доступные заметки:{formatted_keywords}"
        return None

    def _get_keywords_sync(self, peer_id: int) -> List[str]:
        """
        Синхронное получение всех ключевых слов заметок из базы данных.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT keyword FROM notes
            WHERE peer_id = ?
            """,
            (peer_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [row[0] for row in rows]
        return []

    async def add_note(self, keyword: str, text: str, peer_id: int) -> bool:
        """
        Добавление новой заметки или обновление существующей.
        :param keyword: Ключевое слово заметки.
        :param text: Текст заметки.
        :param peer_id: Идентификатор чата (peer_id).
        :return: True, если заметка была обновлена, False если создана новая.
        """
        async with self.lock:
            updated = await asyncio.get_event_loop().run_in_executor(
                None,
                self._add_note_sync,
                keyword,
                text,
                peer_id
            )
        return updated

    def _add_note_sync(self, keyword: str, text: str, peer_id: int) -> bool:
        """
        Синхронное добавление или обновление заметки в базе данных.
        :return: True, если обновлена, False если добавлена новая.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # Проверяем, существует ли уже заметка с таким ключевым словом
            cursor.execute("""
                SELECT 1 FROM notes
                WHERE peer_id = ? AND LOWER(keyword) = LOWER(?)
            """,
            (peer_id, keyword)
            )
            exists = cursor.fetchone() is not None

            # Вставляем новую заметку или обновляем существующую
            cursor.execute("""
                INSERT INTO notes (peer_id, keyword, text)
                VALUES (?, ?, ?)
                ON CONFLICT(peer_id, keyword) DO UPDATE SET text=excluded.text
            """,
            (peer_id, keyword, text)
            )
            conn.commit()
            conn.close()

            logger.debug(f"Заметка '{keyword}' для peer_id '{peer_id}' {'обновлена' if exists else 'создана'}.")
            return exists
        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении/обновлении заметки '{keyword}' для peer_id '{peer_id}': {e}")
            conn.close()
            return False

    async def delete_note(self, keyword: str, peer_id: int) -> bool:
        """
        Удаление заметки по ключевому слову.
        :param keyword: Ключевое слово заметки.
        :param peer_id: Идентификатор чата (peer_id).
        :return: True, если заметка была удалена, False иначе.
        """
        async with self.lock:
            deleted = await asyncio.get_event_loop().run_in_executor(
                None,
                self._delete_note_sync,
                keyword,
                peer_id
            )
        return deleted

    def _delete_note_sync(self, keyword: str, peer_id: int) -> bool:
        """
        Синхронное удаление заметки из базы данных.
        :return: True, если заметка была удалена, False иначе.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM notes
                WHERE peer_id = ? AND LOWER(keyword) = LOWER(?)
            """,
            (peer_id, keyword)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            if deleted:
                logger.debug(f"Заметка '{keyword}' удалена для peer_id '{peer_id}'.")
            else:
                logger.debug(f"Заметка '{keyword}' не найдена для peer_id '{peer_id}'.")
            return deleted
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении заметки '{keyword}' для peer_id '{peer_id}': {e}")
            conn.close()
            return False

    async def delete_all_notes(self, peer_id: int) -> None:
        """
        Удаление всех заметок для заданного чата.
        :param peer_id: Идентификатор чата (peer_id).
        """
        async with self.lock:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._delete_all_notes_sync,
                peer_id
            )

    def _delete_all_notes_sync(self, peer_id: int) -> None:
        """
        Синхронное удаление всех заметок из базы данных для заданного peer_id.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM notes
                WHERE peer_id = ?
            """,
            (peer_id,)
            )
            conn.commit()
            conn.close()
            logger.debug(f"Все заметки удалены для peer_id '{peer_id}'.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении всех заметок для peer_id '{peer_id}': {e}")
            conn.close()

    async def import_notes(self, from_cid: int, to_pid: int) -> None:
        """
        Импорт заметок из одного чата в другой.
        :param from_cid: Идентификатор исходного чата.
        :param to_pid: Идентификатор целевого чата.
        """
        async with self.lock:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._import_notes_sync,
                from_cid,
                to_pid
            )

    def _import_notes_sync(self, from_cid: int, to_pid: int) -> None:
        """
        Синхронное копирование заметок из одного чата в другой.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT keyword, text FROM notes
                WHERE peer_id = ?
            """,
            (from_cid,)
            )
            rows = cursor.fetchall()
            for row in rows:
                keyword, text = row
                cursor.execute("""
                    INSERT INTO notes (peer_id, keyword, text)
                    VALUES (?, ?, ?)
                    ON CONFLICT(peer_id, keyword) DO UPDATE SET text=excluded.text
                """,
                (to_pid, keyword, text)
                )
            conn.commit()
            conn.close()
            logger.debug(f"Заметки импортированы из peer_id '{from_cid}' в peer_id '{to_pid}'.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при импорте заметок из peer_id '{from_cid}' в peer_id '{to_pid}': {e}")
            conn.close()

    def parse_note(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Парсинг команды создания заметки.
        Поддерживает:
        - Новая заметка "Название" Текст
        - Новая заметка Название Текст (где название - первая часть до пробела или перевода строки)
        :param text: Текст команды после префикса.
        :return: Кортеж (keyword, text) или (None, None) если парсинг не удался.
        """
        keyword = None
        note_text = None
        # Попытка парсинга с кавычками
        match = re.match(r'^"([^"]+)"\s+(.*)$', text)
        if match:
            keyword, note_text = match.groups()
            logger.debug(f"Парсинг заметки с кавычками: keyword='{keyword}', text='{note_text}'")
            return keyword.strip(), note_text.strip()

        # Парсинг с переводом строки
        parts = text.strip().split('\n', 1)
        if len(parts) == 2:
            keyword = parts[0].strip()
            note_text = parts[1].strip()
            logger.debug(f"Парсинг заметки с переводом строки: keyword='{keyword}', text='{note_text}'")
            return keyword, note_text

        # Парсинг с пробелом
        parts = text.strip().split(' ', 1)
        if len(parts) == 2:
            keyword = parts[0].strip()
            note_text = parts[1].strip()
            logger.debug(f"Парсинг заметки с пробелом: keyword='{keyword}', text='{note_text}'")
            return keyword, note_text

        logger.debug("Не удалось распарсить заметку.")
        return None, None

    async def check_note_events(self, message) -> Optional[str]:
        """
        Обработка событий сообщений для работы с заметками.
        :param message: Словарь сообщения.
        :return: Ответное сообщение или None.
        """
        text = message.get('text', '').strip()
        peer_id = message.get('peer_id', 0)
        logger.debug(f"Получено сообщение в модуле 'notes': text='{text}', peer_id='{peer_id}'")
        
        if not text or not peer_id:
            logger.debug("Пустое сообщение или отсутствует peer_id. Пропуск.")
            return None

        lower_text = text.lower()

        if lower_text.startswith("заметка "):
            keyword = text[7:].strip()
            logger.debug(f"Обработка команды 'заметка': keyword='{keyword}'")
            note_text = await self.get_note_text(keyword, peer_id)
            if note_text is None:
                note_text = "Такой заметки не нашлось :("
            return note_text

        elif lower_text.startswith("!заметка "):
            keyword = text[8:].strip()
            logger.debug(f"Обработка команды '!заметка': keyword='{keyword}'")
            note_text = await self.get_note_text(keyword, peer_id)
            if note_text is None:
                note_text = "Такой заметки не нашлось :("
            return note_text

        elif lower_text.startswith("заметки") or lower_text.startswith("!заметки") or lower_text.startswith("/заметки"):
            logger.debug("Обработка команды просмотра всех заметок.")
            keywords = await self.get_keywords(peer_id)
            if keywords is None:
                keywords = (
                    "Вы еще не создали ни одной заметки. Чтобы создать заметку, напишите:\n\n"
                    "Новая заметка \"Название\"\nТекст заметки"
                )
            return keywords

        elif lower_text.startswith("!новая заметка ") or lower_text.startswith("новая заметка "):
            # Извлечение текста после команды
            if lower_text.startswith("!новая заметка "):
                command_length = len("!новая заметка ")
            else:
                command_length = len("новая заметка ")
            note_command_text = text[command_length:].strip()
            logger.debug(f"Обработка команды создания/обновления заметки: '{note_command_text}'")
            keyword, note_text = self.parse_note(note_command_text)
            if keyword and note_text:
                updated = await self.add_note(keyword, note_text, peer_id)
                response = f"Заметка {'обновлена' if updated else 'создана'}"
                logger.debug(f"Заметка '{keyword}' {'обновлена' if updated else 'создана'} для peer_id '{peer_id}'.")
                return response
            else:
                logger.debug("Некорректный формат команды создания заметки.")
                return (
                    "Необходимо указать название и текст новой заметки. Пример:\n"
                    "Новая заметка \"Правила\" Текст правил"
                )

        elif (lower_text.startswith("!удалить ") or lower_text.startswith("/удалить ")) and "модуль" not in lower_text:
            # Извлечение названия заметки для удаления
            delete_command_text = text[9:].strip()
            if not delete_command_text:
                logger.debug("Необходимо указать название заметки для удаления.")
                return "Необходимо указать название заметки для удаления."
            keyword = delete_command_text
            logger.debug(f"Обработка команды удаления заметки: keyword='{keyword}'")
            deleted = await self.delete_note(keyword, peer_id)
            if deleted:
                response = f"Заметка '{keyword}' удалена."
                logger.debug(f"Заметка '{keyword}' успешно удалена для peer_id '{peer_id}'.")
            else:
                response = f"Заметка '{keyword}' не найдена."
                logger.debug(f"Заметка '{keyword}' не найдена для peer_id '{peer_id}'.")
            return response

        elif lower_text == "/команды заметки":
            logger.debug("Обработка команды '/команды заметки'.")
            commands = (
                "• Создание или обновление заметок:\n"
                "Новая заметка \"Правила\" Текст\n<или>\n"
                "Новая заметка Правила гильдии\nТекст с новой строки\n\n"
                "• Удаление заметок:\n!удалить Правила гильдии\n\n"
                "• Просмотр всех заметок:\n!заметки\n\n"
                "• Просмотр одной заметки:\nЗаметка экспедиции\n<или>\n!экспедиции"
            )
            return commands

        # АДМИНСКИЕ КОМАНДЫ ДЛЯ МОДУЛЯ ЗАМЕТОК ВРЕМЕННО НЕ РАБОТАЮТ
        # elif from_id == admin_id:
        #     if lower_text == "/удалить все заметки":
        #         await self.delete_all_notes(peer_id)
        #         return "Все заметки в этом чате были удалены"

        #     elif lower_text.startswith("/импорт заметок "):
        #         ids = text[15:].split()
        #         imported_ids = []
        #         for num in ids:
        #             if num.isdigit():
        #                 from_cid = int(num)
        #                 await self.import_notes(from_cid, peer_id)
        #                 imported_ids.append(num)
        #         if imported_ids:
        #             return "Заметки импортированы"
        #         else:
        #             return "Не указаны корректные peer_id для импорта."

        elif text.startswith("!") or text.startswith("/"):
            keyword = text[1:].strip()
            if keyword:
                logger.debug(f"Обработка команды поиска заметки по ключевому слову '{keyword}'.")
                note_text = await self.get_note_text(keyword, peer_id)
                if note_text is not None:
                    return note_text
            logger.debug("Нет заметки для заданного ключевого слова.")
            return None

        return None
