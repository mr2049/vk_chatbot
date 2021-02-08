# -*- coding: utf-8 -*-

"""
Use python3.8

Инициализация таблиц в базе данных
"""

from pony.orm import Database, Required, Json

from settings import DB_CONFIG


db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
    """
    Состояние пользователя внутри сценариия.
    Если у пользователя нет state - он не находится внутри сценария, если есть - находится
    """
    user_id = Required(str, unique=True)    # уникальный id пользователя
    scenario_name = Required(str)   # сценарий, в котором находится пользователь
    step_name = Required(str)   # шаг, на котором находится пользователь
    context = Required(Json)    # контекст работы с пользователем


class Registration(db.Entity):
    """
    Заявки на регистрацию
    """
    user_phone = Required(str, unique=True)
    user_email = Required(str)
    user_name = Required(str)
    departure = Required(str)
    arrival = Required(str)
    date = Required(str)
    spaces = Required(str)
    comment = Required(str)


db.generate_mapping(create_tables=True)
