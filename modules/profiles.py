# modules/profiles.py

import re
from typing import Optional, Dict, Any
from datetime import datetime
from utils.logger import logger


class ProfileManager:
    # Сопоставление характеристик с эмодзи
    STAT_EMOJI = {
        "level": "💀",      
        "strength": "👊",   
        "agility": "🖐",     
        "endurance": "❤",   
        "attack": "🗡",       
        "defense": "🛡",    
        "luck": "🍀",     
    }

    def __init__(self, user_manager):
        """
        Инициализация менеджера профилей.
        :param user_manager: Экземпляр UserManager для работы с профилями.
        """
        self.user_manager = user_manager
        logger.debug("Инициализация ProfileManager")

    async def check_profile_events(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Обработка сообщений с профилями игроков.
        :param message: Словарь сообщения.
        :return: Ответное сообщение или None.
        """
        text = message.get('text', '').strip()
        peer_id = message.get('peer_id', 0)
        logger.debug(f"Получено сообщение для профиля: peer_id={peer_id}")

        if not text:
            logger.debug("Пустое сообщение. Пропуск.")
            return None

        # Извлечение user_id из текста сообщения
        user_id_match = re.search(r'\[id(\d+)\|', text)
        if user_id_match:
            user_id = int(user_id_match.group(1))
        else:
            return None  # Возвращаем None вместо сообщения об ошибке

        # Регулярные выражения для извлечения полей
        level_pattern = re.compile(r'💀Уровень:\s*(\d+)')
        strength_pattern = re.compile(r'👊(\d+)')
        agility_pattern = re.compile(r'🖐(\d+)')
        endurance_pattern = re.compile(r'❤(\d+)')
        attack_pattern = re.compile(r'🗡(\d+)')
        defense_pattern = re.compile(r'🛡(\d+)')
        luck_pattern = re.compile(r'🍀(\d+)')

        # Извлечение уровня
        level_match = level_pattern.search(text)
        if level_match:
            level = int(level_match.group(1))
        else:
            return None  # Возвращаем None вместо сообщения об ошибке

        # Извлечение силы
        strength_match = strength_pattern.search(text)
        if strength_match:
            strength = int(strength_match.group(1))
        else:
            return None  # Возвращаем None вместо сообщения об ошибке

        # Извлечение ловкости
        agility_match = agility_pattern.search(text)
        if agility_match:
            agility = int(agility_match.group(1))
        else:
            return None  # Возвращаем None вместо сообщения об ошибке

        # Извлечение выносливости
        endurance_match = endurance_pattern.search(text)
        if endurance_match:
            endurance = int(endurance_match.group(1))
        else:
            return None  # Возвращаем None вместо сообщения об ошибке

        # Извлечение атаки
        attack_match = attack_pattern.search(text)
        if attack_match:
            attack = int(attack_match.group(1))
        else:
            return None  # Возвращаем None вместо сообщения об ошибке

        # Извлечение защиты
        defense_match = defense_pattern.search(text)
        if defense_match:
            defense = int(defense_match.group(1))
        else:
            return None  # Возвращаем None вместо сообщения об ошибке

        # Извлечение удачи
        luck_match = luck_pattern.search(text)
        if luck_match:
            luck = int(luck_match.group(1))
        else:
            return None  # Возвращаем None вместо сообщения об ошибке

        # Получение существующего профиля
        existing_profile = self.user_manager.get_profile(user_id)

        # Сравнение и сбор изменений
        changes = {}
        last_updated_str = "новый профиль"
        if existing_profile:
            changes['strength'] = strength - existing_profile.get('strength', 0)
            changes['agility'] = agility - existing_profile.get('agility', 0)
            changes['endurance'] = endurance - existing_profile.get('endurance', 0)
            changes['level'] = level - existing_profile.get('level', 0)
            changes['attack'] = attack - existing_profile.get('attack', 0)
            changes['defense'] = defense - existing_profile.get('defense', 0)
            changes['luck'] = luck - existing_profile.get('luck', 0)
            last_updated_str = existing_profile.get("last_updated", "новый профиль")
            logger.debug(f"Изменения профиля пользователя {user_id}: {changes}")
        else:
            # Если профиль не существует, считаем все изменения равными текущим значениям
            changes = {
                'strength': strength,
                'agility': agility,
                'endurance': endurance,
                'level': level,
                'attack': attack,
                'defense': defense,
                'luck': luck,
            }
            logger.debug(f"Создан новый профиль для пользователя {user_id} с данными: {changes}")
        
        try:
            # Преобразование строки даты в объект datetime
            last_updated_dt = datetime.strptime(last_updated_str, '%Y-%m-%d %H:%M:%S')
            # Форматирование даты в желаемый формат
            formatted_date = last_updated_dt.strftime('%d.%m %H:%M:%S')
        except (ValueError, TypeError):
            formatted_date = last_updated_str  # Если формат неизвестен, оставить как есть

        # Обновление профиля
        self.user_manager.update_profile(
            user_id,
            strength,
            agility,
            endurance,
            level,
            attack,
            defense,
            luck
        )

        # Получение обновлённого профиля
        updated_profile = self.user_manager.get_profile(user_id)
        

        # Формирование ответа
        response_lines = [f"Дата последнего обновления: {formatted_date}"]
        stat_line = ""
        for stat, emoji in self.STAT_EMOJI.items():
            if stat in changes:
                current_value = updated_profile.get(stat, 0)
                change = changes[stat]
                if change > 0:
                    change_str = f"(+{change})"
                elif change < 0:
                    change_str = f"({change})"
                else:
                    change_str = "(0)"
                stat_line += f" {emoji}{current_value}{change_str}"
        response_lines.append(stat_line.strip())

        response = "\n".join(response_lines)
        logger.debug(f"Ответ для пользователя {user_id}: {response}")
        return response
