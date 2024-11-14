# test_profiles.py

import asyncio
from services.user_manager import UserManager
from modules.profiles import ProfileManager

async def test_profile_manager():
    user_manager = UserManager()
    profile_manager = ProfileManager(user_manager=user_manager)

    user_id = 620722769  # Пример user_id
    peer_id = 2000000001  # Пример peer_id

    # Создание/обновление профиля
    message_create = {
        'text': (
            "👑[id620722769|Михаил], Ваш профиль:\n"
            "👤Класс: апостол (66), гоблин-гном\n"
            "👥Гильдия: Сердце Дракона⭐\n"
            "😇Очень положительная карма\n"
            "💀Уровень: 669\n"
            "🎉Достижений: 71\n"
            "👊1950 🖐1693 ❤2040 🍀124 🗡1190 🛡710"
        ),
        'from_id': None,  # Теперь не используется
        'peer_id': peer_id
    }
    response = await profile_manager.check_profile_events(message_create)
    print(f"Ответ на создание/обновление профиля:\n{response}\n")

    # Обновление профиля с изменениями
    message_update = {
        'text': (
            "👑[id620722769|Михаил], Ваш профиль:\n"
            "👤Класс: апостол (66), гоблин-гном\n"
            "👥Гильдия: Сердце Дракона⭐\n"
            "😇Очень положительная карма\n"
            "💀Уровень: 670\n"  # Уровень изменился
            "🎉Достижений: 72\n"  # Достижения изменились
            "👊2000 🖐1700 ❤2050 🍀130 🗡1200 🛡720"  # Атака, защита, удача изменились
        ),
        'from_id': None,  # Теперь не используется
        'peer_id': peer_id
    }
    response = await profile_manager.check_profile_events(message_update)
    print(f"Ответ на обновление профиля:\n{response}\n")

    # Дополнительное обновление профиля с уменьшением характеристик
    message_decrease = {
        'text': (
            "👑[id620722769|Михаил], Ваш профиль:\n"
            "👤Класс: апостол (66), гоблин-гном\n"
            "👥Гильдия: Сердце Дракона⭐\n"
            "😇Очень положительная карма\n"
            "💀Уровень: 669\n"  # Уровень уменьшился
            "🎉Достижений: 70\n"  # Достижения уменьшились
            "👊1900 🖐1600 ❤2030 🍀120 🗡1150 🛡700"  # Атака, защита, удача уменьшились
        ),
        'from_id': None,  # Теперь не используется
        'peer_id': peer_id
    }
    response = await profile_manager.check_profile_events(message_decrease)
    print(f"Ответ на уменьшение профиля:\n{response}\n")

    # Тестирование не профильного сообщения
    message_non_profile = {
        'text': "Привет! Как дела?",
        'from_id': None,
        'peer_id': peer_id
    }
    response = await profile_manager.check_profile_events(message_non_profile)
    print(f"Ответ на не профильное сообщение:\n{response}\n")  # Должно быть None

if __name__ == "__main__":
    asyncio.run(test_profile_manager())
