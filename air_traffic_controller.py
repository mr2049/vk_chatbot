# -*- coding: utf-8 -*-

"""
Use python3.8

Модуль авиадиспетчер
Проверяет наличие сообщения между городами, формирует распписание
"""

import calendar

from datetime import datetime
from random import randint

from settings_time_table import ROUTE_TABLE


def route_controller(departure, arrival):
    """
    Проверка наличия сообщения
    :param departure: город отправления
    :param arrival: город назначения
    :return: bool, True - сообщение есть, False - сообщения нет
    """
    if arrival in ROUTE_TABLE[departure]:
        return True
    else:
        return False


def route_formation(departure, arrival, date):
    """
    Авиадиспетчер, формирует расписание пяти ближайших доступных рейсов
    :param departure: город отправления
    :param arrival: город назначения
    :param date: дата вылета (str('%d-%m-%Y'))
    :return: possible_flights_dict - расписание в dict {порядковый номер: str('%d-%m-%Y'), ...}, для работы
             possible_flights_str - полное расписание в строке, для вывода в чат
    """

    date = datetime.strptime(date, '%d-%m-%Y')

    # формирование списка возможных дат
    if departure == 'Москва' and arrival == 'Лондон':
        all_flights = system_weeks_days(date=date)
    elif departure == 'Лондон' and arrival == 'Париж':
        all_flights = system_month_days(date=date)
    else:
        all_flights = random_days(date=date)

    result_flights_dict = {}  # даты в словаре, для работы
    result_flights_str = str()  # даты строкой, для вывода в чат
    flights_count = 0
    # подбор пяти ближайших
    for table_datetime in all_flights:
        if table_datetime >= date:
            flights_count += 1

            result_flights_dict[str(flights_count)] = datetime.strftime(table_datetime, '%d-%m-%Y %H:%M')

            result_flights_str += datetime.strftime(table_datetime, f'{flights_count}:\t'
                                                                    f'Дата вылета - %d-%m-%Y; Время вылета - %H:%M\n')
        if len(result_flights_dict) >= 5:
            break

    return result_flights_dict, result_flights_str


def random_days(date):
    """
    Формирует случайные числа в месяце, который ввёл пользователь
    :param date: datetime object
    :return: list[datetime object, ...]
    """
    list_of_flights = []

    if date.day < 25:
        count = 13
    else:
        count = 2

    # если пользователь ввёл число позднее 25, добавляем 2 рейса в этом месяце
    while len(list_of_flights) < count:
        try:
            random_day = randint(date.day, 31)
            flight_date = datetime(year=date.year, month=date.month, day=random_day,
                                   hour=randint(0, 23), minute=randint(0, 59))
            list_of_flights.append(flight_date)
        except ValueError:
            pass

    # и ещё 13 ресов в следующем месяце (или году)
    if count == 2:
        next_month = date.month + 1
        next_year = date.year
        if next_month == 13:
            next_month = 1
            next_year = date.year + 1
        while len(list_of_flights) < 15:
            random_day = randint(1, 15)
            flight_date = datetime(year=next_year, month=next_month, day=random_day,
                                   hour=randint(0, 23), minute=randint(0, 59))
            list_of_flights.append(flight_date)

    list_of_flights = sorted(list_of_flights)
    return list_of_flights


def system_month_days(date):
    """
    Добавляет к случайным числам месяца из random_days, регулярные рейсы (каждое 5, 15, 25 числа месяца)
    :param date: datetime object
    :return: list[datetime object, ...]
    """
    list_of_flights = random_days(date=date)

    # в этом месяце
    for day in range(5, 26, 10):
        system_flight_date = datetime(year=date.year, month=date.month, day=day, hour=15, minute=30)
        list_of_flights.append(system_flight_date)

    # в следующем месяце (или году)
    next_month = date.month + 1
    next_year = date.year
    if next_month == 13:
        next_month = 1
        next_year = date.year + 1
    for day in range(5, 26, 10):
        system_flight_date = datetime(year=next_year, month=next_month, day=day, hour=15, minute=30)
        list_of_flights.append(system_flight_date)

    list_of_flights = sorted(list_of_flights)
    return list_of_flights


def system_weeks_days(date):
    """
    Добавляет к случайным числам месяца из random_days, регулярные рейсы (понедельник и среду в неделе)
    :param date: datetime object
    :return: list[datetime object, ...]
    """
    list_of_flights = random_days(date=date)
    calendar_text = calendar.TextCalendar()
    days_iterator = calendar_text.itermonthdays2(year=date.year, month=date.month)

    # понедельники и среды этого месяца
    for day_number, week_day_number in days_iterator:
        if (week_day_number == 0 or week_day_number == 2) and day_number != 0:
            system_flight_date = datetime(year=date.year, month=date.month, day=day_number, hour=10, minute=0)
            list_of_flights.append(system_flight_date)

    # понедельники и среды из следующего месяца (или года)
    next_month = date.month + 1
    next_year = date.year
    if next_month == 13:
        next_month = 1
        next_year = date.year + 1
    days_iterator = calendar_text.itermonthdays2(year=next_year, month=next_month)

    for day_number, week_day_number in days_iterator:
        if (week_day_number == 0 or week_day_number == 2) and day_number != 0:
            system_flight_date = datetime(year=next_year, month=next_month, day=day_number, hour=10, minute=0)
            list_of_flights.append(system_flight_date)

    list_of_flights = sorted(list_of_flights)
    return list_of_flights
