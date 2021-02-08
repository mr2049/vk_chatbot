# -*- coding: utf-8 -*-

"""
Use python3.8

Handler - функция, которая принимает на вход:
text: текст входящего сообщения
context: dict (JSON), с информацией о состоянии пользователя в сценарии
return: bool, True - если шаг пройден, False - если данные введены некорректно
        handle_generate_ticket - возвращает .png в байтах
"""

import re

from datetime import datetime

from generate_ticket import generate_ticket
from settings_time_table import ROUTE_TABLE


RE_CITIES = {
    'Амстердам': re.compile(r'\bамстердам.{0,2}\b'),
    'Берлин': re.compile(r'\bберлин.{0,2}\b'),
    'Буэнос-Айрес': re.compile(r'\bбуэнос-айрес.{0,2}\b'),
    'Лондон': re.compile(r'\bлондон.{0,2}\b'),
    'Лос-Анджелес': re.compile(r'\bлос-анджелес.{0,2}\b'),
    'Мадрид': re.compile(r'\bмадрид.{0,2}\b'),
    'Москва': re.compile(r'\bмоскв.{0,2}\b'),
    'Нью-Йорк': re.compile(r'\bнью-йорк.{0,2}\b'),
    'Париж': re.compile(r'\bпариж.{0,2}\b'),
    'Пекин': re.compile(r'\bпекин.{0,2}\b'),
    'Рим': re.compile(r'\bрим.{0,2}\b'),
    'Рио-де-Жанейро': re.compile(r'\bрио-де-жанейр.{0,2}\b'),
    'Санкт-Петербург': re.compile(r'\bсанкт-петербург.{0,2}\b'),
    'Сидней': re.compile(r'\bсидне.{0,2}\b'),
    'Токио': re.compile(r'\bтокио.{0,2}\b')
}

RE_EXPRESSIONS = {
    're_name': re.compile(r'^[a-zA-Zа-яА-ЯёЁ]{3,40}$'),
    're_date': re.compile(r'^(\d\d)-(\d\d)-(202[0-1])$'),
    're_five_numbers': re.compile(r'^[1-5]$'),
    're_yes_no': re.compile(r'^да$|^нет$'),
    're_phone': re.compile(r'^(?:[+][7]|[8])(?:-\d{3}){2}(?:-\d{2}){2}$',),
    're_email': re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$')
}


def handle_name(text, context):
    """
    Обработка сообщения об имени
    """
    match = re.match(RE_EXPRESSIONS['re_name'], text)
    if match:
        context['name'] = text
        return True
    else:
        return False


def handle_departure_city(text, context):
    """
    Обработка сообщения о городе отправеления
    """
    if 'available_cities' not in context:
        available_cities = str()
        for city in ROUTE_TABLE.keys():
            available_cities += (str(city) + '\n')
        context['available_cities'] = available_cities

    for city, expression in RE_CITIES.items():
        match = re.search(expression, text)
        if match:
            context['departure'] = city
            return True
    return False


def handle_arrival_city(text, context):
    """
    Обработка сообщения о городе назначения
    """
    for city, expression in RE_CITIES.items():
        match = re.search(expression, text)
        if match:
            context['arrival'] = city
            del context['available_cities']
            return True
    return False


def handle_date(text, context):
    """
    Обработка сообщения о дате отправления
    """
    match = re.search(RE_EXPRESSIONS['re_date'], text)
    if match:
        try:
            user_date = datetime.strptime(match.group(), '%d-%m-%Y')
            if user_date >= datetime.today():
                context['date'] = match.group()
                return True
        except ValueError:
            pass
    return False


def handle_flights(text, context):
    """
    Обработка сообщения о порядковом номере выбранного рейса
    """
    match = re.search(RE_EXPRESSIONS['re_five_numbers'], text)
    if match:
        if match.group() in context['result_flights_dict']:
            flight_date = context['result_flights_dict'][match.group()]
            flight_date = datetime.strptime(flight_date, '%d-%m-%Y %H:%M')
            context['flight_date_to_output'] = flight_date.strftime('Дата вылета - %d-%m-%Y; Время вылета - %H:%M')
            context['flight_date_to_database'] = flight_date.strftime('%d-%m-%Y %H:%M')
            del context['date']
            del context['result_flights_dict']
            del context['result_flights_str']
            return True
    return False


def handle_spaces(text, context):
    """
    Обработка сообщения о количестве мест
    """
    match = re.search(RE_EXPRESSIONS['re_five_numbers'], text)
    if match:
        if 0 < int(match.group()) < 6:
            context['spaces'] = match.group()
            context['comment'] = '-----'
            return True
    return False


def handle_comment(text, context):
    """
    Запись комментария, если пользователь хочет его оставить
    """
    context['comment'] = text
    return True


def handle_confirmation(text, context):
    """
    Обработка сообщения о подтверждениях (завершения оформления, желания выйти, желания оставить комментарий)
    """
    match = re.search(RE_EXPRESSIONS['re_yes_no'], text)
    if match:
        if text == 'да':
            context['confirmation'] = True
        else:
            context['confirmation'] = False
        return True
    return False


def handle_phone(text, context):
    """
    Обработка сообщения о номере телефона
    """
    match = re.search(RE_EXPRESSIONS['re_phone'], text)
    if match:
        context['phone'] = match.group()
        return True
    return False


def handle_email(text, context):
    """
    Обработка сообщения об email
    """
    match = re.match(RE_EXPRESSIONS['re_email'], text)
    if match:
        context['email'] = text
        return True
    else:
        return False


def handle_generate_ticket(text, context):
    """
    Запуск функции рисования билета
    :return: .png в байтах
    """
    return generate_ticket(phone=context['phone'],
                           email=context['email'],
                           name=context['name'],
                           departure=context['departure'],
                           arrival=context['arrival'],
                           date=context['flight_date_to_database'],
                           spaces=context['spaces'])
