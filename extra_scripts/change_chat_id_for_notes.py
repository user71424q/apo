import sqlite3
import os

def update_chat_numbers(db_path: str, old_chat_number: int, new_chat_number: int):
    """
    Обновляет номер чата для всех заметок с указанным старым номером чата на новый номер чата.

    :param db_path: Путь к базе данных SQLite.
    :param old_chat_number: Старый номер чата (без префикса 2000000000).
    :param new_chat_number: Новый номер чата (без префикса 2000000000).
    """
    # Вычисление peer_id для указанных чатов
    old_peer_id = old_chat_number + 2000000000
    new_peer_id = new_chat_number + 2000000000

    # Проверка существования базы данных
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена.")
        return

    # Подключение к базе данных
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Выполнение SQL-запроса для обновления peer_id
        cursor.execute("UPDATE notes SET peer_id = ? WHERE peer_id = ?", (new_peer_id, old_peer_id))
        updated_rows = cursor.rowcount

        # Фиксация изменений
        conn.commit()
        print(f"Обновлено {updated_rows} заметок: peer_id {old_peer_id} заменён на {new_peer_id}.")

    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Путь к базе данных SQLite
    db_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'notes.db')

    # Старый и новый номера чатов
    old_chat_number = 2  # Номер чата, который нужно заменить
    new_chat_number = 8  # Новый номер чата

    # Обновление номеров чатов
    update_chat_numbers(db_file_path, old_chat_number, new_chat_number)
