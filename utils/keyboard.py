import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


def create_keyboard(buttons, inline=False, one_time=False):
    keyboard = VkKeyboard(inline=inline, one_time=one_time)
    for i, row in enumerate(buttons):
        for label in row:
            keyboard.add_button(label, color=VkKeyboardColor.PRIMARY)
        if i < len(buttons) - 1:
            keyboard.add_line()
    return keyboard.get_keyboard()
