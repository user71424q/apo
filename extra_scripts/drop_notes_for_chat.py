import sqlite3
import os

def delete_notes_for_chat(db_path: str, chat_number: int):
    """
    Удаление всех заметок для указанного чата.

    :param db_path: Путь к базе данных SQLite.
    :param chat_number: Номер чата (без префикса 2000000000).
    """
    # Вычисление peer_id для указанного чата
    peer_id = chat_number + 2000000000

    # Проверка существования базы данных
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена.")
        return

    # Подключение к базе данных
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Выполнение SQL-запроса для удаления заметок
        cursor.execute("DELETE FROM notes WHERE peer_id = ?", (peer_id,))
        deleted_rows = cursor.rowcount

        # Фиксация изменений
        conn.commit()
        print(f"Удалено {deleted_rows} заметок для чата {chat_number} (peer_id {peer_id}).")

    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Путь к базе данных SQLite
    db_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'notes.db')

    # Номер чата, для которого нужно удалить заметки
    chat_number = 8  # Измените на нужный номер чата

    # Удаление заметок
    delete_notes_for_chat(db_file_path, chat_number)
