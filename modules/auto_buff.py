import asyncio
import time
from utils.logger import logger
from services.user_manager import UserManager
from services.chat_manager import ChatManager
import vk_api
from vk_api.utils import get_random_id

BUFF_PEER_ID = -183040898

# Маппинг букв бафов в полные названия для апо
APO_BUFFS_MAPPING = {
    "а": "благословение атаки",
    "з": "благословение защиты",
    "у": "благословение удачи",
    "э": "благословение эльфа",
    "г": "благословение гоблина",
    "д": "благословение демона",
    "м": "благословение гнома",
    "н": "благословение нежити",
    "ч": "благословение человека",
    "о": "благословение орка",
}

# Маппинг команд бафов для деб
DEB_BUFFS_MAPPING = {
    "/неудачи": "проклятие неудачи",
    "/добычи": "проклятие добычи",
    "/боли": "проклятие боли",
}

# Маппинг команд бафов для вопла
VOPL_BUFFS_MAPPING = {
    "/свет": "очищение светом",
    "/очищение": "очищение",
    "/воскрешение": "воскрешение",
}


class AutoBuffManager:
    def __init__(self, user_manager: UserManager, chat_manager: ChatManager):
        self.user_manager = user_manager
        self.chat_manager = chat_manager
        self.cooldowns = {}  # Структура: {user_id: timestamp}
        self.active_tasks = []

    def is_on_cooldown(self, user_id, role):
        current_time = time.time()
        cooldown_period = self.get_cooldown_period(role)
        last_used = self.cooldowns.get(user_id, 0)
        on_cd = (current_time - last_used) < cooldown_period
        logger.debug(
            f"Проверка кулдауна для пользователя {user_id} с ролью '{role}': {'на кулдауне' if on_cd else 'готов'}"
        )
        return on_cd

    def get_cooldown_period(self, role):
        if role == "апо":
            return 60
        elif role == "деб":
            return 3600
        elif role == "вопла":
            return 60 * 15
        else:
            return 0

    async def process_message(self, chat_id, conversation_message_id, text):
        if text.lower().startswith("баф "):
            await self.handle_apo_buff_request(chat_id, conversation_message_id, text)
        elif text.lower() in DEB_BUFFS_MAPPING:
            await self.handle_deb_buff_request(
                chat_id, conversation_message_id, text.lower()
            )
        elif text.lower() in VOPL_BUFFS_MAPPING:
            await self.handle_vopl_buff_request(
                chat_id, conversation_message_id, text.lower()
            )

    async def handle_apo_buff_request(
        self, chat_id: int, conversation_message_id: int, text: str
    ):
        requested_buffs = text[4:].lower()
        if len(requested_buffs) > 4:
            return
        for priority_buff in ("а", "з", "у"):
            if priority_buff in requested_buffs:
                requested_buffs = (
                    requested_buffs.replace(priority_buff, "", 1) + priority_buff
                )

        apo_users = self.user_manager.get_users_by_role_in_chat("апо", chat_id)
        if not apo_users:
            logger.debug(f"В чате {chat_id} нет пользователей с ролью 'апо'.")
            return

        remaining_buffs = ""
        for buff in requested_buffs:
            assigned = False
            for user in apo_users:
                if buff not in user["buff_list"]:
                    continue
                if not self.is_on_cooldown(user["user_id"], "апо"):
                    await self.send_buff(
                        user["user_id"],
                        chat_id,
                        APO_BUFFS_MAPPING[buff],
                        "апо",
                        conversation_message_id,
                    )
                    assigned = True
                    break
                else:
                    assigned = "on_cooldown"

            if assigned == "on_cooldown":
                remaining_buffs += buff
            elif not assigned:
                logger.debug(
                    f"Баф '{buff}' не может быть выдан — нет апо с таким бафом."
                )

        if remaining_buffs:
            await self.schedule_delayed_buff_request(
                chat_id, conversation_message_id, remaining_buffs, apo_users
            )

    async def handle_deb_buff_request(
        self, chat_id: int, conversation_message_id: int, text: str
    ):
        buff_name = DEB_BUFFS_MAPPING.get(text)
        if not buff_name:
            logger.debug(f"Некорректный запрос деба: {text}")
            return

        deb_users = self.user_manager.get_users_by_role_in_chat("деб", chat_id)
        if not deb_users:
            logger.debug(f"В чате {chat_id} нет пользователей с ролью 'деб'.")
            return

        assigned = False
        for user in deb_users:
            if not self.is_on_cooldown(user["user_id"], "деб"):
                await self.send_buff(
                    user["user_id"], chat_id, buff_name, "деб", conversation_message_id
                )
                assigned = True
                break

        if not assigned:
            await self.schedule_delayed_deb_request(
                chat_id, conversation_message_id, text, deb_users
            )

    async def handle_vopl_buff_request(
        self, chat_id: int, conversation_message_id: int, text: str
    ):
        buff_name = VOPL_BUFFS_MAPPING.get(text)
        if not buff_name:
            logger.debug(f"Некорректный запрос вопла: {text}")
            return

        vopl_users = self.user_manager.get_users_by_role_in_chat("вопла", chat_id)
        if not vopl_users:
            logger.debug(f"В чате {chat_id} нет пользователей с ролью 'вопла'.")
            return

        assigned = False
        for user in vopl_users:
            if not self.is_on_cooldown(user["user_id"], "вопла"):
                await self.send_buff(
                    user["user_id"],
                    chat_id,
                    buff_name,
                    "вопла",
                    conversation_message_id,
                )
                assigned = True
                break

        if not assigned:
            await self.schedule_delayed_vopl_request(
                chat_id, conversation_message_id, text, vopl_users
            )

    async def schedule_delayed_buff_request(
        self,
        chat_id: int,
        conversation_message_id: int,
        remaining_buffs: str,
        apo_users: list,
    ):
        min_cooldown = self._calculate_min_cooldown("апо", remaining_buffs, apo_users)
        if min_cooldown < float("inf"):
            logger.debug(
                f"Назначение отложенного вызова для бафов '{remaining_buffs}' через {min_cooldown} секунд."
            )
            task = asyncio.create_task(
                self._delayed_buff_handler(
                    chat_id,
                    conversation_message_id,
                    "баф " + remaining_buffs,
                    min_cooldown,
                    "апо",
                ),
                name=f"buff_{chat_id}_{conversation_message_id}",
            )
            self.active_tasks.append(task)
            task.add_done_callback(
                lambda t: (
                    self.active_tasks.remove(t) if t in self.active_tasks else None
                )
            )

    async def schedule_delayed_deb_request(
        self,
        chat_id: int,
        conversation_message_id: int,
        buff_name: str,
        deb_users: list,
    ):
        min_cooldown = self._calculate_min_cooldown("деб", buff_name, deb_users)
        if min_cooldown < float("inf"):
            logger.debug(
                f"Назначение отложенного вызова для бафа '{buff_name}' через {min_cooldown} секунд."
            )
            asyncio.create_task(
                self._delayed_buff_handler(
                    chat_id, conversation_message_id, buff_name, min_cooldown, "деб"
                )
            )

    async def schedule_delayed_vopl_request(
        self,
        chat_id: int,
        conversation_message_id: int,
        buff_name: str,
        vopl_users: list,
    ):
        min_cooldown = self._calculate_min_cooldown("вопла", buff_name, vopl_users)
        if min_cooldown < float("inf"):
            logger.debug(
                f"Назначение отложенного вызова для бафа '{buff_name}' через {min_cooldown} секунд."
            )
            asyncio.create_task(
                self._delayed_buff_handler(
                    chat_id, conversation_message_id, buff_name, min_cooldown, "вопла"
                )
            )

    async def _delayed_buff_handler(
        self,
        chat_id: int,
        conversation_message_id: int,
        remaining_buffs: str,
        delay: float,
        role: str,
    ):
        logger.debug(
            f"Отложенный вызов для бафов '{remaining_buffs}' активирован. Ожидание {delay} секунд."
        )
        await asyncio.wait_for(asyncio.sleep(delay), timeout=delay + 1)

        logger.debug(
            f"Отложенный вызов для бафов '{remaining_buffs}' завершен. Повторная попытка."
        )
        if role == "апо":
            await self.handle_apo_buff_request(
                chat_id, conversation_message_id, remaining_buffs
            )
        elif role == "деб":
            await self.handle_deb_buff_request(
                chat_id, conversation_message_id, remaining_buffs
            )
        elif role == "вопла":
            await self.handle_vopl_buff_request(
                chat_id, conversation_message_id, remaining_buffs
            )

    def _calculate_min_cooldown(self, role: str, buffs: str, users: list):
        min_cooldown = float("inf")
        for buff in buffs:
            for user in users:
                if role == "апо" and buff not in user["buff_list"]:
                    continue
                cooldown = self.get_cooldown_period(role) - (
                    time.time() - self.cooldowns.get(user["user_id"], 0)
                )
                if 0 < cooldown < min_cooldown:
                    min_cooldown = cooldown
        return min_cooldown

    async def send_buff(
        self, user_id, group_chat_id, buff_name, role, conversation_message_id
    ):
        auto_buffs = self.user_manager.get_all_auto_buffs(user_id)
        target_auto_buff = None

        for auto_buff in auto_buffs:
            if auto_buff["group_chat_id"] == group_chat_id:
                target_auto_buff = auto_buff
                break

        if not target_auto_buff:
            logger.error(f"Авто баф для пользователя {user_id} не найден.")
            return

        token = target_auto_buff["token"]
        user_chat_id = target_auto_buff["chat_id"]

        try:
            vk_session = vk_api.VkApi(token=token)
            vk = vk_session.get_api()
            response = vk_session.method(
                "messages.getByConversationMessageId",
                {
                    "peer_id": user_chat_id,
                    "conversation_message_ids": conversation_message_id,
                    "access_token": token,
                },
            )
            if not response["items"]:
                logger.error(
                    f"Не удалось найти сообщение по conversation_message_id: {conversation_message_id}"
                )
                return
            message_id = response["items"][0]["id"]

            vk_session.method(
                "messages.send",
                {
                    "peer_id": BUFF_PEER_ID,
                    "message": buff_name,
                    "random_id": get_random_id(),
                    "forward_messages": message_id,
                },
            )
            logger.debug(
                f"{role.upper()} {user_id} отправил баф '{buff_name}'"
            )
            self.cooldowns[user_id] = time.time()
            logger.debug(
                f"Кулдаун для пользователя {user_id} с ролью '{role}' установлен на {self.get_cooldown_period(role)} секунд."
            )
        except Exception as e:
            logger.error(
                f"Ошибка при отправке бафа от {user_id}: {e}"
            )
