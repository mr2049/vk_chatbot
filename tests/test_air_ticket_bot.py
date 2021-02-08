# -*- coding: utf-8 -*-

from copy import deepcopy

import unittest
from pony.orm import db_session, rollback
from unittest.mock import Mock, patch

import generate_ticket
from air_ticket_bot import Bot
from vk_api.bot_longpoll import VkBotMessageEvent


try:
    import settings
except ImportError:
    exit('DO --->>>cp setting.py.default settings.py<<<--- and set group_id and group_token!')


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()

    return wrapper


class TestBot(unittest.TestCase):
    RAW_EVENT = {
        'type': 'message_new',
        'object': {
            'message':
                {'date': 1602794324, 'from_id': 618021856, 'id': 69, 'out': 0, 'peer_id': 618021856,
                 'text': 'ПРОВЕРКА', 'conversation_message_id': 68, 'fwd_messages': [], 'important': False,
                 'random_id': 0, 'attachments': [], 'is_hidden': False},
            'client_info':
                {'button_actions': ['text', 'vkpay', 'open_app', 'location', 'open_link'],
                 'keyboard': True, 'inline_keyboard': True, 'carousel': False, 'lang_id': 0}
        },
        'group_id': 199276537,
        'event_id': '15b4cd3ec482654830e341023f2e733dca435026'
    }

    INPUTS = [
        'Привет',
        '/help',
        '/ticket',
        'Иван',
        'москва',
        'лондон',
        '05-12-2020',
        '1',
        '1',
        'нет',
        'да',
        '+7-812-124-12-24',
        'ivan@yandex.ru'
    ]

    EXPECTED_OUTPUTS = [
        settings.DEFAULT_ANSWER,
        settings.DEFAULT_ANSWER,
        settings.SCENARIOS['order_ticket']['steps']['step1']['text'],
        settings.SCENARIOS['order_ticket']['steps']['step2']['text'],
        settings.SCENARIOS['order_ticket']['steps']['step3']['text'],
        settings.SCENARIOS['order_ticket']['steps']['step4']['text'],
        settings.SCENARIOS['order_ticket']['steps']['step5']['text'].format(result_flights_str=True),
        settings.SCENARIOS['order_ticket']['steps']['step6']['text'],
        settings.SCENARIOS['order_ticket']['steps']['step7']['text'],
        settings.SCENARIOS['order_ticket']['steps']['step8']['text'].format(name='Иван',
                                                                            departure='Москва',
                                                                            arrival='Лондон',
                                                                            flight_date_to_output=True,
                                                                            spaces='1'),
        settings.SCENARIOS['order_ticket']['steps']['step9']['text'],
        settings.SCENARIOS['order_ticket']['steps']['step10']['text'],
        settings.SCENARIOS['order_ticket']['steps']['step11']['text'].format(phone='+7-812-124-12-24',
                                                                             email='ivan@yandex.ru')
    ]

    def test_run(self):
        count = 5
        obj = {}
        events = [obj] * count  # [obj, obj, ...]
        long_poller_mock = Mock(return_value=events)
        long_poller_listen_mock = Mock()
        long_poller_listen_mock.listen = long_poller_mock
        with patch('air_ticket_bot.VkApi'):
            with patch('air_ticket_bot.VkBotLongPoll', return_value=long_poller_listen_mock):
                bot = Bot(group_id='', group_token='')
                bot.on_event = Mock()
                bot.run()

                bot.on_event.assert_called()
                bot.on_event.assert_any_call(event=obj)
                self.assertEqual(bot.on_event.call_count, count)

    @isolate_db
    def test_run_ok(self):
        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['message']['text'] = input_text
            events.append(VkBotMessageEvent(event))

        send_mock = Mock()
        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        with patch('air_ticket_bot.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot(group_id='', group_token='')
            bot.api = Mock()
            bot.send_image = Mock()
            bot.api.messages.send = send_mock
            bot.run()
        assert send_mock.call_count == len(self.INPUTS)

        real_outputs = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs['message'])

        # чтобы как-то упорядочить рандомную дату
        real_outputs[6] = settings.SCENARIOS['order_ticket']['steps']['step5']['text'].format(result_flights_str=True)
        real_outputs[9] = settings.SCENARIOS['order_ticket']['steps']['step8']['text'].format(name='Иван',
                                                                                              departure='Москва',
                                                                                              arrival='Лондон',
                                                                                              flight_date_to_output=
                                                                                              True,
                                                                                              spaces='1')
        assert real_outputs == self.EXPECTED_OUTPUTS

    def test_generate_ticket(self):
        with open(file='../files/ivan@yandex.ru.svg', mode='rb') as avatar_file:
            avatar_mock = Mock()
            avatar_mock.content = avatar_file.read()

        with patch('requests.get', return_value=avatar_mock):
            generate_ticket.TEMPLATE_PATH = '../files/air_ticket_sample.jpg'
            generate_ticket.FONT_PATH = '../files/ofont.ru_Lifehack.ttf'
            ticket_file = generate_ticket.generate_ticket(phone='+7-966-866-36-66',
                                                          email='ivan@yandex.ru',
                                                          name='Ivan',
                                                          departure='Moscow',
                                                          arrival='London',
                                                          date='31-12-2020 23:59',
                                                          spaces='1')

        with open(file='../files/example_ticket.png', mode='rb') as expected_file:
            expected_bytes = expected_file.read()

        assert ticket_file.read() == expected_bytes


if __name__ == '__main__':
    unittest.main()
