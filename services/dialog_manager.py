from utils.logger import logger
from utils.keyboard import create_keyboard
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import asyncio
from config.settings import VK_API_TOKEN


class DialogManager:
    def __init__(self, chat_manager, user_manager):
        logger.debug("Инициализация DialogManager")
        self.active_dialogs = {}
        self.chat_manager = chat_manager
        self.user_manager = user_manager  # Добавлено для сохранения данных в БД

    def start_dialog(self, user_id, dialog_type):
        logger.debug(f"Начало диалога {dialog_type} с пользователем {user_id}")
        self.active_dialogs[user_id] = {
            "type": dialog_type,
            "state": "start",
            "data": {},
        }

    async def update_dialog(self, user_id, message):
        logger.debug(
            f"Обновление диалога для пользователя {user_id} с сообщением: {message}"
        )
        dialog = self.active_dialogs.get(user_id)
        if not dialog:
            logger.warning(f"Нет активного диалога для пользователя {user_id}")
            return None

        if dialog["type"] == "auto_buff":
            return await self._handle_auto_buff_dialog(user_id, dialog, message)
        elif dialog["type"] == "remove_auto_buff":
            return await self._handle_remove_auto_buff_dialog(user_id, dialog, message)
        else:
            logger.warning(
                f"Неизвестный тип диалога {dialog['type']} для пользователя {user_id}"
            )
            return None

    async def _handle_auto_buff_dialog(self, user_id, dialog, message):
        state = dialog["state"]
        logger.debug(f"Состояние диалога авто бафа: {state}")

        if state == "start":
            # Спрашиваем роль с кнопками
            dialog["state"] = "ask_role"
            self.active_dialogs[user_id] = dialog

            buttons = [["апо", "деб", "вопла"]]
            keyboard = create_keyboard(buttons, one_time=True)

            return {"text": "Выберите вашу роль:", "keyboard": keyboard}

        elif state == "ask_role":
            # Валидация выбора роли
            role = message.lower()
            if role in ["апо", "деб", "вопла"]:
                dialog["data"]["role"] = role
                if role == "апо":
                    dialog["state"] = "ask_buffs"
                    self.active_dialogs[user_id] = dialog
                    return {
                        "text": "Введите бафы, которые будете раздавать (буквы из 'азуэгдмнчо', до 6 букв):",
                        "keyboard": None,
                    }
                else:
                    dialog["state"] = "ask_token"
                    self.active_dialogs[user_id] = dialog
                    return {
                        "text": "Пришлите токен для доступа к отправке сообщений от вашего имени. Если вы не знаете как получить токен, можете посмотреть инструкцию по ссылке: https://disk.yandex.ru/i/6QkEUDqi10xZvw",
                        "keyboard": None,
                    }
            else:
                logger.debug(f"Неверная роль '{message}' от пользователя {user_id}")
                buttons = [["апо", "деб", "вопла"]]
                keyboard = create_keyboard(buttons, one_time=True)
                return {
                    "text": "Пожалуйста, выберите роль, используя кнопки ниже.",
                    "keyboard": keyboard,
                }

        elif state == "ask_buffs":
            # Валидация введенного списка бафов
            valid_letters = set("азуэгдмнчо")
            buff_list = message.lower()
            if 1 <= len(buff_list) <= 6 and all(c in valid_letters for c in buff_list):
                dialog["data"]["buff_list"] = buff_list
                dialog["state"] = "ask_token"
                self.active_dialogs[user_id] = dialog
                return {
                    "text": "Пришлите токен для доступа к отправке сообщений от вашего имени. Если вы не знаете как получить токен, можете посмотреть инструкцию по ссылке: https://disk.yandex.ru/i/6QkEUDqi10xZvw",
                    "keyboard": None,
                }
            else:
                return {
                    "text": "Некорректный список бафов. Введите буквы из 'азуэгдмнчо', до 6 букв.",
                    "keyboard": None,
                }

        elif state == "ask_token":
            # Попытка создания сессии VK API от имени пользователя
            token = message.strip()
            try:
                user_vk_session = vk_api.VkApi(token=token)
                user_vk = user_vk_session.get_api()
                # Проверим токен, выполнив простой запрос
                response = user_vk.users.get()
                if response:
                    user_info = response[0]
                    token_owner_id = user_info["id"]
                    logger.debug(
                        f"Токен пользователя {user_id} действителен и принадлежит {token_owner_id}."
                    )
                    dialog["data"]["token"] = token
                    dialog["data"]["token_owner_id"] = token_owner_id
                    dialog["data"][
                        "user_vk_session"
                    ] = user_vk_session  # Сохраняем сессию для дальнейшего использования
                    dialog["state"] = "ask_chat"
                    self.active_dialogs[user_id] = dialog

                    # Получаем список чатов с включенным модулем авто бафа
                    chats = self.chat_manager.get_chats_with_module("auto_buff")
                    if not chats:
                        return {
                            "text": "К сожалению, нет доступных чатов для авто бафа.",
                            "keyboard": None,
                        }

                    # Формируем список названий чатов для отображения
                    chat_names = [chat['name'] for chat in chats]
                    dialog["data"]["available_chats"] = chat_names
                    dialog["data"][
                        "chats"
                    ] = chats  # Сохраняем полную информацию о чатах

                    # Создаём клавиатуру с названиями чатов
                    buttons = [[name] for name in chat_names]
                    keyboard = create_keyboard(buttons, one_time=True)

                    return {
                        "text": "Выберите чат, в который хотите встать на авто баф:",
                        "keyboard": keyboard,
                    }
                else:
                    logger.error(
                        f"Не удалось получить информацию о пользователе по токену для {user_id}"
                    )
                    return {
                        "text": "Неверный токен. Пожалуйста, попробуйте снова.",
                        "keyboard": None,
                    }

            except vk_api.exceptions.ApiError as e:
                logger.error(f"Ошибка при валидации токена пользователя {user_id}: {e}")
                return {
                    "text": "Неверный токен. Пожалуйста, попробуйте снова.",
                    "keyboard": None,
                }

        elif state == "ask_chat":
            # Валидация выбранного чата
            chat_name = message.strip()
            available_chats = dialog["data"]["available_chats"]
            if chat_name in available_chats:
                dialog["data"]["chat_name"] = chat_name
                # Находим ID чата по имени
                chat = next(
                    (
                        chat
                        for chat in dialog["data"]["chats"]
                        if chat.get("name", None) == chat_name
                    ),
                    None,
                )
                if chat:
                    group_vk_session = vk_api.VkApi(token=VK_API_TOKEN)
                    group_vk = group_vk_session.get_api()
                    chat_id = chat["id"]

                    try:
                        # Сначала начинаем прослушивание лонгполла пользователя
                        user_vk_session = dialog["data"]["user_vk_session"]
                        user_longpoll = VkLongPoll(user_vk_session)
                        logger.debug(
                            f"Начинаем прослушивание лонгполла пользователя {user_id}"
                        )

                        # Создаём задачу для прослушивания лонгполла
                        chat_id_for_user = None

                        async def listen_for_dot():
                            nonlocal chat_id_for_user
                            while True:
                                events = await asyncio.get_event_loop().run_in_executor(
                                    None, user_longpoll.check
                                )
                                for event in events:
                                    if (
                                        event.type == VkEventType.MESSAGE_NEW
                                        and event.text == "."
                                        and event.from_chat
                                    ):
                                        chat_id_for_user = event.chat_id + 2000000000
                                        logger.debug(
                                            f"Пользователь {user_id} получил сообщение с точкой из чата {chat_id_for_user}"
                                        )
                                        return

                        listener_task = asyncio.create_task(listen_for_dot())

                        # Отправляем сообщение с точкой в чат от имени группы
                        group_vk.messages.send(
                            chat_id=chat_id - 2000000000,
                            message=".",
                            random_id=vk_api.utils.get_random_id(),
                        )
                        logger.debug(
                            f"Отправлено сообщение с точкой в чат {chat_name} ({chat_id})"
                        )

                        # Ждём, пока лонгполл получит сообщение или произойдёт таймаут
                        try:
                            await asyncio.wait_for(listener_task, timeout=10.0)
                        except asyncio.TimeoutError:
                            logger.error(
                                f"Пользователь {user_id} не получил сообщение с точкой из чата {chat_name}"
                            )
                            self.active_dialogs.pop(user_id)
                            return {
                                "text": f"Вы не состоите в чате '{chat_name}'. Диалог отменён.",
                                "keyboard": None,
                            }

                        if chat_id_for_user:
                            dialog["data"]["user_chat_id"] = chat_id_for_user
                            dialog["state"] = "completed"
                            self.active_dialogs[user_id] = dialog

                            # Диалог завершён, сохраняем данные в БД
                            token_owner_id = dialog["data"]["token_owner_id"]
                            self.user_manager.add_user(user_id=token_owner_id)
                            self.user_manager.set_auto_buff(
                                user_id=token_owner_id,
                                chat_id=chat_id_for_user,
                                group_chat_id=chat_id,
                                token=dialog["data"]["token"],
                                role=dialog["data"]["role"],
                                buff_list=dialog["data"].get("buff_list", None),
                            )

                            self.active_dialogs.pop(user_id)
                            return {
                                "text": f"Вы успешно встали на авто баф в чат '{chat_name}'!",
                                "keyboard": None,
                            }
                        else:
                            logger.error(
                                f"Не удалось получить chat_id для пользователя {user_id}"
                            )
                            self.active_dialogs.pop(user_id)
                            return {
                                "text": "Произошла ошибка при получении идентификатора чата. Диалог отменён.",
                                "keyboard": None,
                            }

                    except vk_api.exceptions.ApiError as e:
                        logger.error(
                            f"Ошибка при отправке сообщения в чат {chat_name}: {e}"
                        )
                        self.active_dialogs.pop(user_id)
                        return {
                            "text": f"Не удалось отправить сообщение в чат '{chat_name}'. Диалог отменён.",
                            "keyboard": None,
                        }
                else:
                    logger.error(f"Чат с названием '{chat_name}' не найден")
                    self.active_dialogs.pop(user_id)
                    return {
                        "text": "Произошла ошибка. Диалог отменён.",
                        "keyboard": None,
                    }

            else:
                logger.debug(
                    f"Пользователь {user_id} выбрал неверный чат '{chat_name}'"
                )
                buttons = [[name] for name in available_chats]
                keyboard = create_keyboard(buttons, one_time=True)
                return {
                    "text": "Пожалуйста, выберите чат из списка, используя кнопки ниже.",
                    "keyboard": keyboard,
                }

        else:
            logger.debug(f"Диалог с пользователем {user_id} завершён")
            self.active_dialogs.pop(user_id)
            return None

    async def handle_private_message(self, user_id, text):
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
                response = await self.dialog_manager.update_dialog(user_id, "")
                if response:
                    message = response.get("text", "")
                    keyboard = response.get("keyboard")
                    self.send_message(user_id, message, keyboard)
            elif text.lower() == "хочу сняться с авто бафа":
                self.dialog_manager.start_dialog(user_id, "remove_auto_buff")
                response = await self.dialog_manager.update_dialog(user_id, "")
                if response:
                    message = response.get("text", "")
                    keyboard = response.get("keyboard")
                    self.send_message(user_id, message, keyboard)
            else:
                self.send_message(
                    user_id,
                    "Неизвестная команда. Напишите 'Хочу встать на авто баф' или 'Хочу сняться с авто бафа' для начала.",
                )

    async def _handle_remove_auto_buff_dialog(self, user_id, dialog, message):
        state = dialog["state"]
        logger.debug(f"Состояние диалога снятия с авто бафа: {state}")

        if state == "start":
            # Получаем список чатов с включенным модулем авто бафа
            chats = self.chat_manager.get_chats_with_module("auto_buff")
            if not chats:
                self.active_dialogs.pop(user_id)
                return {
                    "text": "К сожалению, нет доступных чатов для снятия с авто бафа.",
                    "keyboard": None,
                }

            # Формируем список названий чатов для отображения
            chat_names = [chat["name"] for chat in chats]
            dialog["data"]["available_chats"] = chat_names
            dialog["data"]["chats"] = chats  # Сохраняем полную информацию о чатах
            dialog["state"] = "confirm_remove"
            self.active_dialogs[user_id] = dialog

            # Создаём клавиатуру с названиями чатов
            buttons = [[name] for name in chat_names]
            keyboard = create_keyboard(buttons, one_time=True)

            return {
                "text": "Выберите чат, из которого хотите сняться с авто бафа:",
                "keyboard": keyboard,
            }

        elif state == "confirm_remove":
            # Валидация выбранного чата
            selected_chat_name = message.strip()
            available_chats = dialog["data"]["available_chats"]
            if selected_chat_name in available_chats:
                # Находим ID чата по имени
                chat = next(
                    (
                        chat
                        for chat in dialog["data"]["chats"]
                        if chat["name"] == selected_chat_name
                    ),
                    None,
                )
                if chat:
                    chat_id = chat["id"]
                    # конец диалога
                    self.active_dialogs.pop(user_id)
                    if self.user_manager.get_auto_buff_by_group_chat_id(
                        user_id, chat_id
                    ):
                        self.user_manager.remove_auto_buff_by_group_chat_id(
                            user_id, chat_id
                        )
                        return {
                            "text": f"Вы сняты с авто бафа в чате '{selected_chat_name}'.",
                            "keyboard": None,
                        }
                    else:
                        return {
                            "text": f"Вы не стоите на авто бафе в чате '{selected_chat_name}'.",
                            "keyboard": None,
                        }

                else:
                    # Чат не найден (маловероятно, но на всякий случай)
                    self.active_dialogs.pop(user_id)
                    return {
                        "text": "Произошла ошибка. Диалог отменён.",
                        "keyboard": None,
                    }
            else:
                # Неверный выбор
                buttons = [[name] for name in available_chats]
                keyboard = create_keyboard(buttons, one_time=True)
                return {
                    "text": "Пожалуйста, выберите чат из списка, используя кнопки ниже.",
                    "keyboard": keyboard,
                }

        else:
            logger.debug(f"Диалог с пользователем {user_id} завершён")
            self.active_dialogs.pop(user_id)
            return None
