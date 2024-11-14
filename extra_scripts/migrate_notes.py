import asyncio
import json
import os
import sys
from typing import Optional
from modules.notes import NoteManager

async def migrate_notes(json_path: str, db_path: str):
    """
    Миграция заметок из JSON в SQLite базу данных.

    :param json_path: Путь к файлу notes.json.
    :param db_path: Путь к новой базе данных SQLite.
    """
    # Проверка существования файла JSON
    if not os.path.exists(json_path):
        print(f"Файл {json_path} не найден.")
        return

    # Чтение данных из notes.json
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            all_notes = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON: {e}")
        return
    except Exception as e:
        print(f"Ошибка чтения файла {json_path}: {e}")
        return

    # Инициализация NoteManager
    note_manager = NoteManager(db_path=db_path)
    # self.lock is already initialized, _create_table was called in __init__

    # Счётчики для отчёта
    total_notes = 0
    added_notes = 0
    updated_notes = 0
    skipped_notes = 0

    # Проход по всем чатам и заметкам
    for peer_id_str, notes in all_notes.items():
        try:
            peer_id = int(peer_id_str) + 2000000000
        except ValueError:
            print(f"Некорректный peer_id: {peer_id_str}. Пропуск.")
            skipped_notes += len(notes) if isinstance(notes, list) else 1
            continue

        if not isinstance(notes, list):
            print(f"Некорректный формат заметок для peer_id {peer_id}. Ожидался список. Пропуск.")
            skipped_notes += len(notes) if isinstance(notes, list) else 1
            continue

        for note in notes:
            total_notes += 1
            keyword = note.get("keyword")
            text = note.get("text")

            if not keyword or not text:
                print(f"Некорректная заметка в peer_id {peer_id}: {note}. Пропуск.")
                skipped_notes += 1
                continue

            # Добавление или обновление заметки
            updated = await note_manager.add_note(keyword, text, peer_id)
            if updated:
                updated_notes += 1
                print(f"Обновлена заметка '{keyword}' в peer_id {peer_id}.")
            else:
                added_notes += 1
                print(f"Добавлена новая заметка '{keyword}' в peer_id {peer_id}.")

    # Итоговый отчёт
    print("\nМиграция завершена.")
    print(f"Всего заметок в JSON: {total_notes}")
    print(f"Добавлено новых заметок: {added_notes}")
    print(f"Обновлено существующих заметок: {updated_notes}")
    print(f"Пропущено некорректных заметок: {skipped_notes}")

if __name__ == "__main__":
    # Путь к старой JSON-базе
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notes.json')
    
    # Путь к новой SQLite-базе
    db_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'notes.db')

    # Создание директории для базы данных, если не существует
    os.makedirs(os.path.dirname(db_file_path), exist_ok=True)

    # Запуск миграции
    asyncio.run(migrate_notes(json_file_path, db_file_path))
