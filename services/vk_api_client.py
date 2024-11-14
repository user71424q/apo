import asyncio
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from config.settings import VK_API_TOKEN, VK_GROUP_ID
from modules.auto_buff import AutoBuffManager
from modules.notes import NoteManager
from modules.profiles import ProfileManager
from modules.wishes import WishManager
from utils.logger import logger
import concurrent.futures


class VkApiClient:
    def __init__(self, dialog_manager, user_manager, chat_manager):
        self.vk_session = vk_api.VkApi(token=VK_API_TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id=VK_GROUP_ID)
        self.dialog_manager = dialog_manager
        self.user_manager = user_manager
        self.chat_manager = chat_manager
        self.executor = (
            concurrent.futures.ThreadPoolExecutor()
        )  # Инициализация пула потоков
        
        # Инициализация модулей
        self.auto_buff_manager = AutoBuffManager(self.user_manager, self.chat_manager)
        self.note_manager = NoteManager()
        self.profile_manager = ProfileManager(self.user_manager)
        self.wish_manager = WishManager()

    async def start_listening(self):
        logger.info("Запуск прослушивания событий VK")
        loop = (
            asyncio.get_running_loop()
        )  # Получаем текущий event loop в основном контексте

        # Запуск синхронного longpoll.listen() в отдельном потоке
        await loop.run_in_executor(self.executor, self._listen_and_handle_events, loop)

    def _listen_and_handle_events(self, loop):
        # Теперь передаём основной event loop и используем его
        while True:
            try:
                for event in self.longpoll.listen():
                    # Передаём event loop в run_coroutine_threadsafe
                    asyncio.run_coroutine_threadsafe(self.handle_event(event), loop)
            except Exception as e:
                logger.error(f"Ошибка при обработке событий VK: {e}")

    async def handle_event(self, event):
        if event.type == VkBotEventType.MESSAGE_NEW:
            message = event.obj.message
            peer_id = message.get("peer_id")
            from_id = message.get("from_id")

            # Обработка сообщений
            self.user_manager.add_user(user_id=from_id)
            if peer_id < 2000000000:
                await self.handle_private_message(from_id, message)
            else:
                await self.handle_chat_message(message)

    async def handle_private_message(self, user_id, message):
        text = message.get("text", "")
        #админ-команды для лс группы, НЕ являются диалогом
        if self.user_manager.is_admin(user_id):
            if text.lower().startswith("роль") and len(text.split()) == 2 and message.get("fwd_messages", []) != []:
                role = text.lower().split()[1]
                target_id = message["fwd_messages"][0]["from_id"]
                self.user_manager.set_user_role(target_id, role)
                self.send_message(
                    user_id, f"Роль пользователя {user_id} изменена на {role}"
                )
                return
        
        # Проверяем, есть ли активный диалог
        if user_id in self.dialog_manager.active_dialogs:
            response = await self.dialog_manager.update_dialog(user_id, text)
            if response:
                message = response.get("text", "")
                keyboard = response.get("keyboard")
                self.send_message(user_id, message, keyboard)
        else:
            # Если нет активного диалога, проверяем команды
            if text.lower() == "хочу встать на авто баф":
                self.dialog_manager.start_dialog(user_id, "auto_buff")
                # Инициируем диалог с пустым сообщением, чтобы получить первый ответ
                response = await self.dialog_manager.update_dialog(user_id, "")
                if response:
                    message = response.get("text", "")
                    keyboard = response.get("keyboard")
                    self.send_message(user_id, message, keyboard)
            elif text.lower() == "хочу сняться с авто бафа":
                self.dialog_manager.start_dialog(user_id, "remove_auto_buff")
                # Инициируем диалог с пустым сообщением, чтобы получить первый ответ
                response = await self.dialog_manager.update_dialog(user_id, "")
                if response:
                    message = response.get("text", "")
                    keyboard = response.get("keyboard")
                    self.send_message(user_id, message, keyboard)
            else:
                self.send_message(
                    user_id,
                    "Неизвестная команда. Напишите 'Хочу встать на авто баф' или 'хочу сняться с авто бафа' для начала.",
                )

    async def handle_chat_message(self, message):
        peer_id = message["peer_id"]
        user_id = message["from_id"]
        text = message["text"]
        conversation_id = message["conversation_message_id"]
        logger.debug(f"Сообщение в чате {peer_id} от {user_id}: {text}")
        
        #админ-команды для чатов
        if self.user_manager.is_admin(user_id):
            logger.debug(f"Админ {user_id} в чате {peer_id}: {text}")
            if text.lower() == '/модули':
                self.send_message(
                    peer_id,
                    self.chat_manager.get_chat_settings_string(peer_id),
                )
            if text.lower().startswith('/добавить модуль'):
                module_name = text.lower().split()[2]
                self.chat_manager.enable_module(peer_id, module_name)
                self.send_message(peer_id, self.chat_manager.get_chat_settings_string(peer_id))
            if text.lower().startswith('/удалить модуль'):
                module_name = text.lower().split()[2]
                self.chat_manager.disable_module(peer_id, module_name)
                self.send_message(peer_id, self.chat_manager.get_chat_settings_string(peer_id))
            if text.lower().startswith('/имя'):
                name_parts = text.split()[1:]  # Разбиваем строку и игнорируем первый элемент ('/имя')
                name = ' '.join(name_parts) if name_parts else str(peer_id)  # Если нет имени, задаем дефолтное значение
                # Обновляем или создаем настройки чата с новым именем
                current_settings = self.chat_manager.get_chat_settings(peer_id) or {}
                current_settings.update({"name": name})
                self.chat_manager.set_chat_settings(peer_id, current_settings)
                self.send_message(peer_id, self.chat_manager.get_chat_settings_string(peer_id))

        
        # работа с модулями
        modules = self.chat_manager.get_chat_settings(peer_id).get("modules", [])
        if "auto_buff" in modules:
            await self.auto_buff_manager.process_message(peer_id, conversation_id, text)
        if "notes" in modules:
            response = await self.note_manager.check_note_events(message)
            if response:
                self.send_message(peer_id, response)
        if "profiles" in modules and user_id == -183040898:
            response = await self.profile_manager.check_profile_events(message)
            if response:
                self.send_message(peer_id, response)
        if 'wishes' in modules:
            response = await self.wish_manager.check_wish_events(message)
            if response:
                self.send_message(peer_id, response)
        # Дополнительная обработка сообщений в чатах

    def send_message(self, peer_id, message, keyboard=None):
        logger.debug(f"Отправка сообщения {peer_id}: {message}")
        try:
            params = {
                "peer_id": peer_id,
                "message": message,
                "random_id": vk_api.utils.get_random_id(),
            }
            if keyboard:
                params["keyboard"] = keyboard
            self.vk.messages.send(**params)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            
