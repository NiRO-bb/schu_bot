import telebot
import sqlite3 # ДЛЯ РАБОТЫ С БД

# СООБЩЕНИЯ ПО РАСПИСАНИЮ
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time

# ВЫБОР СЛУЧАЙНОЙ ТЕМЫ
import random

from config import TOKEN
bot = telebot.TeleBot(TOKEN)

# СЛОВАРЬ ИСКЛЮЧЕНИЙ, ЧТОБЫ ПРИ НАЖАТИИ КНОПКИ НЕ ПРОИЗОШЛА ОШИБКА
exception = {
    '0' : 'Перейти в главное меню Бота',
    '1' : 'Перейти в меню изменения тем',
    '2' : 'Удалить тему',
    '3' : 'Показать список всех тем',
    '4' : 'Показать работы',
    '5' : 'Изменить тему',
    '6' : 'Изменить название темы',
    '7' : 'Изменить работу',
    '8' : 'Добавить фото',
    '9' : 'Удалить фото',
    '10' : 'Посмотреть работы',
    '11' : 'Создать новую тему',
    '12' : 'Перейти в меню уведомлений',
    '13' : 'Оставить',
    '14' : 'Изменить время уведомлений',
    '15' : 'Раннее уведомление',
    '16' : 'Позднее уведомление',
    '17' : 'Сохранить работу'
}

# КЛАВИАТУРЫ
main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
btn_start = telebot.types.KeyboardButton(text='Перейти в меню уведомлений')
btn_create_theme = telebot.types.KeyboardButton(text='Создать новую тему')
btn_delete_theme = telebot.types.KeyboardButton(text='Удалить тему')
btn_show_list = telebot.types.KeyboardButton(text='Показать список всех тем')
btn_show_photo = telebot.types.KeyboardButton(text='Показать работы')
btn_change = telebot.types.KeyboardButton(text='Изменить тему')
main_keyboard.add(btn_start, btn_create_theme)
main_keyboard.add(btn_delete_theme, btn_show_list)
main_keyboard.add(btn_show_photo, btn_change)

change_time_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
change_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True) # при измнении темы

# РАСПИСАНИЕ
scheduler = BackgroundScheduler()
scheduler.start()

@bot.message_handler(commands=['start'])
def welcome(msg):
    # ПО chat_id ПРОВЕРЯЕМ, СУЩЕСТВУЕТ ЛИ УЖЕ ЗАПИСЬ В БД ДЛЯ ЭТОГО ПОЛЬЗОВАТЕЛЯ
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM var WHERE chat_id = ?', (msg.chat.id,))
    chat_id_list = cursor.fetchall()

    if not chat_id_list:
        # ДОБАВЛЯЕМ В БД ОСНОВНЫЕ ПЕРЕМЕННЫЕ
        cursor.execute('INSERT INTO var (chat_id, saved_message, selected_theme, first_launch, id_start, id_end) VALUES (?, ?, ?, ?, ?, ?)',
                       (msg.chat.id, '', '', True, str(msg.chat.id)+'s', str(msg.chat.id)+'e'))

    cursor.execute('SELECT first_launch FROM var WHERE chat_id = ?', (msg.chat.id,))
    first_launch = cursor.fetchall()[0][0]

    # ДОБАВЛЯЕМ В БД ВРЕМЯ СООБЩЕНИЙ
    if first_launch:
        cursor.execute('UPDATE var SET first_launch = ? WHERE chat_id = ?', (False, msg.chat.id))

        cursor.execute('INSERT INTO message_time (chat_id, start_time, end_time) VALUES (?, ?, ?)',
                       (msg.chat.id, 5, 19))
        conn.commit()

        set_start(msg)
        set_end(msg)

    conn.commit()
    conn.close()

    # СОЗДАНИЕ КЛАВИАТУРЫ
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
    btn_start = telebot.types.KeyboardButton(text='Перейти в меню уведомлений')
    keyboard.add(btn_main_menu)
    keyboard.add(btn_start)
    bot.send_message(msg.chat.id, 'Привет.\n\nВ главном меню ты можешь работать с темами. '
                                  'Темы - просто название для твоих работ, которые ты захотел объединить вместе. '
                                  'Ты создаешь их самостоятельно и можешь загружать туда всё, что захочешь, я не ограничиваю тебя.\n\n'
                                  'В меню уведомлений ты можешь настроить время, когда я буду присылать тебе сообщения. '
                                  'К сожалению (или счастью) отключить уведомления нельзя, поэтому, если ты не получил моё сообщение в указанное время, значит сервер упал...\n\n'
                                  'Перейди в одно из меню для продолжения.', reply_markup=keyboard)


@bot.message_handler(func=lambda msg: msg.text=='Перейти в меню уведомлений')
def notification_menu(msg): # Перейти в меню уведомлений
    # ПОЛУЧАЕМ ЗНАЧЕНИЕ first_launch
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()

    # ПРИСВАИВАЕМ ЗНАЧЕНИЯ ИЗ БД ПЕРЕМЕННЫМ ВРЕМЕНИ
    cursor.execute('SELECT start_time FROM message_time WHERE chat_id = ?', (msg.chat.id,))
    start_time = int(cursor.fetchall()[0][0]) + 3

    cursor.execute('SELECT end_time FROM message_time WHERE chat_id = ?', (msg.chat.id,))
    end_time = int(cursor.fetchall()[0][0]) + 3
    conn.close()

    # СОЗДАНИЕ КЛАВИАТУРЫ ДЛЯ РАБОТЫ С РАСПИСАНИЕМ
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_change_time = telebot.types.KeyboardButton(text='Изменить время уведомлений')
    btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
    keyboard.add(btn_main_menu)
    keyboard.add(btn_change_time)
    def notification_msg_pattern(msg, start, end):
        bot.send_message(msg.chat.id, 'Я буду писать дважды в день.\n'
                                      f'Раннее уведомление в {start} (МСК): Я предложу тебе несколько твоих тем для работы, ты сможешь выбрать одну.\n'
                                      f'Позднее уведомление в {end} (МСК): Ты сможешь показать свои результаты, я сохраню их.\n\n'
                                      'На данный момент изменить можно только часы, минуты корректировать нельзя.', reply_markup=keyboard)

    # ВЫВОДИМ ПРАВИЛЬНОЕ ВРЕМЯ (проблемы возникают из-за того, что время на сервере стоит по UTC, а нам надо по МСКа)
    if start_time <= 23 and end_time <= 23:
        notification_msg_pattern(msg, start_time, end_time)

    elif start_time > 23 and end_time > 23:
        notification_msg_pattern(msg, start_time - 24, end_time - 24)

    elif start_time > 23 and end_time <= 23:
        notification_msg_pattern(msg, start_time - 24, end_time)

    elif start_time <= 23 and end_time > 23:
        notification_msg_pattern(msg, start_time, end_time - 24)

@bot.message_handler(func=lambda msg: msg.text=='Изменить время уведомлений')
def change_time_request(msg): # Изменить
    # СОЗДАНИЕ КЛАВИАТУРЫ ДЛЯ РАБОТЫ С РАСПИСАНИЕМ
    change_time_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_change_start_time = telebot.types.KeyboardButton(text='Раннее уведомление')
    btn_change_end_time = telebot.types.KeyboardButton(text='Позднее уведомление')
    btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
    change_time_keyboard.add(btn_main_menu)
    change_time_keyboard.add(btn_change_start_time, btn_change_end_time)
    bot.send_message(msg.chat.id, 'Какое уведомление ты хочешь изменить?', reply_markup=change_time_keyboard)

@bot.message_handler(func=lambda msg: msg.text=='Раннее уведомление')
def change_start_time_request(msg): # Раннее уведомление
    bot.send_message(msg.chat.id, 'Напиши новое время раннего уведомления.\nНапример: 10. Тогда сообщения будут приходить в 10 часов (МСК).', reply_markup=change_time_keyboard)
    bot.register_next_step_handler(msg, change_start_time)
def change_start_time(msg): # Ранее уведомление (2)
    flag = change_time_pattern(msg, change_start_time, 'start_time')
    if flag:
        set_start(msg)

@bot.message_handler(func=lambda msg: msg.text=='Позднее уведомление')
def change_end_time_request(msg): # Позднее уведомление
    bot.send_message(msg.chat.id,'Напиши новое время позднего уведомления.\nНапример: 21. Тогда сообщения будут приходить в 21 час (МСК).',reply_markup=change_time_keyboard)
    bot.register_next_step_handler(msg, change_end_time)
def change_end_time(msg): # Позднее уведомление (2)
    flag = change_time_pattern(msg, change_end_time, 'end_time')
    if flag:
        set_end(msg)

def change_time_pattern(msg, function, time_name):
    if msg.content_type != 'text':
        bot.send_message(msg.chat.id, 'Ты должен прислать мне текст, чтобы я мог его обработать.\nПопробуй ещё раз.')
        bot.register_next_step_handler(msg, function)
    elif msg.text != exception['0']:
        try:
            if isinstance(int(msg.text), (int)):
                time = time_error(msg) - 3
                if time < 0:
                    time += 24

                conn = sqlite3.connect('schu.db')
                cursor = conn.cursor()
                cursor.execute(f'UPDATE message_time SET {time_name} = ? WHERE chat_id = ?', (time, msg.chat.id))
                conn.commit()
                conn.close()
                return True

        except Exception:
            bot.send_message(msg.chat.id,
                             'Чтобы я мог установить время, ты должен написать целое число.\nПопробуй ещё раз.')
            bot.register_next_step_handler(msg, function)
            #return False
    else:
        bot.send_message(msg.chat.id, 'Возвращаю тебя в главное меню.', reply_markup=main_keyboard)


# ГЛАВНОЕ МЕНЮ
@bot.message_handler(func=lambda msg: msg.text=='Перейти в главное меню Бота')
def main_menu(msg): # Перейти в главное меню Бота
    # ОТОБРАЖЕНИЕ ВЫБРАННОЙ ТЕМЫ
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT selected_theme FROM var WHERE chat_id = ?', (msg.chat.id,))
    selected_theme = cursor.fetchall()[0][0]
    conn.close()
    if selected_theme == '':
        bot.send_message(msg.chat.id, 'Ты пока не выбрал тему для работы.')
    else:
        bot.send_message(msg.chat.id, f'Выбранная тема - "{selected_theme}".')
    # СОЗДАНИЕ КЛАВИАТУРЫ ГЛАВНОГО МЕНЮ
    bot.send_message(msg.chat.id, 'Что дальше?', reply_markup=main_keyboard)

@bot.message_handler(func=lambda msg: msg.text=='Создать новую тему')
def create_theme_request(msg): # Создать новую тему
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
    keyboard.add(btn_main_menu)
    bot.send_message(msg.chat.id, 'Напиши название новой темы.', reply_markup=keyboard)
    bot.register_next_step_handler(msg, create_theme)

def create_theme(msg): # Создать новую тему (2)
    # ПРОВЕРКА ТИПА ДАННЫХ
    if msg.content_type != 'text':
        bot.send_message(msg.chat.id, 'Ты должен прислать мне текст, чтобы я мог его обработать.\nПопробуй ещё раз.')
        bot.register_next_step_handler(msg, create_theme)
    elif msg.text != exception['0']:
        # НЕ ЯВЛЯЕТСЯ ЛИ ТЕКСТ ЧИСЛОМ
        try:
            if isinstance(float(msg.text), (int, float)):
                bot.send_message(msg.chat.id, 'Ты не можешь назвать тему, используя одни лишь цифры.\n'
                                              'Кстати, ты можешь использовать эмодзи.', reply_markup=main_keyboard)
        except Exception:
            # ПРОВОДИМ ПРОВЕРКУ СО СЛОВАРЕМ ИСКЛЮЧЕНИЙ (exception)
            if name_check(msg):
                # ПРОВЕРКА НА НАЛИЧИЕ ТЕМЫ В БД
                if theme_check(msg):
                    bot.send_message(msg.chat.id, 'Такая тема уже существует.', reply_markup=main_keyboard)
                else:
                    # ДОБАВЛЕНИЕ В БД
                    bot.send_message(msg.chat.id, f'Была создана тема - "{msg.text.lower()}"', reply_markup=main_keyboard)
                    conn = sqlite3.connect('schu.db')
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO list (chat_id, theme) VALUES (?, ?)', (msg.chat.id, msg.text.lower()))
                    conn.commit()
                    conn.close()
            else:
                bot.send_message(msg.chat.id, 'Извини, ты не можешь назвать тему так.\n'
                                              'Название темы совпадает с названием одной из команд.', reply_markup=main_keyboard)
    else:
        bot.send_message(msg.chat.id, 'Возвращаю тебя в главное меню.', reply_markup=main_keyboard)

@bot.message_handler(func=lambda msg: msg.text=='Удалить тему')
def delete_theme_request(msg): # Удалить тему
    # ПОЛУЧАЕМ СПИСОК ВСЕХ ТЕМ ИЗ БД
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT theme FROM list WHERE chat_id = ?', (msg.chat.id,))
    theme_list = cursor.fetchall()
    conn.close()

    # ПРОВЕРЯЕМ, НЕ ПУСТОЙ ЛИ СПИСОК
    if theme_list:
        # СОЗДАЕМ КНОПКУ ОТМЕНЫ
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
        keyboard.add(btn_main_menu)

        themes = [theme[0] for theme in theme_list]
        for theme in themes:
            # ДЛЯ КАЖДОЙ ИМЕЮЩЕЙСЯ ТЕМЫ СОЗДАЕМ КНОПКУ
            btn = telebot.types.KeyboardButton(text=f'{theme}')
            keyboard.add(btn)

        # ПОСЛЕ СОЗДАНИЯ КЛАВИАТУРЫ ОСТАЕТСЯ ТОЛЬКО НАЖАТЬ НА КНОПКУ
        bot.send_message(msg.chat.id, 'Выбери тему, которую хочешь удалить.', reply_markup=keyboard)
        bot.register_next_step_handler(msg, delete_theme)

    else:
        bot.send_message(msg.chat.id, 'Список твоих тем пуст. Мне нечего удалять.', reply_markup=main_keyboard)

def delete_theme(msg): # Удалить тему (2)
    if msg.content_type != 'text':
        bot.send_message(msg.chat.id, 'Ты должен прислать мне текст, чтобы я мог его обработать.\nПопробуй ещё раз.')
        bot.register_next_step_handler(msg, delete_theme)
    elif msg.text != exception['0']:
        # ПРОВЕРКА на наличие темы
        conn = sqlite3.connect('schu.db')
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id FROM list WHERE theme = ?', (msg.text.lower(),))
        result = cursor.fetchall()
        conn.close()

        if result:
            # УДАЛЕНИЕ ИЗ БД
            conn = sqlite3.connect('schu.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM list WHERE theme = ?', (msg.text.lower(),))
            cursor.execute('DELETE FROM art WHERE theme = ?', (msg.text.lower(),))

            # СРАВНИВАЕМ С selected_theme
            cursor.execute('SELECT selected_theme FROM var WHERE chat_id = ?', (msg.chat.id,))
            if cursor.fetchall()[0][0] == msg.text.lower():
                cursor.execute('UPDATE var SET selected_theme = ? WHERE chat_id = ?', ('', msg.chat.id))

            conn.commit()
            conn.close()
            bot.send_message(msg.chat.id, f'Была удалена тема - "{msg.text.lower()}"', reply_markup=main_keyboard)

        else:
            bot.send_message(msg.chat.id, 'Такой темы нет в твоём списке.', reply_markup=main_keyboard)
    else:
        bot.send_message(msg.chat.id, 'Возвращаю тебя в главное меню.', reply_markup=main_keyboard)

@bot.message_handler(func=lambda msg: msg.text=='Показать список всех тем')
def show_list_request(msg): # Показать список всех тем
    # ПОЛУЧЕНИЕ ДАННЫХ ИЗ БД
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT theme FROM list WHERE chat_id = ?', (msg.chat.id,))
    theme_list = cursor.fetchall()
    conn.close()

    # ПРОВЕРКА, НЕ ПУСТОЙ ЛИ СПИСОК
    if theme_list:
        themes = '\n'.join([theme[0] for theme in theme_list])
        bot.send_message(msg.chat.id, 'Вот твой список тем:\n'
                                               f'{themes}')

    else:
        bot.send_message(msg.chat.id, 'Твой список тем пуст.')

@bot.message_handler(func=lambda msg: msg.text=='Показать работы')
def show_photo_request(msg): # Показать работы
    # ПОЛУЧАЕМ СПИСОК ТЕМ
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT theme FROM list WHERE chat_id = ?', (msg.chat.id,))
    theme_list = cursor.fetchall()
    conn.close()

    # НЕ ПУСТОЙ ЛИ СПИСОК
    if theme_list:
        # СОЗДАНИЕ КЛАВИАТУРЫ ВСЕХ ИМЕЮЩИХСЯ ТЕМ
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
        keyboard.add(btn_main_menu)

        themes = [theme[0] for theme in theme_list]
        # СОЗДАЕМ КНОПКИ
        for theme in themes:
            btn = telebot.types.KeyboardButton(text=f'{theme}')
            keyboard.add(btn)
        bot.send_message(msg.chat.id, 'Выбери тему, работы которой хочешь увидеть.', reply_markup=keyboard)
        bot.register_next_step_handler(msg, show_photo)

    else:
        bot.send_message(msg.chat.id, 'Твой список тем пуст. Я не могу найти ни одной работы.')

def show_photo(msg): # Показать работы (2)
    if msg.content_type != 'text':
        bot.send_message(msg.chat.id, 'Ты должен прислать мне текст, чтобы я мог его обработать.\nПопробуй ещё раз.')
        bot.register_next_step_handler(msg, show_photo)
    elif msg.text != exception['0']:
        if theme_check(msg):
            # ИЗМЕНЯЕМ ЗНАЧЕНИЕ saved_message
            conn = sqlite3.connect('schu.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE var SET saved_message = ? WHERE chat_id = ?', (msg.text.lower(), msg.chat.id))
            conn.commit()
            conn.close()
            # ПОЛУЧАЕМ ФОТО
            get_photo(msg)
        else:
            bot.send_message(msg.chat.id, 'Такой темы нет в твоём списке.', reply_markup=main_keyboard)
    else:
        bot.send_message(msg.chat.id, 'Возвращаю тебя в главное меню..', reply_markup=main_keyboard)

@bot.message_handler(func=lambda msg: msg.text=='Изменить тему')
def change_request(msg): # Изменить тему
    # ПОЛУЧАЕМ СПИСОК ТЕМ
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT theme FROM list WHERE chat_id = ?', (msg.chat.id,))
    theme_list = cursor.fetchall()
    conn.close()

    # НЕ ПУСТОЙ ЛИ СПИСОК
    if theme_list:
        # СОЗДАНИЕ КЛАВИАТУРЫ ДЛЯ ВЫБОРА ИЗМЕНЯЕМОЙ ТЕМЫ
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
        keyboard.add(btn_main_menu)

        themes = [theme[0] for theme in theme_list]
        # СОЗДАЕМ КНОПКИ
        for theme in themes:
            btn = telebot.types.KeyboardButton(text=f'{theme}')
            keyboard.add(btn)
        bot.send_message(msg.chat.id, 'Выбери тему, которую хочешь изменить.', reply_markup=keyboard)

    else:
        bot.send_message(msg.chat.id, 'В твоём списке нет ни одной темы.')
    bot.register_next_step_handler(msg, change)

def change(msg): # Изменить тему (2)
    if msg.content_type != 'text':
        bot.send_message(msg.chat.id, 'Ты должен прислать мне текст, чтобы я мог его обработать.\nПопробуй ещё раз.')
        bot.register_next_step_handler(msg, change)
    elif msg.text != exception['0']:
        # ПРОВЕРЯЕМ, СУЩЕСТВУЕТ ЛИ ТЕМА
        if theme_check(msg):
            # ИЗМЕНЯЕМ ЗНАЧЕНИЕ saved_message
            conn = sqlite3.connect('schu.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE var SET saved_message = ? WHERE chat_id = ?', (msg.text.lower(), msg.chat.id))
            conn.commit()
            conn.close()

            change_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn_change_theme = telebot.types.KeyboardButton(text='Изменить название темы')
            btn_change_photo = telebot.types.KeyboardButton(text='Изменить работы')
            btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
            change_keyboard.add(btn_main_menu)
            change_keyboard.add(btn_change_theme, btn_change_photo)
            bot.send_message(msg.chat.id, f'Была выбрана тема - "{msg.text.lower()}".\n'
                                              'Дальше что?', reply_markup=change_keyboard)

        else:
            bot.send_message(msg.chat.id, 'Такой темы нет в твоём списке.', reply_markup=main_keyboard)
    else:
        bot.send_message(msg.chat.id, 'Возвращаю тебя в главное меню..', reply_markup=main_keyboard)

@bot.message_handler(func=lambda msg: msg.text=='Изменить название темы')
def change_theme_request(msg): # Изменить название темы
    bot.send_message(msg.chat.id, f'Напиши новое название темы.')
    bot.register_next_step_handler(msg, change_theme)

def change_theme(msg): # Изменить название темы (2)
    if msg.content_type != 'text':
        bot.send_message(msg.chat.id, 'Ты должен прислать мне текст, чтобы я мог его обработать.\nПопробуй ещё раз.')
        bot.register_next_step_handler(msg, change_theme)
    elif msg.text != exception['0']:
        if name_check(msg):
            # ПОЛУЧАЕМ ЗНАЧЕНИЕ SAVED_MESSAGE ИЗ БД
            conn = sqlite3.connect('schu.db')
            cursor = conn.cursor()
            cursor.execute('SELECT saved_message FROM var WHERE chat_id = ?', (msg.chat.id,))
            saved_message = cursor.fetchall()[0][0]

            # ИЗМЕНЯЕМ НАЗВАНИЕ ТЕМЫ В БД
            cursor.execute('UPDATE list SET theme = ? WHERE theme = ?', (msg.text.lower(), saved_message))
            cursor.execute('UPDATE art SET theme = ? WHERE theme = ?', (msg.text.lower(), saved_message))

            # МЕНЯЕМ НАЗВАНИЕ selected_theme, если оно совпадает
            cursor.execute('SELECT selected_theme FROM var WHERE chat_id = ?', (msg.chat.id,))
            if cursor.fetchall()[0][0] == saved_message:
                cursor.execute('UPDATE var SET selected_theme = ? WHERE chat_id = ?', (msg.text.lower(), msg.chat.id))

            # УВЕДОМЛЯЕМ ПОЛЬЗОВАТЕЛЯ ОБ УСПЕШНОМ ДЕЙСТВИИ
            bot.send_message(msg.chat.id, f'Я изменил название темы "{saved_message}".\n'
                                              f'Теперь она называется - "{msg.text.lower()}"', reply_markup=change_keyboard)
            cursor.execute('UPDATE var SET saved_message = ? WHERE chat_id = ?', (msg.text.lower(), msg.chat.id))
            conn.commit()
            conn.close()
        else:
            bot.send_message(msg.chat.id, 'Извини, ты не можешь назвать тему так.\n'
                                          'Название темы совпадает с названием одной из команд.', reply_markup=main_keyboard)
    else:
        bot.send_message(msg.chat.id, 'Возвращаю тебя в главное меню.', reply_markup=main_keyboard)

@bot.message_handler(func=lambda msg: msg.text=='Изменить работы')
def change_photo_request(msg): # Изменить работы
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_change_photo_add = telebot.types.KeyboardButton(text='Добавить фото')
    btn_change_photo_delete = telebot.types.KeyboardButton(text='Удалить фото')
    btn_change_photo_show = telebot.types.KeyboardButton(text='Посмотреть работы')
    btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
    keyboard.add(btn_main_menu)
    keyboard.add(btn_change_photo_add, btn_change_photo_delete, btn_change_photo_show)
    bot.send_message(msg.chat.id, 'Что именно ты хочешь сделать с работами?\n\n'
                                  'ВНИМАНИЕ: кнопка "Удалить фото" удалит все фотографии выбранной темы.', reply_markup=keyboard)

@bot.message_handler(func=lambda msg: msg.text=='Добавить фото')
def change_photo_add_request(msg): # Добавить фото
    bot.send_message(msg.chat.id, 'Покажи фотографию, которую хочешь сохранить.\n'
                                  'Присылай фотографии по одной.')
    bot.register_next_step_handler(msg, change_photo_add)

def change_photo_add(msg): # Добавить фото (2)
    add_photo_pattern(msg, True)
def add_photo_pattern(msg, from_change):
    if msg.content_type != 'photo':
        if msg.text == exception['0']:
            bot.send_message(msg.chat.id, 'Возвращаю тебя в главное меню..', reply_markup=main_keyboard)
        bot.send_message(msg.chat.id, 'Ты должен прислать мне фотографию, чтобы я мог её сохранить.\nПопробуй ещё раз.')
        bot.register_next_step_handler(msg, change_photo_add)
    else:
        # СОХРАНЕНИЕ ФОТО В БД
        if from_change:
            conn = sqlite3.connect('schu.db')
            cursor = conn.cursor()
            cursor.execute('SELECT saved_message FROM var WHERE chat_id = ?', (msg.chat.id,))
            saved_message = cursor.fetchall()[0][0]

            cursor.execute('INSERT INTO art (chat_id, theme, photo) VALUES (?, ?, ?)',
                               (msg.chat.id, saved_message, msg.photo[-1].file_id))
            conn.commit()
            conn.close()
            bot.send_message(msg.chat.id, 'Работа сохранена.')
        else:
            conn = sqlite3.connect('schu.db')
            cursor = conn.cursor()
            cursor.execute('SELECT selected_theme FROM var WHERE chat_id = ?', (msg.chat.id,))
            selected_theme = cursor.fetchall()[0][0]

            cursor.execute('INSERT INTO art (chat_id, theme, photo) VALUES (?, ?, ?)',
                               (msg.chat.id, selected_theme, msg.photo[-1].file_id))
            conn.commit()
            conn.close()
            bot.send_message(msg.chat.id,'Я сохранил твою работу. Ты молодец. Не прекращай работать и помни, что любой твой труд лучше бездействия.')

@bot.message_handler(func=lambda msg: msg.text=='Удалить фото')
def change_photo_delete_request(msg): # Удалить фото
    # ПОЛУЧЕНИЕ SAVED_MESSAGE ИЗ БД
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT saved_message FROM var WHERE chat_id = ?', (msg.chat.id,))
    saved_message = cursor.fetchall()[0][0]

    # УДАЛЕНИЕ ДАННЫХ ИЗ БД
    cursor.execute('DELETE FROM art WHERE theme = ?',(saved_message,))
    conn.commit()
    conn.close()
    bot.send_message(msg.chat.id, f'Все работы из темы "{saved_message}" были удалены.', reply_markup=main_keyboard)

@bot.message_handler(func=lambda msg: msg.text=='Посмотреть работы')
def change_photo_show_request(msg): # Посмотреть работы
   get_photo(msg)


# ФУНКЦИИ
def theme_check(msg):
    # ПОЛУЧАЕМ СПИСОК ТЕМ
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT theme FROM list WHERE chat_id = ?', (msg.chat.id,))
    theme_list = cursor.fetchall()
    conn.close()

    # ПРОВЕРЯЕМ, ЕСТЬ ЛИ ИНТЕРЕСУЮЩАЯ НАС ТЕМА В БД
    flag = False
    for aaa in [theme[0] for theme in theme_list]:
        if msg.text.lower() == aaa:
            flag = True
    return flag

def get_photo(msg):
    # ПОЛУЧАЕМ SAVED_MESSAGE ИЗ БД
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT saved_message FROM var WHERE chat_id = ?', (msg.chat.id,))
    saved_message = cursor.fetchall()[0][0]

    # ПОЛУЧАЕМ СПИСОК ФОТО ИЗ БД
    cursor.execute('SELECT photo FROM art WHERE theme = ?', (saved_message,))
    photos = cursor.fetchall()
    conn.close()

    # ПРОВЕРКА НА НАЛИЧИЕ ФОТО
    if photos:
        bot.send_message(msg.chat.id, f'Работы по теме "{saved_message}":', reply_markup=main_keyboard)
        # ОТПРАВКА ФАЙЛОВ ГРУППОЙ
        media_group = []
        for photo in photos:
            media_group.append(telebot.types.InputMediaPhoto(photo[0]))
        # РАЗБИВАЕМ ФОТО НА ГРУППЫ ПО 10 ШТУК
        for i in range(0, len(media_group), 10):
            bot.send_media_group(msg.chat.id, media_group[i:i + 10])

    else:
        bot.send_message(msg.chat.id, f'Тема "{saved_message}" не содержит ни одной работы.', reply_markup=main_keyboard)

def name_check(msg):
    # ПРОВЕРКА НА ИСКЛЮЧЕННЫЕ НАЗВАНИЯ (СЛОВАРЬ EXCEPTION)
    flag = True
    for name in exception.values():
        if name.lower() == msg.text.lower():
            flag = False
    return flag

# ФУНКЦИЯ ДЛЯ ПРОВЕРКИ СООБЩЕНИЯ, ПРИСЫЛАЕМОГО ПОЛЬЗОВАТЕЛЕМ ПРИ УСТАНОВКЕ РАСПИСАНИЯ
def time_error(msg):
    if int(msg.text) >= 0 and int(msg.text) <= 23:
        return int(msg.text)
    else:
        bot.send_message(msg.chat.id, 'Время, которое ты указал, некорректно.\n'
                                      'Оно должно быть в пределах от 0 до 23.', reply_markup=change_time_keyboard)


def set_start(msg):
    # ФУНКЦИЯ СРАБОТАЕТ В УКАЗАННОЕ ВРЕМЯ
    def start_work_msg():
        bot.send_message(msg.chat.id, 'Привет.\n'
                                      'Давай приступим к делу.')
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

        # ПОЛУЧАЕМ СПИСОК ТЕМ ИЗ БД
        conn = sqlite3.connect('schu.db')
        cursor = conn.cursor()
        cursor.execute('SELECT theme FROM list WHERE chat_id = ?', (msg.chat.id,))
        theme_list = cursor.fetchall()
        conn.close()

        # ПРОВЕРКА КОЛИЧЕСТВА ТЕМ
        if not theme_list:
            bot.send_message(msg.chat.id, 'Твой список тем пуст. Для работы мне нужна хотя бы одна тема.\n'
                                          'Поработаем в следующий раз.')

        elif len(theme_list) < 2:
            bot.send_message(msg.chat.id, 'В твоём списке тем всего одна тема. Создай ещё одну.\n'
                                          'Поработаем в следующий раз.')

        else:
            themes = [theme[0] for theme in theme_list]
            # ВЫБИРАЕМ 2 СЛУЧАЙНЫЕ ТЕМЫ ИЗ ИМЕЮЩИХСЯ
            theme1 = random.choice(themes)
            theme2 = random.choice(themes)
            while theme2 == theme1:
                theme2 = random.choice(themes)

            # СОЗДАЕМ КНОПКИ СЛУЧАЙНЫХ ТЕМ
            btn1 = telebot.types.KeyboardButton(text=f'{theme1}')
            btn2 = telebot.types.KeyboardButton(text=f'{theme2}')
            keyboard.add(btn1, btn2)

            bot.send_message(msg.chat.id, 'Я выбрал две случайные темы из твоего списка. Выбери ту, над которой хочешь поработать.',
                             reply_markup=keyboard)
            bot.register_next_step_handler(msg, func_selected_theme)

    # ПОЛУЧАЕМ ЗНАЧЕНИЕ start_time
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT start_time FROM message_time WHERE chat_id = ?', (msg.chat.id,))
    start_time = int(cursor.fetchall()[0][0])

    cursor.execute('SELECT id_start FROM var WHERE chat_id = ?', (msg.chat.id,))
    id_start = cursor.fetchall()[0][0]

    conn.close()
    # ПРОВЕРЯЕМ, СУЩЕСТВУЕТ ЛИ УЖЕ ЭТА ЗАДАЧА (ЕСЛИ ДВЕ ЗАДАЧИ ИМЕЮТ ОДИН ID, ТО ПРОИЗОЙДЕТ ОШИБКА)
    if scheduler.get_job(id_start):
        scheduler.remove_job(id_start)

    # ДОБАВЛЯЕМ ЗАДАЧУ В РАСПИСАНИЕ # закладка
    scheduler.add_job(start_work_msg, CronTrigger(hour=start_time, minute=0), id=id_start)
    bot.send_message(msg.chat.id, 'Время раннего уведомления успешно установлено!')

def func_selected_theme(msg):
    if msg.content_type != 'text':
        bot.send_message(msg.chat.id, 'Ты должен нажать на одну из кнопок. Пожалуйста, не надо ничего присылать.\nПопробуй ещё раз.')
        bot.register_next_step_handler(msg, func_selected_theme)
    else:
        # ИЗМЕНЯЕМ ЗНАЧЕНИЕ SELECTED_THEME, ЧТОБЫ БОТ ЗНАЛ, КАКУЮ ТЕМУ ТЫ ВЫБРАЛ В НАЧАЛЕ ДНЯ (ПРИ ПЕРВОМ СООБЩЕНИИ)
        conn = sqlite3.connect('schu.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE var SET selected_theme = ? WHERE chat_id = ?', (msg.text.lower(), msg.chat.id))
        cursor.execute('UPDATE var SET saved_message = ? WHERE chat_id = ?', (msg.text.lower(), msg.chat.id))
        conn.commit()
        conn.close()
        # ВЫВОДИМ СПИСОК РАБОТ ДЛЯ УДОБСТВА
        get_photo(msg)

def set_end(msg):
    def end_work_msg():
        # ПРОВЕРЯЕМ, СУЩЕСТВУЕТ ЛИ selected_theme
        conn = sqlite3.connect('schu.db')
        cursor = conn.cursor()
        cursor.execute('SELECT selected_theme FROM var WHERE chat_id = ?', (msg.chat.id,))
        if cursor.fetchall()[0][0] == '':
            bot.send_message(msg.chat.id, '', reply_markup=main_keyboard)
            conn.close()
        else:
            cursor.execute('SELECT selected_theme FROM var WHERE chat_id = ?', (msg.chat.id,))
            selected_theme = cursor.fetchall()[0][0]

            conn.commit()
            conn.close()

            keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn_main_menu = telebot.types.KeyboardButton(text='Перейти в главное меню Бота')
            btn_save = telebot.types.KeyboardButton(text='Сохранить работу')
            keyboard.add(btn_main_menu)
            keyboard.add(btn_save)
            bot.send_message(msg.chat.id, f'Как там "{selected_theme}"?\n'
                                          f'Можешь прислать мне результаты, чтобы я мог их сохранить.', reply_markup=keyboard)

    # ПОЛУЧАЕМ ЗНАЧЕНИЕ end_time
    conn = sqlite3.connect('schu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT end_time FROM message_time WHERE chat_id = ?', (msg.chat.id,))
    end_time = int(cursor.fetchall()[0][0])

    cursor.execute('SELECT id_end FROM var WHERE chat_id = ?', (msg.chat.id,))
    id_end = cursor.fetchall()[0][0]
    conn.close()

    if scheduler.get_job(id_end):
        scheduler.remove_job(id_end)
    # ДОБАВЛЯЕМ ЗАДАЧУ В РАСПИСАНИЕ # закладка
    scheduler.add_job(end_work_msg, CronTrigger(hour=end_time, minute=0), id=id_end)
    bot.send_message(msg.chat.id, 'Время позднего уведомления успешно установлено!')

@bot.message_handler(func=lambda msg: msg.text=='Сохранить работу')
def save_work(msg):
    add_photo_pattern(msg, False)

if __name__ == '__main__':
    print('Бот запущен!')
    bot.infinity_polling()

# РАСПИСАНИЕ РАБОТАЕТ ПОСТОЯННО
try:
    while True:
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()