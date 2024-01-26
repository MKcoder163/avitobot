import logging
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import time

last_task_completion_time = 0

API_TOKEN = '6730947645:AAF6Y5QxE3NAgPRA6sJ4Y3ovFA06VSMlqNg'
CHAT_ID_TO_SEND = 1002103365867  # Замените на ваш ID чата
YOUR_LOG_GROUP_CHAT_ID = -1002103365867

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


class OrderReviewsStep(StatesGroup):
    url = State()
    count = State()
    contact = State()
    order_number = State()


class NewTaskStep(StatesGroup):
    task = State()


class TaskExecutionStep(StatesGroup):
    waiting_for_screenshot = State()
    waiting_for_avito_username = State()
    waiting_for_phone_number = State()
    waiting_for_bank_info = State()


current_order_number = 0  # Переменная для хранения текущего номера заказа
current_task = None  # Переменная для хранения текущего задания


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_order_reviews = types.KeyboardButton("1. Заказать отзывы")
    button_task_execution = types.KeyboardButton("2. Выполнить задание")
    markup.add(button_order_reviews, button_task_execution)

    await message.answer("Выберите действие:", reply_markup=markup)


@dp.message_handler(lambda message: message.text.startswith("1. Заказать отзывы"))
async def order_reviews(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_button = types.KeyboardButton("Отмена")
    markup.add(cancel_button)

    await OrderReviewsStep.url.set()
    await message.answer("Введите ссылку:", reply_markup=markup)


# Добавьте новый обработчик сообщений для отмены на каждом этапе
@dp.message_handler(lambda message: message.text.lower() == "отмена", state='*')
async def cancel_operation(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
        await message.answer(f"Действие отменено для продолжения работы введите /start .", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("Нет активных операций для отмены.")


@dp.message_handler(state=OrderReviewsStep.url)
async def process_url(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['url'] = message.text

    await message.answer("Введите количество отзывов:")
    await OrderReviewsStep.next()


@dp.message_handler(state=OrderReviewsStep.count)
async def process_count(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['count'] = message.text

    await message.answer("Введите контакт для связи:")
    await OrderReviewsStep.next()


@dp.message_handler(state=OrderReviewsStep.contact)
async def process_contact(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['contact'] = message.text

    global current_order_number
    current_order_number += 1
    order_number_str = str(current_order_number).zfill(4)

    async with state.proxy() as data:
        data['order_number'] = order_number_str

    # Укажите chat_id вашей группы вместо message.chat.id
    group_chat_id = -1002103365867  # Замените на фактический chat_id вашей группы
    order_info = f"Номер заказа: {order_number_str}\nСсылка: {data['url']}\nКоличество отзывов: {data['count']}\n" \
                  f"Контакт для связи: {data['contact']}"

    await bot.send_message(group_chat_id, order_info)

    await message.answer(f"Ваш заказ принят. Спасибо!\nНомер заказа: {order_number_str}")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_order_reviews = types.KeyboardButton("1. Заказать отзывы")
    button_task_execution = types.KeyboardButton("2. Выполнить задание")
    markup.add(button_order_reviews, button_task_execution)

    await message.answer("Выберите действие:", reply_markup=markup)
    await state.finish()


@dp.message_handler(commands=['newtask'])
async def new_task_start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_button = types.KeyboardButton("Отмена")
    markup.add(cancel_button)
    await NewTaskStep.task.set()
    await message.answer("Введите новое задание:", reply_markup=markup)


@dp.message_handler(state=NewTaskStep.task)
async def process_new_task(message: types.Message, state: FSMContext):
    global current_task
    current_task = message.text

    group_chat_id = YOUR_LOG_GROUP_CHAT_ID
    caption = f"Новое задание:\n\n{current_task}"
    await bot.send_message(group_chat_id, caption)

    await state.finish()
    await message.answer("Новое задание добавлено.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_order_reviews = types.KeyboardButton("1. Заказать отзывы")
    button_task_execution = types.KeyboardButton("2. Выполнить задание")
    markup.add(button_order_reviews, button_task_execution)

    await message.answer("Выберите действие:", reply_markup=markup)


@dp.message_handler(lambda message: message.text.startswith("2. Выполнить задание"))
async def get_task(message: types.Message):
    remaining_time = time_until_next_task()
    if remaining_time > 0:
        hours, remainder = divmod(remaining_time, 3600)
        minutes, _ = divmod(remainder, 60)
        await message.answer(f"Выполнение нового задания возможно через {int(hours)} часов и {int(minutes)} минут.")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cancel_button = types.KeyboardButton("Отмена")
        markup.add(cancel_button)
        if current_task:
            await message.answer(f"Ваше текущее задание:\n\n{current_task}."+"""
            
Гайд по выполнению:
1. Пишешь диалог 
  а) Здравствуйте)
  б) пару вопросов по товару
  в) между сообщениями ждёшь ответа
  г) в конце просишь номер телефона или тг
2. Скринишь весь диалог
3. После последнего сообщения в диалоге, ждёшь 1,5 часа 
4. Написание отзыва
5.Кидаешь скрины всей переписки и самого отзыва""", reply_markup=markup)
            await TaskExecutionStep.waiting_for_screenshot.set()
            await message.answer(" Теперь отправьте скриншот выполненного задания:")
        else:
            await message.answer("У вас нет текущего задания. Попросите куратора добавить новое задание.")


@dp.message_handler(state=TaskExecutionStep.waiting_for_screenshot, content_types=types.ContentType.PHOTO)
async def process_screenshot(message: types.Message, state: FSMContext):
    screenshot_file_id = message.photo[-1].file_id
    username = message.from_user.username if message.from_user.username else "Нет username"
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    group_chat_id = -1002103365867
    await bot.send_photo(group_chat_id, screenshot_file_id)

    if message.photo[-1] != message.photo[0]:  # Check if there are more screenshots
        await message.answer("Отправьте еще скриншот или введите /next, чтобы перейти к следующему шагу.")
        await TaskExecutionStep.waiting_for_screenshot.set()
    else:
        await TaskExecutionStep.waiting_for_avito_username.set()
        await message.answer("Теперь введите ваше имя на Авито:")
@dp.message_handler(state=TaskExecutionStep.waiting_for_screenshot, commands=['next'])
async def skip_screenshot(message: types.Message, state: FSMContext):
    await TaskExecutionStep.waiting_for_avito_username.set()
    await message.answer("Теперь введите ваше имя на Авито:")

@dp.message_handler(state=TaskExecutionStep.waiting_for_avito_username)
async def process_avito_username(message: types.Message, state: FSMContext):
    avito_username = message.text
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = message.from_user.username if message.from_user.username else "Нет username"

    group_chat_id = -1002103365867
    caption = f"Пользователь: @{username}\nДата и время выполнения задания: {current_datetime}\nИмя на Авито: {avito_username}\nЗадание: {current_task}"
    await bot.send_message(group_chat_id, caption)

    await TaskExecutionStep.waiting_for_phone_number.set()
    await message.answer("Теперь введите ваш номер телефона:")


@dp.message_handler(state=TaskExecutionStep.waiting_for_phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    phone_number = message.text

    group_chat_id = -1002103365867
    caption = f"Номер телефона: {phone_number}"
    await bot.send_message(group_chat_id, caption)

    await TaskExecutionStep.waiting_for_bank_info.set()
    await message.answer("Теперь введите информацию о банке для зачисления средств:")


@dp.message_handler(state=TaskExecutionStep.waiting_for_bank_info)
async def process_bank_info(message: types.Message, state: FSMContext):
    bank_info = message.text

    group_chat_id = -1002103365867
    caption = f"Информация о банке: {bank_info}"
    await bot.send_message(group_chat_id, caption)
    global last_task_completion_time
    last_task_completion_time = time.time()  # Запоминаем время выполнения текущего задания

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_order_reviews = types.KeyboardButton("1. Заказать отзывы")
    button_task_execution = types.KeyboardButton("2. Выполнить задание")
    markup.add(button_order_reviews, button_task_execution)

    await message.answer(f"Спасибо за выполнение задания. Задание завершено. Оплата будет произведена после проверки.", reply_markup=markup)
    await state.finish()

def time_until_next_task():
    global last_task_completion_time
    current_time = time.time()
    elapsed_time = current_time - last_task_completion_time
    remaining_time = max(0, 48 * 60 * 60 - elapsed_time)  # Время в секундах
    return remaining_time


if __name__ == '__main__':
    from aiogram import executor
    from aiogram.contrib.fsm_storage.memory import MemoryStorage

    storage = MemoryStorage()
    dp.storage = storage

    executor.start_polling(dp, skip_updates=True)
