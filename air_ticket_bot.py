# -*- coding: utf-8 -*-

"""
Use python3.8

Основной модуль, из него производится запуск бота
"""

import requests
import logging
from random import randint

from pony.orm import db_session

import handlers
from air_traffic_controller import route_controller, route_formation
from models import UserState, Registration
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll
from vk_api.vk_api import VkApi


try:
    import settings
except ImportError:
    exit('DO --->>>cp setting.py.default settings.py<<<--- and set group_id and group_token!')


def configure_logging():
    """
    Создание и конфигурация логера
    """
    bot_log = logging.getLogger(name='air_ticket_bot')

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(fmt='%(levelname)s %(message)s'))
    stream_handler.setLevel(logging.INFO)
    bot_log.addHandler(hdlr=stream_handler)

    file_handler = logging.FileHandler(filename='air_ticket_bot.log', delay=False)
    file_handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s', datefmt='%d-%m-%Y %H:%M'))
    file_handler.setLevel(logging.DEBUG)
    bot_log.addHandler(hdlr=file_handler)

    bot_log.setLevel(logging.DEBUG)

    return bot_log


class Bot:

    """
    Echo bot для vk.com

    Сценарий для заказа авиабилетов через vk.com
    Поддерживает ответ на вопрос о помощи (нужно ввести /help)
    Сценарий регистрации (для начала нужно ввести /ticket):
    - спрашиваем имя
    - спрашиваем город отправления
    - спрашиваем город назначения
    - спрашиваем дату
    - спрашиваем количество мест
    - даём возможность оствавить комментарий в произвольной форме
    - просим подтвердить заказ
    - просим номер телефона
    - просим email
    - говорим что заказ прошёл успешно, отправляем картинку с билетом
    Если шаг не пройден, пишем уточняющее сообщение, пока шаг не будет пройден.
    Если в процессе выполнения сценария вводится /help, ответом будет уточняющее сообщение текущего шага.
    Если в процессе выполнения сценария вводится /ticket, ответом будет предложение закончить оформление билета.
    """

    def __init__(self, group_id, group_token):
        """
        :param group_id: group_id группы vk
        :param group_token: секретный токен для этой группы
        """
        self.group_id = group_id
        self.group_token = group_token
        self.vk = VkApi(token=self.group_token)
        self.long_poller = VkBotLongPoll(vk=self.vk, group_id=self.group_id)
        self.api = self.vk.get_api()

    def run(self):
        """
        Запуск бота
        """
        for event in self.long_poller.listen():
            try:
                self.on_event(event=event)
            except Exception:
                log.exception('ОШИБКА ПРИ ОБРАБОТКЕ СОБЫТИЯ')

    @db_session
    def on_event(self, event):
        """
        Ответ на полученные сообщения, если это текст
        :param event: VkBotMessageEvent object
        :return: None
        """
        if event.type != VkBotEventType.MESSAGE_NEW:
            log.info(f'{event.type} - НЕОБРАБАТЫВАЕМЫЙ ТИП СОБЫТИЯ')
            return

        user_id = event.object.message['peer_id']
        text = event.object.message["text"]
        state = UserState.get(user_id=str(user_id))

        if state is not None:
            self.continue_scenario(state=state, user_id=user_id, text=text)
        else:
            # search intent
            for intent in settings.INTENTS:
                log.debug(f'User gets {intent}')
                if any(token in text.lower() for token in intent['tokens']):
                    if intent['answer']:
                        self.send_text(text_to_send=intent['answer'], user_id=user_id)
                    else:
                        self.start_scenario(user_id=user_id, scenario_name=intent['scenario'], text=text)
                    break
            else:
                self.send_text(text_to_send=settings.DEFAULT_ANSWER, user_id=user_id)

    def send_text(self, text_to_send, user_id):
        """
        Отправка сообщения в чат
        :param text_to_send: текст, который нужно отправить
        :param user_id: id пользователя, от которого пришло сообщение боту
        :return: None
        """
        self.api.messages.send(message=text_to_send,
                               random_id=randint(0, 2 ** 20),
                               peer_id=user_id)

    def send_image(self, image, user_id):
        """
        Отправка картинки в чат
        :param image: картинка, который нужно отправить (настроено на формат .png)
        :param user_id: id пользователя, от которого пришло сообщение боту
        :return: None
        """
        upload_url = self.api.photos.getMessagesUploadServer()['upload_url']
        upload_data = requests.post(url=upload_url, files={'photo': ('image.png', image, 'image/png')}).json()

        image_data = self.api.photos.saveMessagesPhoto(**upload_data)
        owner_id = image_data[0]['owner_id']
        media_id = image_data[0]['id']
        attachment = f'photo{owner_id}_{media_id}'

        self.api.messages.send(attachment=attachment,
                               random_id=randint(0, 2 ** 20),
                               peer_id=user_id)

    def send_step(self, step, user_id, text, context):
        """
        Отправка и сообщения, и картинки в чат (если это предусматривается в шаге сценария)
        :param step: текущий шаг выполнения сценария (словарь, с информацией о шаге)
        :param user_id: id пользователя, от которого пришло сообщение боту
        :param text: текст ПОЛУЧЕННОГО от пользователя сообщения
        :param context: контекст работы с пользователем (JSON, хранящийся в базе данных state.context)
        :return: None
        """
        if 'text' in step:
            self.send_text(text_to_send=step['text'].format(**context), user_id=user_id)
        if 'image' in step:
            handler = getattr(handlers, step['image'])
            image = handler(text=text, context=context)
            self.send_image(image=image, user_id=user_id)

    def start_scenario(self, user_id, scenario_name, text):
        """
        Запуск сценария
        :param user_id: id пользователя, от которого пришло сообщение боту
        :param scenario_name: назавание запускаемого сценария
        :param text: текст, введённый пользователем в сообщении
        :return: None
        """
        scenario = settings.SCENARIOS[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        UserState(user_id=str(user_id), scenario_name=scenario_name, step_name=first_step, context={})
        self.send_step(step=step, user_id=user_id, text=text, context={})

    def continue_scenario(self, state, user_id, text):
        """
        Продолжение сценария
        :param state: состояние пользователя в сценарии (таблица из базы данных)
        :param user_id: id пользователя, от которого пришло сообщение боту
        :param text: текст сообщения пользователя
        :return: None
        """
        # continue scenario
        steps = settings.SCENARIOS[state.scenario_name]['steps']
        step = steps[state.step_name]

        if text == '/help':
            self.send_step(step=step, user_id=user_id, text=text, context=state.context)
        elif text == '/ticket':
            state.context['pause_step'] = state.step_name
            next_step = steps['step0']
            state.step_name = 'step0'
            self.send_text(text_to_send=next_step['text'], user_id=user_id)
        else:
            handler = getattr(handlers, step['handler'])
            if handler(text=text.lower(), context=state.context):
                # start new step
                current_foo = self.define_step_foo(step_name=state.step_name)
                current_foo(state=state, steps=steps, step=step, user_id=user_id, text=text)    # работает
            else:
                # retry current step
                text_to_send = step['failure_text'].format(**state.context)
                self.send_text(text_to_send=text_to_send, user_id=user_id)

    def define_step_foo(self, step_name):
        """
        Определение функции, выполняющей текущий шаг
        :param step_name: название выполняемого шага
        :return: название нужной функции
        """
        if step_name == 'step0':
            return self._step0
        elif step_name == 'step3':
            return self._step3
        elif step_name == 'step4':
            return self._step4
        elif step_name == 'step7':
            return self._step7
        elif step_name == 'step8':
            return self._step8
        else:
            return self._normal_step

    def _step0(self, state, steps, step, user_id, text):
        """
        Функция (шаг) отвечает за прерывание исполнения сценария
        :param state: текущее состояние пользователя
        :param steps: все шаги сценария исполняемого в данный момент
        :param step: шаг, на котором сейчас находится пользователь
        :param user_id: id пользователя, от которого пришло сообщение боту
        :param text: текст сообщения пользователя
        :return: None
        """
        # checking the want to go out
        confirmation = state.context['confirmation']
        if not confirmation:
            state.step_name = state.context['pause_step']
            next_step = steps[state.step_name]
            self.send_step(step=next_step, user_id=user_id, text=text, context=state.context)
            del state.context['pause_step']
        else:
            state.step_name = step['additional_next_step']
            next_step = steps[step['additional_next_step']]
            self.send_text(text_to_send=next_step['text'], user_id=user_id)
            state.delete()

    def _step3(self, state, steps, step, user_id, text):
        """
        Функция (шаг) отвечает за проверку сообщения между введёнными городами
        :param state: текущее состояние пользователя
        :param steps: все шаги сценария исполняемого в данный момент
        :param step: шаг, на котором сейчас находится пользователь
        :param user_id: id пользователя, от которого пришло сообщение боту
        :param text: текст сообщения пользователя
        :return: None
        """
        # checking have route between two cities
        departure = state.context['departure']
        appointment = state.context['arrival']
        if not route_controller(departure=departure, arrival=appointment):
            # break scenario if have not route
            next_step = steps[step['additional_next_step']]
            state.step_name = step['additional_next_step']
            self.send_text(text_to_send=next_step['text'], user_id=user_id)
            state.delete()
        else:
            self._normal_step(state=state, steps=steps, step=step, user_id=user_id, text=text)

    def _step4(self, state, steps, step, user_id, text):
        """
        Функция (шаг) отвечает за формирование ближайших пяти рейсов
        :param state: текущее состояние пользователя
        :param steps: все шаги сценария исполняемого в данный момент
        :param step: шаг, на котором сейчас находится пользователь
        :param user_id: id пользователя, от которого пришло сообщение боту
        :param text: текст сообщения пользователя
        :return: None
        """
        # formation route
        departure = state.context['departure']
        arrival = state.context['arrival']
        date = state.context['date']
        state.context['result_flights_dict'], state.context['result_flights_str'] = \
            route_formation(departure=departure, arrival=arrival, date=date)
        self._normal_step(state=state, steps=steps, step=step, user_id=user_id, text=text)

    def _step7(self, state, steps, step, user_id, text):
        """
        Функция (шаг) отвечает за комментарий пользователя
        :param state: текущее состояние пользователя
        :param steps: все шаги сценария исполняемого в данный момент
        :param step: шаг, на котором сейчас находится пользователь
        :param user_id: id пользователя, от которого пришло сообщение боту
        :param text: текст сообщения пользователя
        :return: None
        """
        # checking the want to leave comment
        confirmation = state.context['confirmation']
        if confirmation:
            next_step = steps[step['additional_next_step']]
            state.step_name = step['additional_next_step']
            self.send_text(text_to_send=next_step['text'], user_id=user_id)
        else:
            self._normal_step(state=state, steps=steps, step=step, user_id=user_id, text=text)

    def _step8(self, state, steps, step, user_id, text):
        """
        Функция (шаг) отвечает за подтверждение заказа
        :param state: текущее состояние пользователя
        :param steps: все шаги сценария исполняемого в данный момент
        :param step: шаг, на котором сейчас находится пользователь
        :param user_id: id пользователя, от которого пришло сообщение боту
        :param text: текст сообщения пользователя
        :return: None
        """
        # checking the want to complete ticket
        confirmation = state.context['confirmation']
        if not confirmation:
            next_step = steps[step['additional_next_step']]
            state.step_name = step['additional_next_step']
            self.send_text(text_to_send=next_step['text'], user_id=user_id)
            state.delete()
        else:
            self._normal_step(state=state, steps=steps, step=step, user_id=user_id, text=text)

    def _normal_step(self, state, steps, step, user_id, text):
        """
        Функция "Обычный шаг", используется при обычном переходе из одного шага сценария на другой
        :param state: текущее состояние пользователя
        :param steps: все шаги сценария исполняемого в данный момент
        :param step: шаг, на котором сейчас находится пользователь
        :param user_id: id пользователя, от которого пришло сообщение боту
        :param text: текст сообщения пользователя
        :return: None
        """
        next_step = steps[step['next_step']]
        self.send_step(step=next_step, user_id=user_id, text=text, context=state.context)
        if next_step['next_step']:
            # switch to next step normal
            state.step_name = step['next_step']
        else:
            # finish scenario
            log.info('Оформлен билет:\n'
                     'Телефон покупателя - {phone}\n'
                     'Email покупателя - {email}\n'
                     'Имя - {name}\n'
                     'Город отправления - {departure}\n'
                     'Город прибытия - {arrival}\n'
                     '{flight_date_to_output}\n'
                     'Количество мест - {spaces}\n'
                     'Комментарий - {comment}'.format(**state.context))

            Registration(user_phone=state.context['phone'],
                         user_email=state.context['email'],
                         user_name=state.context['name'],
                         departure=state.context['departure'],
                         arrival=state.context['arrival'],
                         date=state.context['flight_date_to_database'],
                         spaces=state.context['spaces'],
                         comment=state.context['comment'])
            state.delete()


if __name__ == '__main__':
    log = configure_logging()
    bot = Bot(group_id=settings.GROUP_ID, group_token=settings.GROUP_TOKEN)
    bot.run()
else:
    log = configure_logging()
