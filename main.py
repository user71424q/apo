import asyncio
from services.vk_api_client import VkApiClient
from services.chat_manager import ChatManager
from services.user_manager import UserManager
from services.dialog_manager import DialogManager
from utils.logger import logger


async def main():
    logger.info("Запуск бота")
    chat_manager = ChatManager()
    user_manager = UserManager()
    dialog_manager = DialogManager(chat_manager, user_manager)


    vk_client = VkApiClient(
        dialog_manager, user_manager, chat_manager
    )

    await vk_client.start_listening()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота")
